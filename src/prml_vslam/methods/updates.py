"""Method-owned runtime update contracts."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils import BaseData


class SlamUpdate(BaseData):
    """Incremental SLAM update emitted by streaming-capable backends."""

    seq: int
    """Source-frame sequence number associated with the update."""

    timestamp_ns: int
    """Timestamp in nanoseconds."""

    source_seq: int | None = None
    """Source-packet sequence number that produced this update, when explicit."""

    source_timestamp_ns: int | None = None
    """Source-packet timestamp that produced this update, when explicit."""

    is_keyframe: bool = False
    """Whether the update came from an accepted keyframe."""

    keyframe_index: int | None = None
    """Accepted keyframe index in backend view order, if the frame was admitted."""

    pose: FrameTransform | None = None
    """Optional canonical pose estimate."""

    num_sparse_points: int = 0
    """Current sparse point count when the backend exposes it."""

    num_dense_points: int = 0
    """Current cumulative dense-point count when the backend exposes reconstruction output."""

    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 pointmap in camera coordinates for the current accepted keyframe."""

    preview_rgb: NDArray[np.uint8] | None = None
    """Optional HxWx3 preview visualization for the current accepted keyframe."""

    pose_updated: bool = False
    """Whether the pose in this update is a fresh result from a new backend step."""


__all__ = ["SlamUpdate"]
