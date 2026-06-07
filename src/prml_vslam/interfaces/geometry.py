"""Typed geometry payload contracts shared across source and viewer boundaries.

This module keeps the three geometry representations distinct:

- :class:`PointCloud` is an unstructured set of XYZ samples in one explicit
  coordinate frame.
- :class:`PointMap` is a raster-aligned camera-local XYZ image.
- :class:`DepthMap` is a metric depth raster with intrinsics and optional pose.

Callers should use :class:`FrameTransform` fields with ``T_world_camera`` or
``T_world_frame`` semantics when a payload is world-placeable. Inverse
transforms remain local implementation details for APIs that require them.
"""

from __future__ import annotations

import math
from typing import Self

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray
from pydantic import Field, model_validator

from prml_vslam.utils import BaseData, JsonScalar

from .camera import CameraIntrinsics
from .transforms import FrameTransform

# TODO: Do we really need these geometry DTOs?


class PointCloud(BaseData):
    """Represent unstructured XYZ samples in one named coordinate frame.

    ``points_xyz`` is not raster-aligned and must not be treated as a depth map
    or pointmap without an explicit projection step. When ``T_world_frame`` is
    present, it maps this cloud's :attr:`frame` into the named world frame.
    """

    points_xyz: NDArray[np.float32]
    """Nx3 metric XYZ samples in :attr:`frame` coordinates."""

    frame: str
    """Coordinate frame of :attr:`points_xyz`, for example ``tum_rgbd_camera``."""

    colors_rgb: NDArray[np.uint8] | None = None
    """Optional Nx3 uint8 RGB colors aligned with :attr:`points_xyz`."""

    T_world_frame: FrameTransform | None = None
    """Optional world <- frame transform for world-placeable clouds."""

    timestamp_ns: int | None = Field(default=None, ge=0)
    """Source timestamp for this sample, when the cloud is time-varying."""

    provenance: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small scalar provenance that does not deserve dedicated typed fields."""

    @model_validator(mode="after")
    def validate_point_cloud(self) -> Self:
        """Normalize arrays and validate frame/shape invariants."""
        if not self.frame:
            raise ValueError("PointCloud.frame must be non-empty.")
        points = np.asarray(self.points_xyz, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"Expected point cloud shape (N, 3), got {points.shape}.")
        if not np.all(np.isfinite(points)):
            raise ValueError("Point cloud samples must contain only finite values.")
        object.__setattr__(self, "points_xyz", points)

        if self.colors_rgb is not None:
            colors = np.asarray(self.colors_rgb, dtype=np.uint8)
            if colors.shape != points.shape:
                raise ValueError(f"Expected point colors shape {points.shape}, got {colors.shape}.")
            object.__setattr__(self, "colors_rgb", colors)

        if self.T_world_frame is not None and self.T_world_frame.source_frame != self.frame:
            raise ValueError(
                "PointCloud.T_world_frame.source_frame must match PointCloud.frame "
                f"({self.T_world_frame.source_frame!r} != {self.frame!r})."
            )
        return self


class PointMap(BaseData):
    """Represent a raster-aligned camera-local XYZ pointmap.

    ``points_xyz_camera`` must have shape ``H x W x 3`` and shares the raster
    geometry of the associated intrinsics/image/depth payload. Sparse
    unstructured point clouds are not pointmaps.
    """

    points_xyz_camera: NDArray[np.float32]
    """HxWx3 metric XYZ samples in :attr:`camera_frame` coordinates."""

    camera_frame: str = "camera"
    """Camera frame used by :attr:`points_xyz_camera`."""

    T_world_camera: FrameTransform | None = None
    """Optional world <- camera pose for world-placeable pointmaps."""

    intrinsics: CameraIntrinsics | None = None
    """Optional intrinsics for the raster represented by this pointmap."""

    provenance: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small scalar provenance that does not deserve dedicated typed fields."""

    @model_validator(mode="after")
    def validate_pointmap(self) -> Self:
        """Normalize arrays and validate pointmap shape/frame invariants."""
        if not self.camera_frame:
            raise ValueError("PointMap.camera_frame must be non-empty.")
        points = np.asarray(self.points_xyz_camera, dtype=np.float32)
        if points.ndim != 3 or points.shape[2] != 3:
            raise ValueError(f"Expected pointmap shape (H, W, 3), got {points.shape}.")
        if not np.all(np.isfinite(points)):
            raise ValueError("Pointmap samples must contain only finite values.")
        object.__setattr__(self, "points_xyz_camera", points)

        if self.intrinsics is not None:
            height_px, width_px = points.shape[:2]
            if self.intrinsics.width_px is not None and self.intrinsics.width_px != width_px:
                raise ValueError(
                    f"Intrinsics width_px={self.intrinsics.width_px} does not match pointmap width {width_px}."
                )
            if self.intrinsics.height_px is not None and self.intrinsics.height_px != height_px:
                raise ValueError(
                    f"Intrinsics height_px={self.intrinsics.height_px} does not match pointmap height {height_px}."
                )

        if self.T_world_camera is not None and self.T_world_camera.source_frame != self.camera_frame:
            raise ValueError(
                "PointMap.T_world_camera.source_frame must match PointMap.camera_frame "
                f"({self.T_world_camera.source_frame!r} != {self.camera_frame!r})."
            )
        return self


class DepthMap(BaseData):
    """Represent a metric depth raster with explicit camera semantics."""

    depth_m: NDArray[np.float32]
    """HxW depth values in meters."""

    camera_frame: str = "camera"
    """Camera frame for the depth raster."""

    T_world_camera: FrameTransform | None = None
    """Optional world <- camera pose for world-placeable depth payloads."""

    intrinsics: CameraIntrinsics | None = None
    """Optional intrinsics for the depth raster."""

    provenance: dict[str, JsonScalar] = Field(default_factory=dict)
    """Small scalar provenance that does not deserve dedicated typed fields."""

    @model_validator(mode="after")
    def validate_depth_map(self) -> Self:
        """Normalize arrays and validate depth shape/frame invariants."""
        if not self.camera_frame:
            raise ValueError("DepthMap.camera_frame must be non-empty.")
        depth = np.asarray(self.depth_m, dtype=np.float32)
        if depth.ndim != 2:
            raise ValueError(f"Expected depth map shape (H, W), got {depth.shape}.")
        if not np.all(np.isfinite(depth)):
            raise ValueError("Depth maps must contain only finite values.")
        if np.any(depth < 0.0):
            raise ValueError("Depth maps must not contain negative values.")
        object.__setattr__(self, "depth_m", depth)

        if self.intrinsics is not None:
            height_px, width_px = depth.shape
            if self.intrinsics.width_px is not None and self.intrinsics.width_px != width_px:
                raise ValueError(
                    f"Intrinsics width_px={self.intrinsics.width_px} does not match depth width {width_px}."
                )
            if self.intrinsics.height_px is not None and self.intrinsics.height_px != height_px:
                raise ValueError(
                    f"Intrinsics height_px={self.intrinsics.height_px} does not match depth height {height_px}."
                )

        if self.T_world_camera is not None and self.T_world_camera.source_frame != self.camera_frame:
            raise ValueError(
                "DepthMap.T_world_camera.source_frame must match DepthMap.camera_frame "
                f"({self.T_world_camera.source_frame!r} != {self.camera_frame!r})."
            )
        return self


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


__all__ = [
    "DepthMap",
    "PointCloud",
    "PointMap",
    "apply_similarity_to_trajectory",
    "yaw_similarity_align",
]
