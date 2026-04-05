"""Canonical shared runtime frame contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils.base_data import BaseData

from .camera import CameraIntrinsics, SE3Pose


class FramePacket(BaseData):
    """Canonical frame payload shared by replay and live ingress."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    seq: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    arrival_timestamp_s: float | None = None
    rgb: NDArray[np.uint8] | None = None
    depth: NDArray[np.float32] | None = None
    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 dense point cloud in camera coordinates."""
    uncertainty: NDArray[np.float32] | None = None
    intrinsics: CameraIntrinsics | None = None
    pose: SE3Pose | None = None
    image_path: Path | None = None
    jpeg_bytes: bytes | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
