"""Dataset-owned identifiers and normalized trajectory contracts."""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from jaxtyping import Float

from prml_vslam.io.interfaces import CameraPose
from prml_vslam.utils import BaseData


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {
            DatasetId.ADVIO: "ADVIO",
        }[self]


class TimedPoseTrajectory(BaseData):
    """Timestamped trajectory represented as dense NumPy arrays."""

    timestamps_s: Float[np.ndarray, "num_points"]  # noqa: F821, UP037
    positions_xyz: Float[np.ndarray, "num_points 3"]  # noqa: F722
    quaternions_xyzw: Float[np.ndarray, "num_points 4"]  # noqa: F722

    def pose_at(self, index: int) -> CameraPose:
        """Return one pose sample as a structured pose object."""
        return CameraPose.from_quaternion_translation(self.quaternions_xyzw[index], self.positions_xyz[index])


__all__ = [
    "DatasetId",
    "TimedPoseTrajectory",
]
