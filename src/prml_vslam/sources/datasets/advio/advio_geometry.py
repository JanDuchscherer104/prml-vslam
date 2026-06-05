"""ADVIO trajectory geometry helpers.

This module intentionally does not prepare ADVIO Tango point-cloud payloads.
ADVIO benchmark prep now owns reference trajectories only; dense reference
cloud artifacts are produced by datasets with RGB-D observations such as
TUM RGB-D.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils import BaseData

_ALIGNMENT_MAX_DIFF_S = 0.02
_MIN_ALIGNMENT_PAIRS = 3
_RDF_HORIZONTAL_AXES = (0, 2)


class Sim3Alignment(BaseData):
    """Stored alignment mapping source-frame trajectory positions into target-frame positions."""

    source_frame: str
    target_frame: str
    alignment_type: Literal["sim3", "planar_rigid"] = "sim3"
    scale: float
    rotation: list[list[float]]
    translation: list[float]
    matched_pairs: int
    rms_error_m: float


def fit_sim3_alignment(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    source_frame: str,
    target_frame: str,
    max_diff_s: float = _ALIGNMENT_MAX_DIFF_S,
) -> Sim3Alignment:
    """Fit a Sim(3) transform from source trajectory positions to target positions."""
    source_xyz, target_xyz = _associate_trajectory_positions(
        source_trajectory=source_trajectory,
        target_trajectory=target_trajectory,
        max_diff_s=max_diff_s,
    )
    if len(source_xyz) < _MIN_ALIGNMENT_PAIRS:
        raise ValueError(f"Expected at least {_MIN_ALIGNMENT_PAIRS} matched pairs for Sim(3), got {len(source_xyz)}.")

    source_mean = source_xyz.mean(axis=0)
    target_mean = target_xyz.mean(axis=0)
    source_centered = source_xyz - source_mean
    target_centered = target_xyz - target_mean
    covariance = (target_centered.T @ source_centered) / len(source_xyz)
    u, singular_values, vh = np.linalg.svd(covariance)
    correction = np.eye(3, dtype=np.float64)
    if np.linalg.det(u @ vh) < 0.0:
        correction[-1, -1] = -1.0
    rotation = u @ correction @ vh
    variance = float(np.mean(np.sum(source_centered**2, axis=1)))
    if variance == 0.0:
        raise ValueError("Cannot fit Sim(3) alignment from a degenerate source trajectory.")
    scale = float(np.sum(singular_values * np.diag(correction)) / variance)
    translation = target_mean - scale * (rotation @ source_mean)
    residual = target_xyz - (scale * (source_xyz @ rotation.T) + translation)
    return _alignment_result(
        source_frame=source_frame,
        target_frame=target_frame,
        alignment_type="sim3",
        scale=scale,
        rotation=rotation,
        translation=translation,
        residual=residual,
        matched_pairs=len(source_xyz),
    )


def fit_planar_rigid_alignment(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    source_frame: str,
    target_frame: str,
    max_diff_s: float = _ALIGNMENT_MAX_DIFF_S,
) -> Sim3Alignment:
    """Fit ADVIO-style metric planar rigid alignment from source to target.

    ADVIO provider trajectories are already metric and gravity-aligned. The
    repository RDF convention uses the X/Z plane as horizontal, so this helper
    estimates yaw and translation only, preserving scale and vertical axis.
    """
    source_xyz, target_xyz = _associate_trajectory_positions(
        source_trajectory=source_trajectory,
        target_trajectory=target_trajectory,
        max_diff_s=max_diff_s,
    )
    if len(source_xyz) < _MIN_ALIGNMENT_PAIRS:
        raise ValueError(
            f"Expected at least {_MIN_ALIGNMENT_PAIRS} matched pairs for planar rigid alignment, got {len(source_xyz)}."
        )

    source_mean = source_xyz.mean(axis=0)
    target_mean = target_xyz.mean(axis=0)
    horizontal_axes = np.asarray(_RDF_HORIZONTAL_AXES, dtype=np.int64)
    source_horizontal_centered = source_xyz[:, horizontal_axes] - source_mean[horizontal_axes]
    target_horizontal_centered = target_xyz[:, horizontal_axes] - target_mean[horizontal_axes]
    covariance = (source_horizontal_centered.T @ target_horizontal_centered) / len(source_xyz)
    u, _singular_values, vh = np.linalg.svd(covariance)
    correction = np.eye(2, dtype=np.float64)
    if np.linalg.det(vh.T @ u.T) < 0.0:
        correction[-1, -1] = -1.0
    rotation_horizontal = vh.T @ correction @ u.T
    rotation = np.eye(3, dtype=np.float64)
    rotation[np.ix_(horizontal_axes, horizontal_axes)] = rotation_horizontal
    translation = target_mean - rotation @ source_mean
    residual = target_xyz - (source_xyz @ rotation.T + translation)
    return _alignment_result(
        source_frame=source_frame,
        target_frame=target_frame,
        alignment_type="planar_rigid",
        scale=1.0,
        rotation=rotation,
        translation=translation,
        residual=residual,
        matched_pairs=len(source_xyz),
    )


def apply_sim3(points_xyz_source: NDArray[np.float64], alignment: Sim3Alignment) -> NDArray[np.float64]:
    """Apply one stored similarity or rigid alignment to XYZ rows."""
    points = np.asarray(points_xyz_source, dtype=np.float64)
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    return alignment.scale * (points @ rotation.T) + translation


def interpolate_trajectory_poses(
    trajectory: PoseTrajectory3D,
    timestamps_s: NDArray[np.float64],
    *,
    target_frame: str = "world",
    source_frame: str = "camera",
) -> list[FrameTransform]:
    """Interpolate positions and nearest-neighbor rotations at requested timestamps."""
    source_timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    target_timestamps_s = np.asarray(timestamps_s, dtype=np.float64)
    if source_timestamps_s.size == 0:
        return []
    interpolated_positions = np.column_stack(
        [np.interp(target_timestamps_s, source_timestamps_s, trajectory.positions_xyz[:, axis]) for axis in range(3)]
    )
    nearest_indices = _nearest_timestamp_indices(source_timestamps_s, target_timestamps_s)
    poses: list[FrameTransform] = []
    for position, nearest_index in zip(interpolated_positions, nearest_indices, strict=True):
        nearest_pose = FrameTransform.from_matrix(
            np.asarray(trajectory.poses_se3[int(nearest_index)], dtype=np.float64),
            target_frame=target_frame,
            source_frame=source_frame,
        )
        poses.append(
            FrameTransform(
                target_frame=target_frame,
                source_frame=source_frame,
                qx=nearest_pose.qx,
                qy=nearest_pose.qy,
                qz=nearest_pose.qz,
                qw=nearest_pose.qw,
                tx=float(position[0]),
                ty=float(position[1]),
                tz=float(position[2]),
            )
        )
    return poses


def _alignment_result(
    *,
    source_frame: str,
    target_frame: str,
    alignment_type: Literal["sim3", "planar_rigid"],
    scale: float,
    rotation: NDArray[np.float64],
    translation: NDArray[np.float64],
    residual: NDArray[np.float64],
    matched_pairs: int,
) -> Sim3Alignment:
    return Sim3Alignment(
        source_frame=source_frame,
        target_frame=target_frame,
        alignment_type=alignment_type,
        scale=scale,
        rotation=rotation.tolist(),
        translation=translation.tolist(),
        matched_pairs=int(matched_pairs),
        rms_error_m=float(np.sqrt(np.mean(np.sum(residual**2, axis=1)))),
    )


def _associate_trajectory_positions(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    max_diff_s: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    source_timestamps = np.asarray(source_trajectory.timestamps, dtype=np.float64)
    target_timestamps = np.asarray(target_trajectory.timestamps, dtype=np.float64)
    if source_timestamps.size == 0 or target_timestamps.size == 0:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.float64)
    nearest_indices = _nearest_timestamp_indices(target_timestamps, source_timestamps)
    keep = np.abs(target_timestamps[nearest_indices] - source_timestamps) <= max_diff_s
    return (
        np.asarray(source_trajectory.positions_xyz[keep], dtype=np.float64),
        np.asarray(target_trajectory.positions_xyz[nearest_indices[keep]], dtype=np.float64),
    )


def _nearest_timestamp_indices(
    source_timestamps_s: NDArray[np.float64],
    target_timestamps_s: NDArray[np.float64],
) -> NDArray[np.int64]:
    nearest_indices = np.searchsorted(source_timestamps_s, target_timestamps_s, side="left")
    nearest_indices = np.clip(nearest_indices, 0, max(len(source_timestamps_s) - 1, 0))
    previous_indices = np.clip(nearest_indices - 1, 0, max(len(source_timestamps_s) - 1, 0))
    pick_previous = np.abs(target_timestamps_s - source_timestamps_s[previous_indices]) <= np.abs(
        source_timestamps_s[nearest_indices] - target_timestamps_s
    )
    return np.where(pick_previous, previous_indices, nearest_indices)


__all__ = [
    "Sim3Alignment",
    "apply_sim3",
    "fit_planar_rigid_alignment",
    "fit_sim3_alignment",
    "interpolate_trajectory_poses",
]
