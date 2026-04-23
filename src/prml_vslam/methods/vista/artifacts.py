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
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.methods.config_contracts import SlamOutputPolicy
from prml_vslam.methods.vista.artifact_io import load_vista_intrinsics_matrices, load_vista_view_names
from prml_vslam.pipeline.contracts.provenance import ArtifactRef
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

_VISTA_ROTATION_PROJECTION_MAX_FROBENIUS_ERROR = 1e-2
_VISTA_MODEL_RASTER_SIZE_PX = 224


def _artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    """Build one stable artifact reference for a normalized ViSTA output."""
    resolved_path = path.resolve()
    return ArtifactRef(
        path=resolved_path,
        kind=kind,
        fingerprint=stable_hash({"path": str(resolved_path), "kind": kind}),
    )


def build_vista_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    timestamps_s: Sequence[float],
) -> SlamArtifacts:
    """Normalize native ViSTA exports into repository-owned artifact contracts.

    The preserved native output directory contains a different geometry surface
    from the live session API:

    - live/session readback uses scaled camera-local pointmaps under posed
      camera entities;
    - ``pointcloud.ply`` is an already fused world-space dense cloud emitted by
      upstream export.

    This function only normalizes the exported artifact surface.
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
    pointcloud_ply = native_output_dir / "pointcloud.ply"
    if pointcloud_ply.exists() and (output_policy.emit_sparse_points or output_policy.emit_dense_points):
        point_cloud = o3d.io.read_point_cloud(pointcloud_ply)
        points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
        colors_rgb = np.asarray(point_cloud.colors, dtype=np.float64) if point_cloud.has_colors() else None
        point_cloud_path = write_point_cloud_ply(run_paths.point_cloud_path, points_xyz, colors_rgb=colors_rgb)
        canonical_ref = _artifact_ref(point_cloud_path, kind="ply")
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
        estimated_intrinsics_ref = _artifact_ref(run_paths.estimated_intrinsics_path, kind="json")

    extras = {
        path.name: _artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file() and path.name not in {"trajectory.npy", "pointcloud.ply", "rerun_recording.rrd"}
    }
    if estimated_intrinsics_ref is not None:
        extras[run_paths.estimated_intrinsics_path.name] = estimated_intrinsics_ref
    return SlamArtifacts(
        trajectory_tum=_artifact_ref(trajectory_path, kind="tum"),
        sparse_points_ply=sparse_points_ref,
        dense_points_ply=dense_points_ref,
        extras=extras,
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
