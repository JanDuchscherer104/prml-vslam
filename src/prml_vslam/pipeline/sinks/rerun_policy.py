"""Visualization-policy layer for the repo-owned Rerun event sink."""

from __future__ import annotations

import logging
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.methods.events import KeyframeVisualizationReady, PoseEstimated
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, PacketObserved, RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RerunLoggingPolicy:
    """Own Rerun entity layout, timelines, and branch logging semantics."""

    log_pinhole: Callable[..., None]
    log_pointcloud: Callable[..., None]
    log_line_strip3d: Callable[..., None]
    log_clear: Callable[..., None]
    log_depth_image: Callable[..., None]
    log_rgb_image: Callable[..., None]
    log_transform: Callable[..., None]
    frusta_history_window_streaming: int | None = 20
    show_tracking_trajectory: bool = True
    _warned_fallback_intrinsics: bool = field(default=False, init=False, repr=False)
    _visible_keyframe_camera_indices: deque[int] = field(default_factory=deque, init=False, repr=False)
    _trajectory_positions_xyz: list[tuple[float, float, float]] = field(default_factory=list, init=False, repr=False)

    def observe(self, stream, event: RunEvent, *, payloads: Mapping[str, np.ndarray] | None = None) -> None:
        """Log one pipeline event according to the current Rerun layout policy."""
        resolved_payloads = {} if payloads is None else payloads
        match event:
            case PacketObserved(packet=packet, frame=frame) if frame is not None:
                image = self._resolve_optional_array(frame, payloads=resolved_payloads)
                if image is None:
                    return
                self._set_frame_time(stream, packet.seq)
                self.log_rgb_image(stream, entity_path="world/live/source/rgb", image_rgb=image)
            case BackendNoticeReceived(notice=notice):
                match notice:
                    case PoseEstimated(pose=pose, seq=seq, source_seq=source_seq):
                        self._set_frame_time(stream, source_seq if source_seq is not None else seq)
                        self.log_transform(stream, entity_path="world/live/tracking/camera", transform=pose)
                        self._log_tracking_trajectory(stream, pose=pose)
                    case KeyframeVisualizationReady() as keyframe_notice:
                        self._log_keyframe_visualization(stream, keyframe_notice, payloads=resolved_payloads)
                    case _:
                        return
            case _:
                return

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
        """
        self._set_frame_time(stream, frame_index)
        self.log_transform(stream, entity_path=root_entity, transform=pose)
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
        """
        del keyframe_index
        self._set_frame_time(stream, frame_index)
        self.log_transform(stream, entity_path=camera_root_entity, transform=pose)
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
        if viewer_intrinsics is not None and (rgb is not None or depth_image is not None):
            self.log_pinhole(stream, entity_path=camera_image_entity, intrinsics=viewer_intrinsics)

        if rgb is not None:
            self.log_rgb_image(stream, entity_path=camera_image_entity, image_rgb=rgb)

        if depth_image is not None:
            self.log_depth_image(stream, entity_path=f"{camera_image_entity}/depth", depth_m=depth_image)

        if preview_image is not None:
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
    def _resolve_optional_array(
        handle: ArrayHandle | PreviewHandle | None,
        *,
        payloads: Mapping[str, np.ndarray],
    ) -> np.ndarray | None:
        if handle is None:
            return None
        payload = payloads.get(handle.handle_id)
        return None if payload is None else np.asarray(payload)


__all__ = ["RerunLoggingPolicy"]
