"""Visualization-policy layer for the repo-owned Rerun event sink."""

from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from prml_vslam.eval.contracts import TrajectoryAlignmentArtifact
from prml_vslam.interfaces import CAMERA_RDF_FRAME, CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.methods.stage.visualization import (
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
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeUpdate, VisualizationIntent, VisualizationItem
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.reconstruction.stage.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)
from prml_vslam.sources.stage.visualization import METADATA_ARTIFACT as SOURCE_METADATA_ARTIFACT
from prml_vslam.sources.stage.visualization import POINT_CLOUD_ARTIFACT as SOURCE_POINT_CLOUD_ARTIFACT
from prml_vslam.sources.stage.visualization import (
    ROLE_SOURCE_CAMERA_POSE,
    ROLE_SOURCE_CAMERA_RGB,
    ROLE_SOURCE_DEPTH,
    ROLE_SOURCE_PINHOLE,
    ROLE_SOURCE_POINTMAP,
    ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ROLE_SOURCE_REFERENCE_TRAJECTORY,
    TRAJECTORY_ARTIFACT,
)
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.visualization.artifacts import (
    ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD,
    ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT,
    ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD,
    ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY,
)
from prml_vslam.visualization.rerun import (
    KEYFRAME_IMAGE_PLANE_DISTANCE,
    LIVE_MODEL_IMAGE_PLANE_DISTANCE,
    MODEL_RGB_2D_ENTITY_PATH,
    SLAM_WORLD_AXIS_LENGTH,
    SOURCE_IMAGE_PLANE_DISTANCE,
    TRAJECTORY_START_AXIS_LENGTH,
)

_LOGGER = logging.getLogger(__name__)
_RGB_ENTITY_PATHS = {
    ROLE_SOURCE_RGB: "world/live/source/rgb",
    ROLE_SOURCE_CAMERA_RGB: "world/live/source/camera/image",
    ROLE_MODEL_RGB: MODEL_RGB_2D_ENTITY_PATH,
    ROLE_MODEL_CAMERA_RGB: "world/slam/live/model/camera/image",
    ROLE_MODEL_PREVIEW: "world/slam/live/model/diag/preview",
    ROLE_KEYFRAME_RGB: "world/slam/keyframes/cameras/{keyframe_index:06d}/image",
    ROLE_KEYFRAME_PREVIEW: "world/slam/keyframes/cameras/{keyframe_index:06d}/diag/preview",
}
_SOURCE_RGB_ROLES = {ROLE_SOURCE_RGB, ROLE_SOURCE_CAMERA_RGB}
_DIAGNOSTIC_PREVIEW_ROLES = {ROLE_MODEL_PREVIEW, ROLE_KEYFRAME_PREVIEW}
_DEPTH_ENTITY_PATHS = {
    ROLE_MODEL_DEPTH: "world/slam/live/model/camera/image/depth",
    ROLE_SOURCE_DEPTH: "world/live/source/camera/image/depth",
    ROLE_KEYFRAME_DEPTH: "world/slam/keyframes/cameras/{keyframe_index:06d}/image/depth",
}
_POINTMAP_ENTITY_PATHS = {
    ROLE_MODEL_POINTMAP: "world/slam/live/model/points",
    ROLE_SOURCE_POINTMAP: "world/live/source/camera/points",
    ROLE_KEYFRAME_POINTMAP: "world/slam/keyframes/points/{keyframe_index:06d}/points",
}
_POSE_ENTITY_PATHS = {
    ROLE_TRACKING_POSE: "world/slam/live/tracking/camera",
    ROLE_SOURCE_CAMERA_POSE: "world/live/source/camera",
    ROLE_LIVE_MODEL_POSE: "world/slam/live/model",
    ROLE_KEYFRAME_CAMERA_POSE: "world/slam/keyframes/cameras/{keyframe_index:06d}",
    ROLE_KEYFRAME_POINTS_POSE: "world/slam/keyframes/points/{keyframe_index:06d}",
}
_PINHOLE_ENTITY_PATHS = {
    ROLE_MODEL_PINHOLE: "world/slam/live/model/camera/image",
    ROLE_SOURCE_PINHOLE: "world/live/source/camera/image",
    ROLE_KEYFRAME_PINHOLE: "world/slam/keyframes/cameras/{keyframe_index:06d}/image",
}


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
    log_pointcloud_ply: Callable[..., None]
    log_mesh_ply: Callable[..., None]
    log_line_strip3d: Callable[..., None]
    log_clear: Callable[..., None]
    log_depth_image: Callable[..., None]
    log_ground_plane_patch: Callable[..., None]
    log_rgb_image: Callable[..., None]
    log_transform: Callable[..., None]
    log_sim3_transform: Callable[..., None]
    show_tracking_trajectory: bool = True
    trajectory_pose_axis_length: float = 0.0
    log_source_rgb: bool = False
    log_diagnostic_preview: bool = False
    log_camera_image_rgb: bool = True
    log_keyframe_camera_payloads: bool = False
    point_cloud_decimation_keep_ratio: float = 1.0
    reference_point_cloud_decimation_keep_ratio: float = 1.0
    mesh_decimation_keep_ratio: float = 1.0
    decimation_random_seed: int = 0
    _warned_fallback_intrinsics: bool = field(default=False, init=False, repr=False)
    _tracking_trajectory_xyz: list[tuple[float, float, float]] = field(default_factory=list, init=False, repr=False)
    _logged_tracking_start_axes: bool = field(default=False, init=False, repr=False)

    def observe_update(
        self,
        stream,
        update: StageRuntimeUpdate,
        *,
        payloads: Mapping[str, np.ndarray] | None = None,
    ) -> None:
        """Log one live runtime update from neutral visualization items."""
        resolved_payloads = {} if payloads is None else payloads
        for semantic_event in update.semantic_events:
            if isinstance(semantic_event, GroundAlignmentMetadata):
                self._log_ground_alignment(stream, metadata=semantic_event)
            if isinstance(semantic_event, TrajectoryAlignmentArtifact):
                self._log_trajectory_alignment(stream, alignment=semantic_event)
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
                if item.role == ROLE_RECONSTRUCTION_POINT_CLOUD:
                    self._log_reconstruction_point_cloud_item(stream, item)
                elif item.role == ROLE_SOURCE_REFERENCE_POINT_CLOUD:
                    self._log_source_reference_point_cloud_item(stream, item)
                elif item.role in {ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD, ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD}:
                    self._log_slam_aligned_point_cloud_item(stream, item)
                else:
                    self._log_pointcloud_item(stream, item, payloads=payloads)
            case VisualizationIntent.TRAJECTORY:
                self._log_trajectory_item(stream, item)
            case VisualizationIntent.POSE_TRANSFORM:
                self._log_pose_item(stream, item)
            case VisualizationIntent.PINHOLE_CAMERA:
                self._log_pinhole_item(stream, item, payloads=payloads)
            case VisualizationIntent.CLEAR:
                self._log_clear_item(stream, item)
            case VisualizationIntent.MESH:
                self._log_reconstruction_mesh_item(stream, item)
            case VisualizationIntent.GROUND_PLANE:
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
        if item.role in _SOURCE_RGB_ROLES and not self.log_source_rgb:
            return
        if item.role == ROLE_MODEL_CAMERA_RGB and not self.log_camera_image_rgb:
            return
        if item.role in {ROLE_KEYFRAME_RGB, ROLE_KEYFRAME_PREVIEW} and not self.log_keyframe_camera_payloads:
            return
        if item.role in _DIAGNOSTIC_PREVIEW_ROLES and not self.log_diagnostic_preview:
            return
        entity_path = self._entity_path_for_role(item, _RGB_ENTITY_PATHS)
        if entity_path is None:
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
        if item.role == ROLE_KEYFRAME_DEPTH and not self.log_keyframe_camera_payloads:
            return
        entity_path = self._entity_path_for_role(item, _DEPTH_ENTITY_PATHS)
        if entity_path is None:
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
        entity_path = self._entity_path_for_role(item, _POINTMAP_ENTITY_PATHS)
        if entity_path is None:
            return
        self._set_item_frame_time(stream, item)
        self.log_pointcloud(
            stream,
            entity_path=entity_path,
            pointmap=pointmap,
            colors=colors,
            decimation_keep_ratio=self.point_cloud_decimation_keep_ratio,
            decimation_seed=self._decimation_seed("point_cloud", entity_path, item.frame_index, item.keyframe_index),
        )

    def _log_reconstruction_point_cloud_item(self, stream, item: VisualizationItem) -> None:
        artifact = item.artifact_refs.get(POINT_CLOUD_ARTIFACT)
        if artifact is None:
            return
        reconstruction_id = str(item.metadata.get("reconstruction_id") or "reference")
        entity_path = (
            "world/slam/point_cloud/raw"
            if reconstruction_id == "slam"
            else f"world/reconstruction/{reconstruction_id}/point_cloud"
        )
        self._log_pointcloud_ply_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=entity_path,
            warning_label="reconstruction point cloud",
            decimation_seed=self._decimation_seed("point_cloud_ply", entity_path, artifact.path),
        )

    def _log_slam_aligned_point_cloud_item(self, stream, item: VisualizationItem) -> None:
        artifact = item.artifact_refs.get(POINT_CLOUD_ARTIFACT)
        if artifact is None:
            return
        target_frame = _entity_token(str(item.metadata.get("target_frame") or item.space or "world"))
        alignment_kind = "icp" if item.role == ROLE_SLAM_ICP_ALIGNED_POINT_CLOUD else "sim3"
        entity_path = f"world/aligned/{target_frame}/slam/{alignment_kind}/point_cloud"
        self._log_pointcloud_ply_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=entity_path,
            warning_label=f"{alignment_kind.upper()}-aligned SLAM point cloud",
            decimation_seed=self._decimation_seed("point_cloud_ply", entity_path, artifact.path),
        )

    def _log_source_reference_point_cloud_item(self, stream, item: VisualizationItem) -> None:
        artifact = item.artifact_refs.get(SOURCE_POINT_CLOUD_ARTIFACT)
        if artifact is None:
            return
        metadata = self._load_source_reference_metadata(item)
        point_count = _metadata_int(metadata, "point_count")
        skipped_payloads = _metadata_int(metadata, "skipped_out_of_range_payloads")
        stats_segment = (
            f"/points_{point_count}_skipped_{skipped_payloads}"
            if point_count is not None and skipped_payloads is not None
            else ""
        )
        reference_source = _entity_token(str(item.metadata.get("reference_source") or "reference"))
        coordinate_status = _entity_token(str(item.metadata.get("coordinate_status") or "native"))
        entity_path = f"world/reference/points/{reference_source}/{coordinate_status}{stats_segment}/point_cloud"
        self._log_pointcloud_ply_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=entity_path,
            warning_label="source reference point cloud",
            decimation_seed=self._decimation_seed("point_cloud_ply", entity_path, artifact.path),
            decimation_keep_ratio=self.reference_point_cloud_decimation_keep_ratio,
        )

    def _log_reconstruction_mesh_item(self, stream, item: VisualizationItem) -> None:
        if item.role != ROLE_RECONSTRUCTION_MESH:
            return
        artifact = item.artifact_refs.get(MESH_ARTIFACT)
        if artifact is None:
            return
        reconstruction_id = str(item.metadata.get("reconstruction_id") or "reference")
        self._log_mesh_ply_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=f"world/reconstruction/{reconstruction_id}/mesh",
            warning_label="reconstruction mesh",
        )

    def _log_trajectory_item(self, stream, item: VisualizationItem) -> None:
        if item.role == ROLE_SOURCE_REFERENCE_TRAJECTORY:
            self._log_source_reference_trajectory_item(stream, item)
            return
        if item.role in {ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT, ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY}:
            self._log_slam_trajectory_artifact_item(stream, item)
            return
        if item.role != ROLE_TRACKING_TRAJECTORY or item.pose is None:
            return
        self._set_item_frame_time(stream, item)
        self._log_tracking_trajectory(stream, pose=item.pose)

    def _log_source_reference_trajectory_item(self, stream, item: VisualizationItem) -> None:
        artifact = item.artifact_refs.get(TRAJECTORY_ARTIFACT)
        if artifact is None:
            return
        reference_source = _entity_token(str(item.metadata.get("reference_source") or "reference"))
        coordinate_status = _entity_token(str(item.metadata.get("coordinate_status") or "source_native"))
        self._log_tum_trajectory_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=f"world/reference/trajectory/{reference_source}/{coordinate_status}",
            warning_label="source reference trajectory",
            target_frame=str(item.metadata.get("target_frame") or item.space or "world"),
        )

    def _log_slam_trajectory_artifact_item(self, stream, item: VisualizationItem) -> None:
        artifact = item.artifact_refs.get(TRAJECTORY_ARTIFACT)
        if artifact is None:
            return
        target_frame = _entity_token(str(item.metadata.get("target_frame") or item.space or "world"))
        entity_path = (
            "world/slam/trajectory/raw"
            if item.role == ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT
            else f"world/aligned/{target_frame}/slam/sim3/trajectory"
        )
        self._log_tum_trajectory_artifact(
            stream,
            artifact_path=artifact.path,
            entity_path=entity_path,
            warning_label="SLAM trajectory",
            target_frame=str(item.metadata.get("target_frame") or item.space or "world"),
        )

    def _log_pointcloud_ply_artifact(
        self,
        stream,
        *,
        artifact_path: Path,
        entity_path: str,
        warning_label: str,
        decimation_seed: int,
        decimation_keep_ratio: float | None = None,
    ) -> None:
        try:
            self.log_pointcloud_ply(
                stream,
                entity_path=entity_path,
                path=artifact_path,
                decimation_keep_ratio=(
                    self.point_cloud_decimation_keep_ratio if decimation_keep_ratio is None else decimation_keep_ratio
                ),
                decimation_seed=decimation_seed,
            )
        except Exception as exc:
            _LOGGER.warning("Skipping %s artifact '%s': %s", warning_label, artifact_path, exc)

    def _log_mesh_ply_artifact(
        self,
        stream,
        *,
        artifact_path: Path,
        entity_path: str,
        warning_label: str,
    ) -> None:
        try:
            self.log_mesh_ply(
                stream,
                entity_path=entity_path,
                path=artifact_path,
                decimation_keep_ratio=self.mesh_decimation_keep_ratio,
            )
        except Exception as exc:
            _LOGGER.warning("Skipping %s artifact '%s': %s", warning_label, artifact_path, exc)

    def _log_tum_trajectory_artifact(
        self,
        stream,
        *,
        artifact_path: Path,
        entity_path: str,
        warning_label: str,
        target_frame: str,
    ) -> None:
        try:
            trajectory = load_tum_trajectory(artifact_path)
            self.log_line_strip3d(
                stream,
                entity_path=entity_path,
                positions_xyz=np.asarray(trajectory.positions_xyz, dtype=np.float32),
                static=True,
            )
            poses = _trajectory_pose_transforms(trajectory, target_frame=target_frame)
            self._log_trajectory_start_axes(stream, entity_path=entity_path, poses=poses, static=True)
            self._log_trajectory_pose_transforms(
                stream,
                entity_path=entity_path,
                poses=poses,
                static=True,
            )
        except Exception as exc:
            _LOGGER.warning("Skipping %s artifact '%s': %s", warning_label, artifact_path, exc)

    def _load_source_reference_metadata(self, item: VisualizationItem) -> dict[str, object]:
        artifact = item.artifact_refs.get(SOURCE_METADATA_ARTIFACT)
        if artifact is None:
            return {}
        try:
            payload = json.loads(artifact.path.read_text(encoding="utf-8"))
        except Exception as exc:
            _LOGGER.warning("Skipping source reference metadata artifact '%s': %s", artifact.path, exc)
            return {}
        return payload if isinstance(payload, dict) else {}

    def _log_pose_item(self, stream, item: VisualizationItem) -> None:
        if item.pose is None:
            return
        entity_path = self._entity_path_for_role(item, _POSE_ENTITY_PATHS)
        if entity_path is None:
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
        entity_path = self._entity_path_for_role(item, _PINHOLE_ENTITY_PATHS)
        if entity_path is None:
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
        self.log_pinhole(
            stream,
            entity_path=entity_path,
            intrinsics=viewer_intrinsics,
            image_plane_distance=_image_plane_distance_for_role(item.role),
        )

    def _entity_path_for_role(self, item: VisualizationItem, mapping: Mapping[str, str]) -> str | None:
        template = mapping.get(item.role)
        if template is None:
            return None
        if "{keyframe_index" not in template:
            return template
        keyframe_index = self._require_keyframe_index(item)
        return None if keyframe_index is None else template.format(keyframe_index=keyframe_index)

    def _log_clear_item(self, stream, item: VisualizationItem) -> None:
        if item.role != ROLE_KEYFRAME_CAMERA_WINDOW or item.keyframe_index is None:
            return
        del stream

    def _log_ground_alignment(self, stream, *, metadata: GroundAlignmentMetadata | None) -> None:
        """Log one derived ground-plane overlay when the alignment stage completes."""
        if metadata is None or not metadata.applied:
            return
        self.log_ground_plane_patch(stream, metadata=metadata)

    def _log_trajectory_alignment(self, stream, *, alignment: TrajectoryAlignmentArtifact) -> None:
        """Log the Sim(3) alignment as a derived target-frame marker."""
        target_frame = _entity_token(alignment.target_frame)
        self.log_sim3_transform(
            stream,
            entity_path=f"world/aligned/{target_frame}/slam/sim3/source_to_target",
            rotation_matrix=np.asarray(alignment.rotation, dtype=np.float64),
            translation_xyz=np.asarray(alignment.translation, dtype=np.float64),
            scale=alignment.scale,
            axis_length=SLAM_WORLD_AXIS_LENGTH,
            static=True,
        )

    def _log_tracking_trajectory(self, stream, *, pose: FrameTransform) -> None:
        """Log one growing trajectory polyline from all observed pose estimates."""
        if not self.show_tracking_trajectory:
            return
        self._tracking_trajectory_xyz.append((float(pose.tx), float(pose.ty), float(pose.tz)))
        if not self._logged_tracking_start_axes:
            self._log_trajectory_start_axes(
                stream,
                entity_path="world/slam/trajectory/raw",
                poses=[pose],
            )
            self._logged_tracking_start_axes = True
        self.log_line_strip3d(
            stream,
            entity_path="world/slam/trajectory/raw",
            positions_xyz=np.asarray(self._tracking_trajectory_xyz, dtype=np.float32),
        )
        self._log_trajectory_pose_transforms(
            stream,
            entity_path="world/slam/trajectory/raw",
            poses=[pose],
            start_index=len(self._tracking_trajectory_xyz) - 1,
        )

    def _log_trajectory_start_axes(
        self,
        stream,
        *,
        entity_path: str,
        poses: list[FrameTransform],
        static: bool = False,
    ) -> None:
        """Log the first trajectory pose as a Transform3D axes marker."""
        if not poses:
            return
        self.log_transform(
            stream,
            entity_path=f"{entity_path}/start",
            transform=poses[0],
            axis_length=TRAJECTORY_START_AXIS_LENGTH,
            static=static,
        )

    def _log_trajectory_pose_transforms(
        self,
        stream,
        *,
        entity_path: str,
        poses: list[FrameTransform],
        start_index: int = 0,
        static: bool = False,
    ) -> None:
        """Log one transform child per trajectory pose."""
        if self.trajectory_pose_axis_length <= 0.0:
            return
        for offset, pose in enumerate(poses):
            self.log_transform(
                stream,
                entity_path=f"{entity_path}/poses/{start_index + offset:06d}",
                transform=pose,
                axis_length=self.trajectory_pose_axis_length,
                static=static,
            )

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

    def _decimation_seed(self, *parts: str | int | Path | None) -> int:
        digest = hashlib.blake2b(digest_size=8)
        digest.update(str(self.decimation_random_seed).encode("utf-8"))
        for part in parts:
            digest.update(b"\0")
            digest.update(b"" if part is None else str(part).encode("utf-8"))
        return int.from_bytes(digest.digest(), byteorder="little", signed=False)


def _entity_token(value: str) -> str:
    """Return a conservative token for one Rerun entity path component."""
    stripped = value.strip().replace(" ", "_")
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in stripped) or "reference"


def _image_plane_distance_for_role(role: str) -> float | None:
    if role == ROLE_MODEL_PINHOLE:
        return LIVE_MODEL_IMAGE_PLANE_DISTANCE
    if role == ROLE_KEYFRAME_PINHOLE:
        return KEYFRAME_IMAGE_PLANE_DISTANCE
    if role == ROLE_SOURCE_PINHOLE:
        return SOURCE_IMAGE_PLANE_DISTANCE
    return None


def _metadata_int(metadata: Mapping[str, object], key: str) -> int | None:
    value = metadata.get(key)
    return int(value) if isinstance(value, int | float) else None


def _trajectory_pose_transforms(trajectory, *, target_frame: str) -> list[FrameTransform]:
    positions = np.asarray(trajectory.positions_xyz, dtype=np.float64)
    quaternions_wxyz = np.asarray(trajectory.orientations_quat_wxyz, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"Expected trajectory positions with shape (N, 3), got {positions.shape}.")
    if quaternions_wxyz.shape != (len(positions), 4):
        raise ValueError(f"Expected one WXYZ quaternion per trajectory pose, got shape {quaternions_wxyz.shape}.")
    return [
        FrameTransform.from_quaternion_translation(
            quaternion_wxyz[[1, 2, 3, 0]],
            position_xyz,
            target_frame=target_frame,
            source_frame=CAMERA_RDF_FRAME,
        )
        for position_xyz, quaternion_wxyz in zip(positions, quaternions_wxyz, strict=True)
    ]
