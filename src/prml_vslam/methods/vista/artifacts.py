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

from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.methods.config_contracts import SlamOutputPolicy
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

_VISTA_ROTATION_PROJECTION_MAX_FROBENIUS_ERROR = 1e-2


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

    sparse_points_ref: ArtifactRef | None = None
    dense_points_ref: ArtifactRef | None = None
    pointcloud_ply = native_output_dir / "pointcloud.ply"
    if pointcloud_ply.exists() and (output_policy.emit_sparse_points or output_policy.emit_dense_points):
        point_cloud = o3d.io.read_point_cloud(str(pointcloud_ply))
        points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
        run_paths = RunArtifactPaths.build(artifact_root)
        point_cloud_path = write_point_cloud_ply(run_paths.point_cloud_path, points_xyz)
        canonical_ref = _artifact_ref(point_cloud_path, kind="ply")
        if output_policy.emit_sparse_points:
            sparse_points_ref = canonical_ref
        if output_policy.emit_dense_points:
            dense_points_ref = canonical_ref

    extras = {
        path.name: _artifact_ref(path, kind=path.suffix.lstrip(".") or "file")
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file() and path.name not in {"trajectory.npy", "pointcloud.ply", "rerun_recording.rrd"}
    }
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


__all__ = ["build_vista_artifacts"]
