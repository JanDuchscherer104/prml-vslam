from __future__ import annotations

import numpy as np

from prml_vslam.datasets.advio_replay_adapter import _poses_for_frame_timestamps
from prml_vslam.interfaces import SE3Pose, TimedPoseTrajectory


def test_se3_pose_from_quaternion_translation_builds_pose() -> None:
    pose = SE3Pose.from_quaternion_translation(
        np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64),
        np.array([1.0, 2.0, 3.0], dtype=np.float64),
    )

    assert pose.qw == 1.0
    assert pose.tx == 1.0
    assert pose.ty == 2.0
    assert pose.tz == 3.0


def test_poses_for_frame_timestamps_interpolates_translation_and_uses_nearest_quaternion() -> None:
    trajectory = TimedPoseTrajectory(
        timestamps_s=np.array([0.0, 1.0], dtype=np.float64),
        positions_xyz=np.array([[0.0, 0.0, 0.0], [10.0, 0.0, 0.0]], dtype=np.float64),
        quaternions_xyzw=np.array([[0.0, 0.0, 0.0, 1.0], [0.5, 0.5, 0.5, 0.5]], dtype=np.float64),
    )

    poses = _poses_for_frame_timestamps(np.array([0, 500_000_000, 1_000_000_000], dtype=np.int64), trajectory)

    assert [pose.tx if pose is not None else None for pose in poses] == [0.0, 5.0, 10.0]
    assert poses[0] == SE3Pose.from_quaternion_translation(
        np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64),
        np.array([0.0, 0.0, 0.0], dtype=np.float64),
    )
    assert poses[2] == SE3Pose.from_quaternion_translation(
        np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float64),
        np.array([10.0, 0.0, 0.0], dtype=np.float64),
    )
