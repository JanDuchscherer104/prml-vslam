"""Visualization-policy layer for the repo-owned Rerun event sink."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata

# TODO(pipeline-refactor/WP-10): Remove legacy backend notice imports after
# RerunLoggingPolicy.observe_update(...) is the only Rerun live telemetry path.
from prml_vslam.interfaces.slam import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, PacketObserved, RunEvent, StageCompleted
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.slam.visualization import (
    COLORS_REF,
    DEPTH_REF,
    IMAGE_REF,
    POINTMAP_REF,
    ROLE_KEYFRAME_CAMERA_POSE,
    ROLE_KEYFRAME_CAMERA_WINDOW,
    ROLE_KEYFRAME_DEPTH,
    ROLE_KEYFRAME_PINHOLE,
    ROLE_KEYFRAME_POINTMAP,
    ROLE_KEYFRAME_POINTS_POSE,
    ROLE_KEYFRAME_PREVIEW,
    ROLE_KEYFRAME_RGB,
    ROLE_LIVE_MODEL_POSE,
    ROLE_MODEL_CAMERA_RGB,
    ROLE_MODEL_DEPTH,
    ROLE_MODEL_PINHOLE,
    ROLE_MODEL_POINTMAP,
    ROLE_MODEL_PREVIEW,
    ROLE_MODEL_RGB,
    ROLE_SOURCE_RGB,
    ROLE_TRACKING_POSE,
    ROLE_TRACKING_TRAJECTORY,
)
from prml_vslam.visualization.rerun import MODEL_RGB_2D_ENTITY_PATH

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RerunLoggingPolicy:
    """Own Rerun entity layout, timelines, and branch logging semantics.

    The current ViSTA-aligned policy keeps upstream-native world semantics:

    - source RGB stays on its own source-frame branch;
    - model RGB, depth, intrinsics, preview, and pointmap stay on the
      ViSTA-preprocessed model raster;
    - pointmaps remain camera-local and are composed into world only through
      their posed parent entity.
    """

    log_pinhole: Callable[..., None]
    log_pointcloud: Callable[..., None]
    log_line_strip3d: Callable[..., None]
    log_clear: Callable[..., None]
    log_depth_image: Callable[..., None]
    log_ground_plane_patch: Callable[..., None]
    log_rgb_image: Callable[..., None]
    log_transform: Callable[..., None]
    frusta_history_window_streaming: int | None = 20
    show_tracking_trajectory: bool = True
    log_source_rgb: bool = False
    log_diagnostic_preview: bool = False
    log_camera_image_rgb: bool = False
    _warned_fallback_intrinsics: bool = field(default=False, init=False, repr=False)
    _visible_keyframe_camera_indices: deque[int] = field(default_factory=deque, init=False, repr=False)
    _trajectory_positions_xyz: list[tuple[float, float, float]] = field(default_factory=list, init=False, repr=False)

    # TODO(pipeline-refactor/WP-10): Delete this RunEvent policy path after
    # Rerun, snapshot, app, and coordinator consumers migrate to
    # StageRuntimeUpdate.visualizations.
    def observe(self, stream, event: RunEvent, *, payloads: Mapping[str, np.ndarray] | None = None) -> None:
        """Log one pipeline event according to the current Rerun layout policy.

        `PacketObserved` and `KeyframeVisualizationReady` intentionally feed
        different image surfaces:

        - `PacketObserved.frame` logs the original source raster on
          `world/live/source/rgb`;
        - `KeyframeVisualizationReady` logs ViSTA model-raster payloads on the
          live/model and keyed-history branches.
        """
        resolved_payloads = {} if payloads is None else payloads
        match event:
            case PacketObserved(packet=packet, frame=frame) if frame is not None:
                if not self.log_source_rgb:
                    return
                image = self._resolve_optional_array(frame, payloads=resolved_payloads)
                if image is None:
                    return
                self._set_frame_time(stream, packet.seq)
                self.log_rgb_image(stream, entity_path="world/live/source/rgb", image_rgb=image)
            case BackendNoticeReceived(notice=notice):
                match notice:
                    case PoseEstimated(pose=pose, seq=seq, source_seq=source_seq):
                        self._set_frame_time(stream, source_seq if source_seq is not None else seq)
                        self.log_transform(
                            stream,
                            entity_path="world/live/tracking/camera",
                            transform=pose,
                            axis_length=0.0,
                        )
                        self._log_tracking_trajectory(stream, pose=pose)
                    case KeyframeVisualizationReady() as keyframe_notice:
                        self._log_keyframe_visualization(stream, keyframe_notice, payloads=resolved_payloads)
                    case _:
                        return
            case StageCompleted(stage_key=stage_key, ground_alignment=ground_alignment):
                if stage_key is StageKey.GROUND_ALIGNMENT:
                    self._log_ground_alignment(stream, metadata=ground_alignment)
            case _:
                return

    def observe_update(
        self,
        stream,
        update: StageRuntimeUpdate,
        *,
        payloads: Mapping[str, np.ndarray] | None = None,
    ) -> None:
        """Log one live runtime update from neutral visualization items."""
        # TODO(pipeline-refactor/WP-08): Replace this materialized payload map
        # with the canonical TransientPayloadRef resolver API once it lands.
        resolved_payloads = {} if payloads is None else payloads
        for semantic_event in update.semantic_events:
            if isinstance(semantic_event, GroundAlignmentMetadata):
                self._log_ground_alignment(stream, metadata=semantic_event)
        for item in update.visualizations:
            self._log_visualization_item(stream, item, payloads=resolved_payloads)

    def _log_visualization_item(
        self,
        stream,
        item: VisualizationItem,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        """Map one SDK-free visualization item to the current Rerun policy."""
        match item.intent:
            case VisualizationIntent.RGB_IMAGE:
                self._log_rgb_item(stream, item, payloads=payloads)
            case VisualizationIntent.DEPTH_IMAGE:
                self._log_depth_item(stream, item, payloads=payloads)
            case VisualizationIntent.POINT_CLOUD:
                self._log_pointcloud_item(stream, item, payloads=payloads)
            case VisualizationIntent.TRAJECTORY:
                self._log_trajectory_item(stream, item)
            case VisualizationIntent.POSE_TRANSFORM:
                self._log_pose_item(stream, item)
            case VisualizationIntent.PINHOLE_CAMERA:
                self._log_pinhole_item(stream, item, payloads=payloads)
            case VisualizationIntent.CLEAR:
                self._log_clear_item(stream, item)
            case VisualizationIntent.GROUND_PLANE | VisualizationIntent.MESH:
                return

    def _log_rgb_item(
        self,
        stream,
        item: VisualizationItem,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        image = self._resolve_visualization_array(item.payload_refs.get(IMAGE_REF), payloads=payloads)
        if image is None:
            return
        match item.role:
            case _ if item.role == ROLE_SOURCE_RGB:
                if not self.log_source_rgb:
                    return
                entity_path = "world/live/source/rgb"
            case _ if item.role == ROLE_MODEL_RGB:
                entity_path = MODEL_RGB_2D_ENTITY_PATH
            case _ if item.role == ROLE_MODEL_CAMERA_RGB:
                if not self.log_camera_image_rgb:
                    return
                entity_path = "world/live/model/camera/image"
            case _ if item.role == ROLE_MODEL_PREVIEW:
                if not self.log_diagnostic_preview:
                    return
                entity_path = "world/live/model/diag/preview"
            case _ if item.role == ROLE_KEYFRAME_RGB:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/cameras/{keyframe_index:06d}/image"
            case _ if item.role == ROLE_KEYFRAME_PREVIEW:
                if not self.log_diagnostic_preview:
                    return
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/cameras/{keyframe_index:06d}/diag/preview"
            case _:
                return
        self._set_item_frame_time(stream, item)
        self.log_rgb_image(stream, entity_path=entity_path, image_rgb=image)

    def _log_depth_item(
        self,
        stream,
        item: VisualizationItem,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        depth_image = self._resolve_visualization_array(item.payload_refs.get(DEPTH_REF), payloads=payloads)
        if depth_image is None:
            return
        match item.role:
            case _ if item.role == ROLE_MODEL_DEPTH:
                entity_path = "world/live/model/camera/image/depth"
            case _ if item.role == ROLE_KEYFRAME_DEPTH:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/cameras/{keyframe_index:06d}/image/depth"
            case _:
                return
        self._set_item_frame_time(stream, item)
        self.log_depth_image(stream, entity_path=entity_path, depth_m=depth_image)

    def _log_pointcloud_item(
        self,
        stream,
        item: VisualizationItem,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        pointmap = self._resolve_visualization_array(item.payload_refs.get(POINTMAP_REF), payloads=payloads)
        if pointmap is None:
            return
        colors = self._resolve_visualization_array(item.payload_refs.get(COLORS_REF), payloads=payloads)
        match item.role:
            case _ if item.role == ROLE_MODEL_POINTMAP:
                entity_path = "world/live/model/points"
            case _ if item.role == ROLE_KEYFRAME_POINTMAP:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/points/{keyframe_index:06d}/points"
            case _:
                return
        self._set_item_frame_time(stream, item)
        self.log_pointcloud(stream, entity_path=entity_path, pointmap=pointmap, colors=colors)

    def _log_trajectory_item(self, stream, item: VisualizationItem) -> None:
        if item.role != ROLE_TRACKING_TRAJECTORY or item.pose is None:
            return
        self._set_item_frame_time(stream, item)
        self._log_tracking_trajectory(stream, pose=item.pose)

    def _log_pose_item(self, stream, item: VisualizationItem) -> None:
        if item.pose is None:
            return
        match item.role:
            case _ if item.role == ROLE_TRACKING_POSE:
                entity_path = "world/live/tracking/camera"
            case _ if item.role == ROLE_LIVE_MODEL_POSE:
                entity_path = "world/live/model"
            case _ if item.role == ROLE_KEYFRAME_CAMERA_POSE:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/cameras/{keyframe_index:06d}"
            case _ if item.role == ROLE_KEYFRAME_POINTS_POSE:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/points/{keyframe_index:06d}"
            case _:
                return
        self._set_item_frame_time(stream, item)
        self.log_transform(stream, entity_path=entity_path, transform=item.pose, axis_length=0.0)

    def _log_pinhole_item(
        self,
        stream,
        item: VisualizationItem,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        match item.role:
            case _ if item.role == ROLE_MODEL_PINHOLE:
                entity_path = "world/live/model/camera/image"
            case _ if item.role == ROLE_KEYFRAME_PINHOLE:
                keyframe_index = self._require_keyframe_index(item)
                if keyframe_index is None:
                    return
                entity_path = f"world/keyframes/cameras/{keyframe_index:06d}/image"
            case _:
                return
        rgb = self._resolve_visualization_array(item.payload_refs.get(IMAGE_REF), payloads=payloads)
        depth_image = self._resolve_visualization_array(item.payload_refs.get(DEPTH_REF), payloads=payloads)
        viewer_intrinsics = self._resolve_viewer_intrinsics(
            intrinsics=item.intrinsics,
            rgb=rgb,
            depth_image=depth_image,
        )
        if viewer_intrinsics is None:
            return
        self._set_item_frame_time(stream, item)
        self.log_pinhole(stream, entity_path=entity_path, intrinsics=viewer_intrinsics)

    def _log_clear_item(self, stream, item: VisualizationItem) -> None:
        if item.role != ROLE_KEYFRAME_CAMERA_WINDOW or item.keyframe_index is None:
            return
        self._set_item_frame_time(stream, item)
        self._evict_stale_keyframe_cameras(stream, keyframe_index=item.keyframe_index)

    def _log_ground_alignment(self, stream, *, metadata: GroundAlignmentMetadata | None) -> None:
        """Log one derived ground-plane overlay when the alignment stage completes."""
        if metadata is None or not metadata.applied:
            return
        self.log_ground_plane_patch(stream, metadata=metadata)

    # TODO(pipeline-refactor/WP-10): Delete after KeyframeVisualizationReady is
    # no longer consumed by the Rerun sink; _log_visualization_item(...) is the
    # target path.
    def _log_keyframe_visualization(
        self,
        stream,
        notice: KeyframeVisualizationReady,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> None:
        rgb = self._resolve_optional_array(notice.image, payloads=payloads)
        depth_image = self._resolve_optional_array(notice.depth, payloads=payloads)
        preview_image = self._resolve_optional_array(notice.preview, payloads=payloads)
        pointmap = self._resolve_optional_array(notice.pointmap, payloads=payloads)
        frame_index = notice.source_seq if notice.source_seq is not None else notice.seq

        self._log_model_branch(
            stream,
            frame_index=frame_index,
            root_entity="world/live/model",
            pose=notice.pose,
            intrinsics=notice.camera_intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
            pointmap=pointmap,
        )
        self._log_keyframe_branch(
            stream,
            frame_index=frame_index,
            keyframe_index=notice.keyframe_index,
            camera_root_entity=f"world/keyframes/cameras/{notice.keyframe_index:06d}",
            points_root_entity=f"world/keyframes/points/{notice.keyframe_index:06d}",
            pose=notice.pose,
            intrinsics=notice.camera_intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
            pointmap=pointmap,
        )
        self._evict_stale_keyframe_cameras(stream, keyframe_index=notice.keyframe_index)

    # TODO(pipeline-refactor/WP-10): Delete with _log_keyframe_visualization(...).
    def _log_model_branch(
        self,
        stream,
        *,
        frame_index: int,
        root_entity: str,
        pose: FrameTransform,
        intrinsics: CameraIntrinsics | None,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
        pointmap: np.ndarray | None,
    ) -> None:
        """Log the latest coherent keyframe bundle on the live frame axis.

        This branch is intentionally ephemeral. It should represent only the
        newest accepted keyframe bundle and is useful for current-state
        debugging, not for accumulated world-map rendering.

        The payloads on this branch share the ViSTA model raster. The pointmap
        stays camera-local and inherits world placement from `root_entity`.
        """
        self._set_frame_time(stream, frame_index)
        self.log_transform(stream, entity_path=root_entity, transform=pose, axis_length=0.0)
        if rgb is not None:
            self.log_rgb_image(stream, entity_path=MODEL_RGB_2D_ENTITY_PATH, image_rgb=rgb)
        self._log_camera_payloads(
            stream,
            camera_image_entity=f"{root_entity}/camera/image",
            preview_entity=f"{root_entity}/diag/preview",
            intrinsics=intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
        )
        self._log_pointmap(
            stream,
            pointmap_entity=f"{root_entity}/points",
            pointmap=pointmap,
            rgb=rgb,
        )

    # TODO(pipeline-refactor/WP-10): Delete with _log_keyframe_visualization(...).
    def _log_keyframe_branch(
        self,
        stream,
        *,
        frame_index: int,
        keyframe_index: int,
        camera_root_entity: str,
        points_root_entity: str,
        pose: FrameTransform,
        intrinsics: CameraIntrinsics | None,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
        pointmap: np.ndarray | None,
    ) -> None:
        """Log one persistent historical keyframe bundle on the frame axis.

        Each historical keyframe gets its own entity subtree, and persistence
        comes from unique entity paths plus latest-at frame queries. Logging the
        branch on the source-frame timeline keeps the keyed history visible at
        the active frame cursor and avoids detached leaf inspection rows.

        This branch preserves camera-local pointmaps as posed descendants. It
        is not a fused world-space dense cloud export.
        """
        del keyframe_index
        self._set_frame_time(stream, frame_index)
        self.log_transform(stream, entity_path=camera_root_entity, transform=pose, axis_length=0.0)
        self.log_transform(stream, entity_path=points_root_entity, transform=pose, axis_length=0.0)
        self._log_camera_payloads(
            stream,
            camera_image_entity=f"{camera_root_entity}/image",
            preview_entity=f"{camera_root_entity}/diag/preview",
            intrinsics=intrinsics,
            rgb=rgb,
            depth_image=depth_image,
            preview_image=preview_image,
        )
        self._log_pointmap(
            stream,
            pointmap_entity=f"{points_root_entity}/points",
            pointmap=pointmap,
            rgb=rgb,
        )

    # TODO(pipeline-refactor/WP-10): Delete when old ArrayHandle/PreviewHandle
    # keyframe visualization notices leave the Rerun policy.
    def _log_camera_payloads(
        self,
        stream,
        *,
        camera_image_entity: str,
        preview_entity: str,
        intrinsics: CameraIntrinsics | None,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
        preview_image: np.ndarray | None,
    ) -> None:
        viewer_intrinsics = self._resolve_viewer_intrinsics(intrinsics=intrinsics, rgb=rgb, depth_image=depth_image)
        if viewer_intrinsics is None:
            if rgb is not None or depth_image is not None:
                _LOGGER.warning(
                    "Skipping 3D camera payloads for '%s' until pinhole intrinsics are available.",
                    camera_image_entity,
                )
        else:
            if rgb is not None or depth_image is not None:
                self.log_pinhole(stream, entity_path=camera_image_entity, intrinsics=viewer_intrinsics)

            if rgb is not None and self.log_camera_image_rgb:
                self.log_rgb_image(stream, entity_path=camera_image_entity, image_rgb=rgb)

            if depth_image is not None:
                self.log_depth_image(stream, entity_path=f"{camera_image_entity}/depth", depth_m=depth_image)

        if preview_image is not None and self.log_diagnostic_preview:
            self.log_rgb_image(stream, entity_path=preview_entity, image_rgb=preview_image)

    def _log_tracking_trajectory(self, stream, *, pose: FrameTransform) -> None:
        """Log one growing trajectory polyline from all observed pose estimates."""
        if not self.show_tracking_trajectory:
            return
        self._trajectory_positions_xyz.append((float(pose.tx), float(pose.ty), float(pose.tz)))
        self.log_line_strip3d(
            stream,
            entity_path="world/trajectory/tracking",
            positions_xyz=np.asarray(self._trajectory_positions_xyz, dtype=np.float32),
        )

    def _evict_stale_keyframe_cameras(self, stream, *, keyframe_index: int) -> None:
        """Keep only the newest configured keyed-camera subtrees latest-visible."""
        if self.frusta_history_window_streaming is None:
            return
        self._visible_keyframe_camera_indices.append(keyframe_index)
        while len(self._visible_keyframe_camera_indices) > self.frusta_history_window_streaming:
            stale_keyframe_index = self._visible_keyframe_camera_indices.popleft()
            self.log_clear(
                stream,
                entity_path=f"world/keyframes/cameras/{stale_keyframe_index:06d}",
                recursive=True,
            )

    # TODO(pipeline-refactor/WP-10): Delete when old keyframe visualization
    # notices no longer route camera-local pointmaps through this helper.
    def _log_pointmap(
        self,
        stream,
        *,
        pointmap_entity: str,
        pointmap: np.ndarray | None,
        rgb: np.ndarray | None,
    ) -> None:
        """Log one camera-local pointmap beneath its posed parent entity."""
        if pointmap is None:
            return
        self.log_pointcloud(stream, entity_path=pointmap_entity, pointmap=pointmap, colors=rgb)

    def _resolve_viewer_intrinsics(
        self,
        *,
        intrinsics: CameraIntrinsics | None,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
    ) -> CameraIntrinsics | None:
        raster_size = self._resolve_raster_size(rgb=rgb, depth_image=depth_image)
        if intrinsics is None:
            if raster_size is None:
                return None
            if not self._warned_fallback_intrinsics:
                _LOGGER.warning(
                    "Rerun logging is falling back to synthetic viewer intrinsics because camera intrinsics are absent."
                )
                self._warned_fallback_intrinsics = True
            width_px, height_px = raster_size
            half_width = width_px / 2.0
            half_height = height_px / 2.0
            return CameraIntrinsics(
                fx=half_width,
                fy=half_height,
                cx=half_width,
                cy=half_height,
                width_px=width_px,
                height_px=height_px,
            )
        if raster_size is None or (intrinsics.width_px is not None and intrinsics.height_px is not None):
            return intrinsics
        width_px, height_px = raster_size
        return intrinsics.model_copy(update={"width_px": width_px, "height_px": height_px})

    @staticmethod
    def _resolve_raster_size(
        *,
        rgb: np.ndarray | None,
        depth_image: np.ndarray | None,
    ) -> tuple[int, int] | None:
        if rgb is not None and depth_image is not None and rgb.shape[:2] != depth_image.shape[:2]:
            raise ValueError(
                "Rerun camera RGB and depth payloads must share the same raster shape for one visualization bundle."
            )
        if rgb is not None:
            return int(rgb.shape[1]), int(rgb.shape[0])
        if depth_image is not None:
            return int(depth_image.shape[1]), int(depth_image.shape[0])
        return None

    @staticmethod
    def _set_frame_time(stream, frame_index: int) -> None:
        stream.reset_time()
        stream.set_time("frame", sequence=frame_index)

    @staticmethod
    def _set_item_frame_time(stream, item: VisualizationItem) -> None:
        if item.frame_index is None:
            return
        RerunLoggingPolicy._set_frame_time(stream, item.frame_index)

    @staticmethod
    def _require_keyframe_index(item: VisualizationItem) -> int | None:
        if item.keyframe_index is None:
            _LOGGER.warning("Skipping Rerun visualization item '%s' without keyframe_index.", item.role)
            return None
        return item.keyframe_index

    # TODO(pipeline-refactor/WP-10): Delete after ArrayHandle/PreviewHandle are
    # removed from the Rerun path in favor of TransientPayloadRef resolution.
    @staticmethod
    def _resolve_optional_array(
        handle: ArrayHandle | PreviewHandle | None,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> np.ndarray | None:
        if handle is None:
            return None
        payload = payloads.get(handle.handle_id)
        return None if payload is None else np.asarray(payload)

    @staticmethod
    def _resolve_visualization_array(
        ref: TransientPayloadRef | None,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> np.ndarray | None:
        if ref is None:
            return None
        payload = payloads.get(ref.handle_id)
        return None if payload is None else np.asarray(payload)


__all__ = ["RerunLoggingPolicy"]
