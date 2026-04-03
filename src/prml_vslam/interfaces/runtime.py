"""Canonical shared runtime frame contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

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
    uncertainty: NDArray[np.float32] | None = None
    intrinsics: CameraIntrinsics | None = None
    pose: SE3Pose | None = None
    image_path: Path | None = None
    jpeg_bytes: bytes | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FramePacketStream(Protocol):
    """Common blocking packet-stream interface for replay or live sources."""

    def connect(self) -> Any:
        """Connect to the source and prepare for frame delivery."""

    def disconnect(self) -> None:
        """Disconnect or release the source."""

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Wait for and return the next frame packet."""
