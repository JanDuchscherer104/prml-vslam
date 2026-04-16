"""Shared geometry helpers used across repository-owned interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Self

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from pydantic import ConfigDict
from pytransform3d.transformations import transform, vectors_to_points

from .base_data import BaseData

if TYPE_CHECKING:
    from prml_vslam.interfaces.camera import CameraIntrinsics
    from prml_vslam.interfaces.transforms import FrameTransform


class ImageSize(BaseData):
    """Integer image resolution in pixels."""

    model_config = ConfigDict(frozen=True)

    width: int
    """Image width in pixels."""

    height: int
    """Image height in pixels."""

    @classmethod
    def from_payload(cls, payload: object) -> Self:
        """Normalize a width/height payload into an image-size model.

        Args:
            payload: Upstream payload encoded as either a mapping with
                ``width``/``height`` keys or a 2-value sequence.

        Returns:
            Normalized image size.
        """
        if isinstance(payload, dict):
            width = payload.get("width")
            height = payload.get("height")
            if isinstance(width, int) and isinstance(height, int):
                return cls(width=width, height=height)

        if isinstance(payload, list | tuple) and len(payload) == 2 and all(isinstance(value, int) for value in payload):
            return cls(width=int(payload[0]), height=int(payload[1]))

        raise TypeError("Image size must be encoded as {'width': int, 'height': int} or [width, height].")


def write_tum_trajectory(
    trajectory_path: Path,
    poses: Sequence[FrameTransform],
    timestamps: Sequence[float],
) -> Path:
    """Write a TUM trajectory file from canonical camera-to-world transforms and timestamps."""
    if len(poses) != len(timestamps):
        raise ValueError(f"Expected one timestamp per pose, got {len(timestamps)} timestamps for {len(poses)} poses.")

    trajectory_path.parent.mkdir(parents=True, exist_ok=True)
    if not poses:
        trajectory_path.write_text("", encoding="utf-8")
        return trajectory_path.resolve()

    pose_array = np.asarray([pose.to_tum_fields() for pose in poses], dtype=np.float64)
    quaternions_xyzw = pose_array[:, 3:]
    quaternion_norms = np.linalg.norm(quaternions_xyzw, axis=1, keepdims=True)
    if np.any(quaternion_norms == 0.0):
        raise ValueError("FrameTransform quaternions must be non-zero.")

    file_interface.write_tum_trajectory_file(
        trajectory_path,
        PoseTrajectory3D(
            positions_xyz=pose_array[:, :3],
            orientations_quat_wxyz=np.roll(quaternions_xyzw / quaternion_norms, 1, axis=1),
            timestamps=np.asarray(timestamps, dtype=np.float64),
        ),
    )
    return trajectory_path.resolve()


def load_tum_trajectory(path: Path) -> PoseTrajectory3D:
    """Load a TUM trajectory file into an `evo` pose trajectory."""
    if path.stat().st_size == 0:
        raise ValueError(f"TUM trajectory file '{path}' is empty.")

    trajectory = file_interface.read_tum_trajectory_file(path)
    valid, details = trajectory.check()
    if not valid:
        raise ValueError(f"Invalid TUM trajectory '{path}': {details}")
    return trajectory


def _import_open3d() -> object:
    try:
        import open3d as o3d
    except ModuleNotFoundError as exc:
        raise RuntimeError("Point-cloud PLY I/O requires the repository Open3D dependency.") from exc
    return o3d


def write_point_cloud_ply(path: Path, points_xyz: np.ndarray) -> Path:
    """Write an XYZ point cloud to PLY using the repository's Open3D dependency."""
    positions = np.asarray(points_xyz, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"Expected point cloud shape (N, 3), got {positions.shape}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    o3d = _import_open3d()
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(positions)
    if not o3d.io.write_point_cloud(str(path), point_cloud, write_ascii=True):
        raise RuntimeError(f"Failed to write point cloud to '{path}'.")
    return path.resolve()


def load_point_cloud_ply(path: Path) -> np.ndarray:
    """Load an XYZ point cloud from PLY using the repository's Open3D dependency."""
    if not path.exists():
        raise FileNotFoundError(f"Point cloud '{path}' does not exist.")
    o3d = _import_open3d()
    point_cloud = o3d.io.read_point_cloud(str(path))
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.ndim != 2 or (points_xyz.size > 0 and points_xyz.shape[1] != 3):
        raise ValueError(f"Expected Open3D to return shape (N, 3) for '{path}', got {points_xyz.shape}.")
    if points_xyz.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    return points_xyz


def transform_points_world_camera(
    points_xyz_camera: np.ndarray,
    pose_world_camera: FrameTransform,
) -> np.ndarray:
    """Transform camera-frame XYZ points into world coordinates."""
    points = np.asarray(points_xyz_camera, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected point array shape (N, 3), got {points.shape}.")
    if len(points) == 0:
        return np.empty((0, 3), dtype=np.float64)
    return transform(pose_world_camera.as_matrix(), vectors_to_points(points))[:, :3]


def pointmap_from_depth(
    depth_map_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    *,
    stride_px: int = 1,
) -> np.ndarray:
    """Unproject a depth raster into a sampled camera-frame pointmap."""
    depth = np.asarray(depth_map_m, dtype=np.float32)
    if depth.ndim != 2:
        raise ValueError(f"Expected a 2D depth map, got shape {depth.shape}.")
    if stride_px < 1:
        raise ValueError(f"Expected stride_px >= 1, got {stride_px}.")
    if intrinsics.fx == 0.0 or intrinsics.fy == 0.0:
        raise ValueError("Camera intrinsics must have non-zero focal lengths.")

    sampled_depth = depth[::stride_px, ::stride_px]
    if not np.all(np.isfinite(sampled_depth)):
        raise ValueError("Depth map must contain only finite values.")

    rows_px = np.arange(0, depth.shape[0], stride_px, dtype=np.float32)
    cols_px = np.arange(0, depth.shape[1], stride_px, dtype=np.float32)
    grid_y_px, grid_x_px = np.meshgrid(rows_px, cols_px, indexing="ij")
    return np.stack(
        [
            (grid_x_px - intrinsics.cx) / intrinsics.fx * sampled_depth,
            (grid_y_px - intrinsics.cy) / intrinsics.fy * sampled_depth,
            sampled_depth,
        ],
        axis=-1,
    ).astype(np.float32)


__all__ = [
    "ImageSize",
    "load_point_cloud_ply",
    "load_tum_trajectory",
    "pointmap_from_depth",
    "transform_points_world_camera",
    "write_point_cloud_ply",
    "write_tum_trajectory",
]
