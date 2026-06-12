"""Shared geometry helpers used across repository-owned interfaces."""

from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import open3d as o3d
from evo.core.trajectory import PoseTrajectory3D  # type: ignore[import-untyped]
from evo.tools import file_interface  # type: ignore[import-untyped]
from pytransform3d.transformations import transform, vectors_to_points

from prml_vslam.utils.console import get_console

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from prml_vslam.interfaces.camera import CameraIntrinsics
    from prml_vslam.interfaces.transforms import FrameTransform


# Default reference-cloud sampling values used by config models and helper fallbacks.
DEFAULT_REFERENCE_CLOUD_DEPTH_STRIDE_PX = 8
DEFAULT_REFERENCE_CLOUD_MAX_POINTS = 100_000
DEFAULT_REFERENCE_CLOUD_RANDOM_SEED = 17


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
    trajectory = _normalize_trajectory_quaternions(trajectory)
    valid, details = trajectory.check()
    if not valid:
        raise ValueError(f"Invalid TUM trajectory '{path}': {details}")
    return trajectory


def _normalize_trajectory_quaternions(trajectory: PoseTrajectory3D) -> PoseTrajectory3D:
    quaternions = np.asarray(trajectory.orientations_quat_wxyz, dtype=np.float64)
    norms = np.linalg.norm(quaternions, axis=1, keepdims=True)

    if np.any(np.isclose(norms, 0.0, atol=1e-6)):
        get_console("geometry").warn("Found zero-norm quaternion in trajectory.")
        return trajectory

    return PoseTrajectory3D(
        positions_xyz=np.asarray(trajectory.positions_xyz, dtype=np.float64),
        orientations_quat_wxyz=quaternions / norms,
        timestamps=np.asarray(trajectory.timestamps, dtype=np.float64),
    )


def write_point_cloud_ply(path: Path, points_xyz: np.ndarray, colors_rgb: np.ndarray | None = None) -> Path:
    """Write an XYZ point cloud to PLY using the repository's Open3D dependency."""
    positions = np.asarray(points_xyz, dtype=np.float64)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError(f"Expected point cloud shape (N, 3), got {positions.shape}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(positions)
    if colors_rgb is not None:
        point_cloud.colors = o3d.utility.Vector3dVector(
            _normalize_point_colors(colors_rgb, expected_length=len(positions))
        )
    if not o3d.io.write_point_cloud(path, point_cloud, write_ascii=True):
        raise RuntimeError(f"Failed to write point cloud to '{path}'.")
    return path.resolve()


def load_point_cloud_ply(path: Path) -> np.ndarray:
    """Load an XYZ point cloud from PLY using the repository's Open3D dependency."""
    if not path.exists():
        raise FileNotFoundError(f"Point cloud '{path}' does not exist.")
    point_cloud = o3d.io.read_point_cloud(path)
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.ndim != 2 or (points_xyz.size > 0 and points_xyz.shape[1] != 3):
        raise ValueError(f"Expected Open3D to return shape (N, 3) for '{path}', got {points_xyz.shape}.")
    if points_xyz.size == 0:
        return np.empty((0, 3), dtype=np.float64)
    return points_xyz


def load_point_cloud_ply_with_colors(path: Path) -> tuple[np.ndarray, np.ndarray | None]:
    """Load XYZ points and optional RGB colors from PLY using Open3D."""
    if not path.exists():
        raise FileNotFoundError(f"Point cloud '{path}' does not exist.")
    point_cloud = o3d.io.read_point_cloud(path)
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.ndim != 2 or (points_xyz.size > 0 and points_xyz.shape[1] != 3):
        raise ValueError(f"Expected Open3D to return shape (N, 3) for '{path}', got {points_xyz.shape}.")
    colors_rgb = np.asarray(point_cloud.colors, dtype=np.float64) if point_cloud.has_colors() else None
    if colors_rgb is not None and colors_rgb.shape != points_xyz.shape:
        raise ValueError(f"Expected point colors to match point shape {points_xyz.shape}, got {colors_rgb.shape}.")
    if points_xyz.size == 0:
        return np.empty((0, 3), dtype=np.float64), None if colors_rgb is None else np.empty((0, 3), dtype=np.float64)
    return points_xyz, colors_rgb


def _normalize_point_colors(colors_rgb: np.ndarray, *, expected_length: int) -> np.ndarray:
    colors = np.asarray(colors_rgb)
    if colors.ndim != 2 or colors.shape != (expected_length, 3):
        raise ValueError(f"Expected point colors shape ({expected_length}, 3), got {colors.shape}.")
    normalized = colors.astype(np.float64)
    if np.issubdtype(colors.dtype, np.integer):
        normalized = normalized / 255.0
    if np.any(normalized < 0.0) or np.any(normalized > 1.0):
        raise ValueError("Point colors must be in [0, 1] for floats or [0, 255] for integers.")
    return normalized


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


def depth_map_to_world_points(
    depth_map_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    T_world_camera: FrameTransform,
    *,
    rgb: np.ndarray | None = None,
    depth_stride_px: int = DEFAULT_REFERENCE_CLOUD_DEPTH_STRIDE_PX,
    device: str = "CPU:0",
) -> tuple[np.ndarray, np.ndarray | None]:
    """Unproject sampled depth into world-frame XYZ points and optional RGB.

    This helper centralizes the dense-depth preprocessing used by dataset
    reference-cloud builders. The pinhole unprojection follows OpenCV RGB-D
    ``depthTo3d`` semantics
    (https://docs.opencv.org/3.4/d2/d3a/group__rgbd.html), the frame-wise
    fusion mirrors ViSTA-SLAM's dense-depth reconstruction path in
    ``external/vista-slam/vista_slam/eval/eval_recon.py``, and the explicit
    ``device`` string maps to Open3D tensor devices such as ``CPU:0`` or
    ``CUDA:0``
    (https://www.open3d.org/docs/release/python_api/open3d.t.geometry.PointCloud.html).

    Args:
        depth_map_m: Depth map in meters with shape ``(H, W)``.
        intrinsics: Pinhole intrinsics for the depth/RGB raster.
        T_world_camera: Repository transform ``world <- camera_rdf``.
        rgb: Optional RGB image with shape ``(H, W, 3)`` and ``uint8`` values.
        depth_stride_px: Pixel stride applied before unprojection.
        device: Open3D tensor device string. ``CPU:0`` is deterministic default;
            CUDA devices are opt-in and must be available.

    Returns:
        Tuple of ``(points_xyz_world, colors_rgb)``. Colors are ``uint8`` when
        ``rgb`` is provided, otherwise ``None``.
    """
    depth = np.asarray(depth_map_m, dtype=np.float32)
    if depth.ndim != 2:
        raise ValueError(f"Expected a 2D depth map, got shape {depth.shape}.")
    if depth_stride_px < 1:
        raise ValueError(f"Expected depth_stride_px >= 1, got {depth_stride_px}.")
    sampled_depth = depth[::depth_stride_px, ::depth_stride_px]
    valid_mask = np.isfinite(sampled_depth) & (sampled_depth > 0.0)
    if not np.any(valid_mask):
        return np.empty((0, 3), dtype=np.float64), _empty_colors(rgb)

    colors_rgb = _sample_rgb_colors(rgb, valid_mask=valid_mask, depth_stride_px=depth_stride_px)
    if _normalized_open3d_device(device).upper().startswith("CPU"):
        safe_depth = np.where(np.isfinite(depth), depth, 0.0).astype(np.float32, copy=False)
        pointmap = pointmap_from_depth(safe_depth, intrinsics, stride_px=depth_stride_px)
        points_xyz_camera = pointmap.reshape(-1, 3)[valid_mask.reshape(-1)]
        return transform_points_world_camera(points_xyz_camera, T_world_camera), colors_rgb

    return _depth_map_to_world_points_tensor(
        sampled_depth,
        valid_mask=valid_mask,
        intrinsics=intrinsics,
        T_world_camera=T_world_camera,
        depth_stride_px=depth_stride_px,
        device=device,
    ), colors_rgb


def sample_point_cloud_random(
    points_xyz: np.ndarray,
    colors_rgb: np.ndarray | None = None,
    *,
    max_points: int | None = DEFAULT_REFERENCE_CLOUD_MAX_POINTS,
    seed: int = DEFAULT_REFERENCE_CLOUD_RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Deterministically cap a fused point cloud without changing frame selection.

    The policy is intentionally point-level only: every upstream observation can
    contribute before this cap is applied. This matches the benchmark-artifact
    need to reduce dense depth-map point volume while preserving the method
    input frame set; Open3D voxel downsampling remains separate for ICP-style
    alignment workflows
    (https://www.open3d.org/docs/latest/tutorial/pipelines/icp_registration.html).
    """
    points = np.asarray(points_xyz, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"Expected point cloud shape (N, 3), got {points.shape}.")
    colors = None
    if colors_rgb is not None:
        colors = np.asarray(colors_rgb, dtype=np.uint8)
        if colors.shape != points.shape:
            raise ValueError(f"Expected colors shape {points.shape}, got {colors.shape}.")
    if max_points is None or len(points) <= max_points:
        return points, colors
    if max_points < 1:
        raise ValueError(f"Expected max_points >= 1, got {max_points}.")
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(points), size=max_points, replace=False)
    indices.sort()
    return points[indices], None if colors is None else colors[indices]


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

    u_px = np.arange(0, depth.shape[1], stride_px, dtype=np.float32)
    v_px = np.arange(0, depth.shape[0], stride_px, dtype=np.float32)
    u_grid, v_grid = np.meshgrid(u_px, v_px)
    points_xyz_camera = np.empty((*sampled_depth.shape, 3), dtype=np.float32)
    points_xyz_camera[..., 0] = (u_grid - np.float32(intrinsics.cx)) * sampled_depth / np.float32(intrinsics.fx)
    points_xyz_camera[..., 1] = (v_grid - np.float32(intrinsics.cy)) * sampled_depth / np.float32(intrinsics.fy)
    points_xyz_camera[..., 2] = sampled_depth
    return points_xyz_camera


def _normalized_open3d_device(device: str) -> str:
    resolved = o3d.core.Device(device)
    device_value = str(resolved)
    if device_value.upper().startswith("CUDA") and not o3d.core.cuda.is_available():
        raise RuntimeError(f"Open3D CUDA device '{device_value}' was requested but CUDA is unavailable.")
    return device_value


def _depth_map_to_world_points_tensor(
    sampled_depth: np.ndarray,
    *,
    valid_mask: np.ndarray,
    intrinsics: CameraIntrinsics,
    T_world_camera: FrameTransform,
    depth_stride_px: int,
    device: str,
) -> np.ndarray:
    o3d_device = o3d.core.Device(_normalized_open3d_device(device))
    dtype = o3d.core.Dtype.Float32
    valid_flat = valid_mask.reshape(-1)
    depth_tensor = o3d.core.Tensor(sampled_depth.reshape(-1, 1), dtype=dtype, device=o3d_device)[valid_flat]
    u_px = np.arange(0, sampled_depth.shape[1] * depth_stride_px, depth_stride_px, dtype=np.float32)
    v_px = np.arange(0, sampled_depth.shape[0] * depth_stride_px, depth_stride_px, dtype=np.float32)
    u_grid, v_grid = np.meshgrid(u_px, v_px)
    u_tensor = o3d.core.Tensor(u_grid.reshape(-1, 1), dtype=dtype, device=o3d_device)[valid_flat]
    v_tensor = o3d.core.Tensor(v_grid.reshape(-1, 1), dtype=dtype, device=o3d_device)[valid_flat]
    x_tensor = (u_tensor - np.float32(intrinsics.cx)) * depth_tensor / np.float32(intrinsics.fx)
    y_tensor = (v_tensor - np.float32(intrinsics.cy)) * depth_tensor / np.float32(intrinsics.fy)
    points_xyz_camera = o3d.core.concatenate([x_tensor, y_tensor, depth_tensor], axis=1)
    ones = o3d.core.Tensor.ones((points_xyz_camera.shape[0], 1), dtype, o3d_device)
    points_h = o3d.core.concatenate([points_xyz_camera, ones], axis=1)
    T_tensor = o3d.core.Tensor(T_world_camera.as_matrix().astype(np.float32), dtype=dtype, device=o3d_device)
    return points_h.matmul(T_tensor.T())[:, :3].cpu().numpy().astype(np.float64, copy=False)


def yaw_similarity_align(
    estimate_xyz: NDArray[np.float64],
    reference_xyz: NDArray[np.float64],
    *,
    up_axis: tuple[float, float, float] | NDArray[np.float64] = (0.0, 1.0, 0.0),
    correct_scale: bool = True,
) -> tuple[float, NDArray[np.float64], NDArray[np.float64]]:
    """Gravity-locked similarity mapping ``estimate`` onto ``reference``.

    Solves ``min_{s, R, t} sum_i ||reference_i - (s R estimate_i + t)||^2`` where
    ``R`` is constrained to a pure rotation about ``up_axis`` (yaw only). Because
    ``R`` fixes ``up_axis`` exactly, the result can never flip a gravity-aligned,
    near-planar trajectory upside down (the failure mode of full Umeyama on
    planar inputs). Inputs must be index-aligned (already timestamp-associated).

    Returns ``(scale, rotation_3x3, translation_3)``.
    """
    estimate = np.asarray(estimate_xyz, dtype=np.float64).reshape(-1, 3)
    reference = np.asarray(reference_xyz, dtype=np.float64).reshape(-1, 3)
    if estimate.shape != reference.shape:
        raise ValueError(f"yaw_similarity_align needs matching shapes, got {estimate.shape} and {reference.shape}.")
    up = np.asarray(up_axis, dtype=np.float64).reshape(3)
    up_norm = float(np.linalg.norm(up))
    if up_norm == 0.0:
        raise ValueError("yaw_similarity_align up_axis must be non-zero.")
    up = up / up_norm
    identity = np.eye(3, dtype=np.float64)
    if len(estimate) == 0:
        return 1.0, identity, np.zeros(3, dtype=np.float64)

    estimate_centroid = estimate.mean(axis=0)
    reference_centroid = reference.mean(axis=0)
    estimate_centered = estimate - estimate_centroid
    reference_centered = reference - reference_centroid

    seed = np.array([1.0, 0.0, 0.0]) if abs(up[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    plane_x = seed - np.dot(seed, up) * up
    plane_x /= np.linalg.norm(plane_x)
    plane_y = np.cross(up, plane_x)

    estimate_x = estimate_centered @ plane_x
    estimate_y = estimate_centered @ plane_y
    reference_x = reference_centered @ plane_x
    reference_y = reference_centered @ plane_y
    cross_term = float(np.sum(estimate_x * reference_y - estimate_y * reference_x))
    dot_term = float(np.sum(estimate_x * reference_x + estimate_y * reference_y))
    theta = math.atan2(cross_term, dot_term)

    skew_up = np.array(
        [[0.0, -up[2], up[1]], [up[2], 0.0, -up[0]], [-up[1], up[0], 0.0]],
        dtype=np.float64,
    )
    rotation = math.cos(theta) * identity + math.sin(theta) * skew_up + (1.0 - math.cos(theta)) * np.outer(up, up)

    scale = 1.0
    if correct_scale:
        denominator = float(np.sum(estimate_centered**2))
        if denominator > 0.0:
            scale = float(np.sum(reference_centered * (estimate_centered @ rotation.T)) / denominator)
    translation = reference_centroid - scale * (rotation @ estimate_centroid)
    return scale, rotation, translation


def apply_similarity_to_trajectory(
    trajectory: PoseTrajectory3D,
    *,
    scale: float,
    rotation: NDArray[np.float64],
    translation: NDArray[np.float64],
) -> PoseTrajectory3D:
    """Return a copy of ``trajectory`` transformed by ``p -> s R p + t``.

    Rotations are left-multiplied by ``R`` and positions follow the similarity,
    matching the convention of the trajectory Sim(3) artifact.
    """
    from prml_vslam.interfaces.transforms import FrameTransform

    rotation = np.asarray(rotation, dtype=np.float64).reshape(3, 3)
    translation = np.asarray(translation, dtype=np.float64).reshape(3)
    poses = [np.asarray(pose, dtype=np.float64) for pose in trajectory.poses_se3]
    if not poses:
        return PoseTrajectory3D(
            positions_xyz=np.zeros((0, 3), dtype=np.float64),
            orientations_quat_wxyz=np.zeros((0, 4), dtype=np.float64),
            timestamps=np.asarray(trajectory.timestamps, dtype=np.float64),
        )
    transformed: list[NDArray[np.float64]] = []
    for pose in poses:
        matrix = np.eye(4, dtype=np.float64)
        matrix[:3, :3] = rotation @ pose[:3, :3]
        matrix[:3, 3] = scale * (rotation @ pose[:3, 3]) + translation
        transformed.append(matrix)
    positions_xyz = np.asarray([matrix[:3, 3] for matrix in transformed], dtype=np.float64)
    orientations_quat_wxyz = np.asarray(
        [FrameTransform.from_matrix(matrix).quaternion_xyzw()[[3, 0, 1, 2]] for matrix in transformed],
        dtype=np.float64,
    )
    return PoseTrajectory3D(
        positions_xyz=positions_xyz,
        orientations_quat_wxyz=orientations_quat_wxyz,
        timestamps=np.asarray(trajectory.timestamps, dtype=np.float64),
    )


def _sample_rgb_colors(
    rgb: np.ndarray | None,
    *,
    valid_mask: np.ndarray,
    depth_stride_px: int,
) -> np.ndarray | None:
    if rgb is None:
        return None
    colors = np.asarray(rgb, dtype=np.uint8)
    if colors.ndim != 3 or colors.shape[2] != 3:
        raise ValueError(f"Expected RGB image shape (H, W, 3), got {colors.shape}.")
    sampled_colors = colors[::depth_stride_px, ::depth_stride_px]
    if sampled_colors.shape[:2] != valid_mask.shape:
        raise ValueError(f"RGB shape {colors.shape[:2]} does not match sampled depth shape {valid_mask.shape}.")
    return sampled_colors.reshape(-1, 3)[valid_mask.reshape(-1)]


def _empty_colors(rgb: np.ndarray | None) -> np.ndarray | None:
    return None if rgb is None else np.empty((0, 3), dtype=np.uint8)


__all__ = [
    "DEFAULT_REFERENCE_CLOUD_DEPTH_STRIDE_PX",
    "DEFAULT_REFERENCE_CLOUD_MAX_POINTS",
    "DEFAULT_REFERENCE_CLOUD_RANDOM_SEED",
    "depth_map_to_world_points",
    "load_point_cloud_ply",
    "load_point_cloud_ply_with_colors",
    "load_tum_trajectory",
    "pointmap_from_depth",
    "sample_point_cloud_random",
    "transform_points_world_camera",
    "write_point_cloud_ply",
    "write_tum_trajectory",
    "apply_similarity_to_trajectory",
    "yaw_similarity_align",
]
