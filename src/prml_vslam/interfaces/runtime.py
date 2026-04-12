"""Canonical shared runtime frame contracts."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils.base_data import BaseData

from .camera import CameraIntrinsics
from .transforms import FrameTransform


class FramePacket(BaseData):
    """Canonical frame payload shared by replay and live ingress."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    seq: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    arrival_timestamp_s: float | None = None
    rgb: NDArray[np.uint8] | None = None
    depth: NDArray[np.float32] | None = None
    confidence: NDArray[np.float32] | None = None
    """Optional HxW sensor-confidence raster aligned with the depth image."""
    intrinsics: CameraIntrinsics | None = None
    pose: FrameTransform | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
