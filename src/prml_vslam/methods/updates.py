"""Method-owned runtime update contracts."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import SE3Pose
from prml_vslam.utils import BaseData


class SlamUpdate(BaseData):
    """Incremental SLAM update emitted by streaming-capable backends."""

    seq: int
    """Frame sequence number associated with the update."""

    timestamp_ns: int
    """Timestamp in nanoseconds."""

    pose: SE3Pose | None = None
    """Optional canonical pose estimate."""

    num_sparse_points: int = 0
    """Current sparse point count when the backend exposes it."""

    num_dense_points: int = 0
    """Current cumulative dense-point count when the backend exposes reconstruction output."""

    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 pointmap in camera coordinates for the current frame."""


__all__ = ["SlamUpdate"]
