"""Native artifact normalization helpers for ViSTA-SLAM.

This module handles end-of-run native outputs only. In particular, it
normalizes exported ViSTA trajectories and fused world-space point clouds. It
does not own live camera-local pointmap semantics, which remain in
``SlamUpdate.pointmap`` and the streaming Rerun sink.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import open3d as o3d

from prml_vslam.interfaces import CameraIntrinsicsSeries, FrameTransform
from prml_vslam.interfaces.artifacts import ArtifactRef, artifact_ref
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.methods.stage.backend_config import SlamOutputPolicy
from prml_vslam.methods.vista.artifact_io import (
    load_vista_confidences,
    load_vista_intrinsics_matrices,
    load_vista_view_names,
)
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

_VISTA_ROTATION_PROJECTION_MAX_FROBENIUS_ERROR = 1e-2
_VISTA_MODEL_RASTER_SIZE_PX = 224
_POINT_CLOUD_CONFIDENCES_FILENAME = "point_cloud_confidences.npz"


def build_vista_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    timestamps_s: Sequence[float],
    num_processed_frames: int = 0,
    num_dense_points: int = 0,
) -> SlamArtifacts:
    """Normalize native ViSTA exports into repository-owned artifact contracts.

    The preserved native output directory contains a different geometry surface
    from the live session API:

    - live/session readback uses scaled camera-local pointmaps under posed
      camera entities;
    - ``pointcloud.ply`` is an already fused world-space dense cloud emitted by
      upstream export.

    This function only normalizes the exported artifact surface.

    Args:
        native_output_dir: Directory containing native ViSTA exports.
        artifact_root: Run-owned artifact root for canonical output paths.
        output_policy: Whether dense/sparse geometry should be exposed.
        timestamps_s: Per-keyframe timestamps; ``len(timestamps_s)`` is the
            accepted keyframe count.
        num_processed_frames: Source frames consumed by the runtime.
        num_dense_points: Dense pointmap samples accumulated over the run.
    """
    trajectory_npy = native_output_dir / "trajectory.npy"
    if not trajectory_npy.exists():
        raise RuntimeError(f"Expected trajectory file not found: '{trajectory_npy}'.")
    trajectory_se3 = np.load(trajectory_npy).astype(np.float64)
    poses = [_frame_transform_from_vista_pose(transform) for transform in trajectory_se3]
    trajectory_path = write_tum_trajectory(artifact_root / "slam" / "trajectory.tum", poses, timestamps_s)
    run_paths = RunArtifactPaths.build(artifact_root)

    sparse_points_ref: ArtifactRef | None = None
    dense_points_ref: ArtifactRef | None = None
    confidence_ref: ArtifactRef | None = None
    pointcloud_ply = native_output_dir / "pointcloud.ply"
    point_cloud_export = _build_unfiltered_cloud_export(native_output_dir=native_output_dir)
    if point_cloud_export is None and pointcloud_ply.exists():
        point_cloud_export = _load_native_point_cloud(pointcloud_ply)
    if point_cloud_export is not None and (output_policy.emit_sparse_points or output_policy.emit_dense_points):
        point_cloud_path = write_point_cloud_ply(
            run_paths.point_cloud_path,
            point_cloud_export.points_xyz,
            colors_rgb=point_cloud_export.colors_rgb,
        )
        canonical_ref = artifact_ref(point_cloud_path, kind="ply")
        if point_cloud_export.confidences is not None:
            confidence_path = _write_point_cloud_confidences(
                artifact_root=artifact_root,
                confidences=point_cloud_export.confidences,
                confidence_threshold=point_cloud_export.confidence_threshold,
                source_shape=point_cloud_export.source_shape,
            )
            confidence_ref = artifact_ref(confidence_path, kind="npz")
        if output_policy.emit_sparse_points:
            sparse_points_ref = canonical_ref
        if output_policy.emit_dense_points:
            dense_points_ref = canonical_ref

    estimated_intrinsics_ref: ArtifactRef | None = None
    native_intrinsics_path = native_output_dir / "intrinsics.npy"
    if native_intrinsics_path.exists():
        estimated_intrinsics = _build_estimated_intrinsics_series(
            native_intrinsics_path=native_intrinsics_path,
            native_output_dir=native_output_dir,
            timestamps_s=timestamps_s,
        )
        run_paths.estimated_intrinsics_path.parent.mkdir(parents=True, exist_ok=True)
        run_paths.estimated_intrinsics_path.write_text(estimated_intrinsics.model_dump_json(indent=2), encoding="utf-8")
        estimated_intrinsics_ref = artifact_ref(run_paths.estimated_intrinsics_path, kind="json")

    extras = {
        path.name: artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file() and path.name not in {"trajectory.npy", "rerun_recording.rrd"}
    }
    if confidence_ref is not None:
        extras[confidence_ref.path.name] = confidence_ref
    if estimated_intrinsics_ref is not None:
        extras[run_paths.estimated_intrinsics_path.name] = estimated_intrinsics_ref
    materialized_dense_count = (
        len(point_cloud_export.points_xyz) if point_cloud_export is not None and dense_points_ref is not None else 0
    )
    return SlamArtifacts(
        trajectory_tum=artifact_ref(trajectory_path, kind="tum"),
        sparse_points_ply=sparse_points_ref,
        dense_points_ply=dense_points_ref,
        extras=extras,
        num_processed_frames=num_processed_frames,
        num_keyframes=len(timestamps_s),
        # ViSTA fuses dense geometry only; mirror the dense count into sparse
        # so a sparse-only output policy still lights up the dashboard.
        num_sparse_points=max(num_dense_points, materialized_dense_count) if sparse_points_ref is not None else 0,
        num_dense_points=max(num_dense_points, materialized_dense_count) if dense_points_ref is not None else 0,
    )


class _VistaPointCloudExport:
    def __init__(
        self,
        *,
        points_xyz: np.ndarray,
        colors_rgb: np.ndarray | None = None,
        confidences: np.ndarray | None = None,
        confidence_threshold: float | None = None,
        source_shape: tuple[int, int, int] | None = None,
    ) -> None:
        self.points_xyz = points_xyz
        self.colors_rgb = colors_rgb
        self.confidences = confidences
        self.confidence_threshold = confidence_threshold
        self.source_shape = source_shape


def _build_unfiltered_cloud_export(*, native_output_dir: Path) -> _VistaPointCloudExport | None:
    depths_path = native_output_dir / "depths.npy"
    scales_path = native_output_dir / "scales.npy"
    intrinsics_path = native_output_dir / "intrinsics.npy"
    trajectory_path = native_output_dir / "trajectory.npy"
    confidences_path = native_output_dir / "confs.npz"
    required_paths = (depths_path, scales_path, intrinsics_path, trajectory_path, confidences_path)
    if not all(path.exists() for path in required_paths):
        return None

    depths = np.asarray(np.load(depths_path), dtype=np.float64)
    scales = np.asarray(np.load(scales_path), dtype=np.float64).reshape(-1)
    intrinsics = load_vista_intrinsics_matrices(intrinsics_path, expected_length=len(scales))
    poses = np.asarray(np.load(trajectory_path), dtype=np.float64)
    confidence_maps, confidence_threshold = load_vista_confidences(confidences_path)
    _validate_native_cloud_arrays(
        depths=depths,
        scales=scales,
        intrinsics=intrinsics,
        poses=poses,
        confidence_maps=confidence_maps,
    )
    points_xyz, valid_mask = _vista_world_points(
        depths=depths,
        scales=scales,
        intrinsics=intrinsics,
        poses=poses,
    )
    confidences = confidence_maps[valid_mask].astype(np.float32)
    colors_rgb = _load_unfiltered_cloud_colors(native_output_dir / "images.npy", valid_mask=valid_mask)
    return _VistaPointCloudExport(
        points_xyz=points_xyz,
        colors_rgb=colors_rgb,
        confidences=confidences,
        confidence_threshold=confidence_threshold,
        source_shape=tuple(int(dim) for dim in confidence_maps.shape),
    )


def _validate_native_cloud_arrays(
    *,
    depths: np.ndarray,
    scales: np.ndarray,
    intrinsics: np.ndarray,
    poses: np.ndarray,
    confidence_maps: np.ndarray,
) -> None:
    if depths.ndim != 3:
        raise ValueError(f"Expected native ViSTA depths shape (N, H, W), got {depths.shape}.")
    if scales.shape != (depths.shape[0],):
        raise ValueError(f"Expected one native ViSTA scale per depth map, got {scales.shape}.")
    if intrinsics.shape != (depths.shape[0], 3, 3):
        raise ValueError(f"Expected native ViSTA intrinsics shape ({depths.shape[0]}, 3, 3), got {intrinsics.shape}.")
    if poses.shape != (depths.shape[0], 4, 4):
        raise ValueError(f"Expected native ViSTA trajectory shape ({depths.shape[0]}, 4, 4), got {poses.shape}.")
    if confidence_maps.shape != depths.shape:
        raise ValueError(f"Expected native ViSTA confidences shape {depths.shape}, got {confidence_maps.shape}.")


def _vista_world_points(
    *,
    depths: np.ndarray,
    scales: np.ndarray,
    intrinsics: np.ndarray,
    poses: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    scaled_depths = depths * scales[:, None, None]
    valid_mask = np.isfinite(scaled_depths) & (scaled_depths > 0.0)
    keyframe_count, height, width = scaled_depths.shape
    pixel_x, pixel_y = np.meshgrid(np.arange(width, dtype=np.float64), np.arange(height, dtype=np.float64))
    pixel_hom = np.stack([pixel_x, pixel_y, np.ones_like(pixel_x)], axis=-1).reshape(-1, 3)
    local_points = np.empty((keyframe_count, height * width, 3), dtype=np.float64)
    for index in range(keyframe_count):
        rays_camera = np.linalg.solve(intrinsics[index], pixel_hom.T).T
        local_points[index] = rays_camera * scaled_depths[index].reshape(-1, 1)
    local_points_hom = np.concatenate(
        [local_points, np.ones((keyframe_count, height * width, 1), dtype=np.float64)],
        axis=-1,
    )
    world_points = np.matmul(local_points_hom, np.swapaxes(poses, 1, 2))[..., :3].reshape(
        keyframe_count, height, width, 3
    )
    return world_points[valid_mask], valid_mask


def _load_unfiltered_cloud_colors(path: Path, *, valid_mask: np.ndarray) -> np.ndarray | None:
    if not path.exists():
        return None
    images = np.asarray(np.load(path), dtype=np.float64)
    if images.shape != (*valid_mask.shape, 3):
        raise ValueError(f"Expected native ViSTA images shape {(*valid_mask.shape, 3)}, got {images.shape}.")
    return images[valid_mask]


def _write_point_cloud_confidences(
    *,
    artifact_root: Path,
    confidences: np.ndarray,
    confidence_threshold: float | None,
    source_shape: tuple[int, int, int] | None,
) -> Path:
    path = artifact_root / "slam" / _POINT_CLOUD_CONFIDENCES_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        confidence=np.asarray(confidences, dtype=np.float32).reshape(-1),
        confidence_threshold=np.asarray(np.nan if confidence_threshold is None else confidence_threshold),
        source_shape=np.asarray(() if source_shape is None else source_shape, dtype=np.int64),
    )
    return path.resolve()


def _load_native_point_cloud(path: Path) -> _VistaPointCloudExport:
    point_cloud = o3d.io.read_point_cloud(path)
    return _VistaPointCloudExport(
        points_xyz=np.asarray(point_cloud.points, dtype=np.float64),
        colors_rgb=np.asarray(point_cloud.colors, dtype=np.float64) if point_cloud.has_colors() else None,
    )


def _frame_transform_from_vista_pose(matrix: np.ndarray) -> FrameTransform:
    """Normalize one upstream ViSTA pose matrix into the canonical repo transform DTO."""
    matrix_array = np.asarray(matrix, dtype=np.float64)
    if matrix_array.shape != (4, 4):
        raise ValueError(f"Expected a 4x4 pose matrix, got shape {matrix_array.shape}.")
    if not np.allclose(matrix_array[3], np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64), atol=1e-6):
        raise ValueError("ViSTA pose matrices must have a final row of [0, 0, 0, 1].")
    normalized = matrix_array.copy()
    normalized[:3, :3] = project_rotation_to_so3(
        normalized[:3, :3],
        max_frobenius_error=_VISTA_ROTATION_PROJECTION_MAX_FROBENIUS_ERROR,
    )
    return FrameTransform.from_matrix(normalized)


def _build_estimated_intrinsics_series(
    *,
    native_intrinsics_path: Path,
    native_output_dir: Path,
    timestamps_s: Sequence[float],
) -> CameraIntrinsicsSeries:
    intrinsics = load_vista_intrinsics_matrices(native_intrinsics_path, expected_length=len(timestamps_s))
    if len(intrinsics) != len(timestamps_s):
        raise ValueError(
            "Expected one native ViSTA intrinsics matrix per trajectory timestamp, "
            f"got {len(intrinsics)} intrinsics and {len(timestamps_s)} timestamps."
        )
    return CameraIntrinsicsSeries.from_matrices(
        intrinsics,
        raster_space="vista_model",
        source="native/intrinsics.npy",
        method_id="vista",
        width_px=_VISTA_MODEL_RASTER_SIZE_PX,
        height_px=_VISTA_MODEL_RASTER_SIZE_PX,
        keyframe_indices=list(range(len(intrinsics))),
        timestamps_ns=[int(round(float(timestamp_s) * 1e9)) for timestamp_s in timestamps_s],
        view_names=load_vista_view_names(native_output_dir / "view_graph.npz", count=len(intrinsics)),
        metadata={
            "native_intrinsics_path": native_intrinsics_path.name,
            "preprocessing": "vista_image_only_center_crop_resize",
        },
    )


__all__ = ["build_vista_artifacts"]
