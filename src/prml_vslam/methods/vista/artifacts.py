"""Native artifact normalization helpers for ViSTA-SLAM."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import open3d as o3d

from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.methods.contracts import SlamOutputPolicy
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.utils import RunArtifactPaths
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

if TYPE_CHECKING:
    import torch

_VISTA_ROTATION_PROJECTION_MAX_FROBENIUS_ERROR = 1e-2


def build_vista_artifacts(
    *,
    native_output_dir: Path,
    artifact_root: Path,
    output_policy: SlamOutputPolicy,
    timestamps_s: Sequence[float],
) -> SlamArtifacts:
    """Normalize native ViSTA outputs into repository-owned artifact contracts."""
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
        canonical_ref = ArtifactRef(
            path=point_cloud_path,
            kind="ply",
            fingerprint=f"vista-point-cloud-{len(points_xyz)}",
        )
        if output_policy.emit_sparse_points:
            sparse_points_ref = canonical_ref
        if output_policy.emit_dense_points:
            dense_points_ref = canonical_ref

    extras = {
        path.name: ArtifactRef(
            path=path.resolve(),
            kind=path.suffix.lstrip(".") or "file",
            fingerprint=f"vista-extra-{path.name}",
        )
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file() and path.name not in {"trajectory.npy", "pointcloud.ply", "rerun_recording.rrd"}
    }
    return SlamArtifacts(
        trajectory_tum=ArtifactRef(
            path=trajectory_path,
            kind="tum",
            fingerprint=f"vista-traj-{len(trajectory_se3)}",
        ),
        sparse_points_ply=sparse_points_ref,
        dense_points_ply=dense_points_ref,
        extras=extras,
    )


def _vista_numpy_array(
    value: np.ndarray | torch.Tensor,
    *,
    dtype: np.dtype[np.generic] | type[np.generic],
) -> np.ndarray:
    """Convert one upstream ViSTA array-like payload into a numpy array."""
    if isinstance(value, np.ndarray):
        return np.asarray(value, dtype=dtype)
    return np.asarray(value.detach().cpu().numpy(), dtype=dtype)


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
