"""Method-owned runtime update contracts.

This module owns the live telemetry surface emitted by streaming-capable
wrappers before the pipeline translates it into transport-safe runtime events.
It is intentionally richer and more backend-aware than the pipeline event
surface because it still lives inside the method layer.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.utils import BaseData


class SlamUpdate(BaseData):
    """Carry one incremental backend update before pipeline translation.

    Backends use this DTO to report poses, map statistics, and optional live
    visualization surfaces such as pointmaps or preview images. The pipeline
    translates it into :mod:`prml_vslam.methods.events` so the transport layer
    can stay backend-neutral.
    """

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
    """Optional HxWx3 camera-local pointmap for the current accepted keyframe.

    The current ViSTA integration forwards the upstream `get_pointmap_vis(...)`
    payload unchanged apart from dtype normalization. This means the pointmap is
    expressed in the ViSTA camera basis (`RDF`: right, down, forward), already
    scaled by the selected Sim(3) node scale, and still local to the keyed
    camera frame. It is not a world-space fused cloud and must be composed
    through the posed parent camera entity when logged to Rerun.
    """

    camera_intrinsics: CameraIntrinsics | None = None
    """Optional camera intrinsics for the current accepted keyframe raster.

    For ViSTA live updates these intrinsics describe the ViSTA-preprocessed
    model raster, not the original source-frame raster.
    """

    image_rgb: NDArray[np.uint8] | None = None
    """Optional HxWx3 RGB image for the current accepted keyframe raster.

    For ViSTA live updates this is the preprocessed model image that shares a
    raster with `camera_intrinsics`, `depth_map`, and `pointmap`.
    """

    depth_map: NDArray[np.float32] | None = None
    """Optional HxW metric depth raster for the current accepted keyframe raster.

    In the ViSTA live path this is the scaled upstream depth image returned by
    `OnlineSLAM.get_view(...)`. It lives on the model raster and should not be
    confused with the exported world-space dense cloud produced later by
    `save_data_all()`.
    """

    preview_rgb: NDArray[np.uint8] | None = None
    """Optional HxWx3 diagnostic preview visualization for the current accepted keyframe.

    ViSTA currently uses a pseudo-colored pointmap preview here. It is neither
    the source RGB image nor a metric depth visualization.
    """

    pose_updated: bool = False
    """Whether the pose in this update is a fresh result from a new backend step."""

    backend_warnings: list[str] = Field(default_factory=list)
    """Non-fatal backend warnings associated with this update."""


__all__ = ["SlamUpdate"]
