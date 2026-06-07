"""ADVIO trajectory interpolation helpers."""

from __future__ import annotations

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform


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
    "interpolate_trajectory_poses",
]
