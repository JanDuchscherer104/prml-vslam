"""Canonical shared trajectory model."""

from __future__ import annotations

import numpy as np
from jaxtyping import Float

from prml_vslam.utils.base_data import BaseData

from .camera import SE3Pose


class TimedPoseTrajectory(BaseData):
    """Timestamped trajectory represented as dense NumPy arrays."""

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    positions_xyz: Float[np.ndarray, "num_points 3"]  # noqa: F722
    quaternions_xyzw: Float[np.ndarray, "num_points 4"]  # noqa: F722

    def pose_at(self, index: int) -> SE3Pose:
        """Return one pose sample as a canonical SE(3) pose."""
        return SE3Pose.from_quaternion_translation(self.quaternions_xyzw[index], self.positions_xyz[index])
