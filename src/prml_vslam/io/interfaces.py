"""Generic camera and frame-stream contracts owned by the IO package."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils import BaseData


class PinholeCameraIntrinsics(BaseData):
    """Pinhole camera intrinsics and optional distortion metadata."""

    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)
    fx: float
    fy: float
    cx: float
    cy: float
    distortion_model: str | None = None
    distortion_coefficients: tuple[float, ...] = ()

    def as_matrix(self) -> NDArray[np.float64]:
        """Return the intrinsics as a 3x3 camera matrix."""
        return np.array(
            [
                [self.fx, 0.0, self.cx],
                [0.0, self.fy, self.cy],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )


class CameraPose(BaseData):
    """One camera pose in world coordinates."""

    qx: float
    qy: float
    qz: float
    qw: float
    tx: float
    ty: float
    tz: float


class VideoFramePacket(BaseData):
    """One decoded RGB frame emitted by a video-backed source."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    frame_index: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    rgb: NDArray[np.uint8]
    intrinsics: PinholeCameraIntrinsics | None = None
    camera_pose: CameraPose | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VideoPacketStream(Protocol):
    """Common blocking packet-stream interface for replay or live sources."""

    def connect(self) -> Any:
        """Connect to the source and prepare for frame delivery."""

    def disconnect(self) -> None:
        """Disconnect or release the source."""

    def wait_for_packet(self, timeout_seconds: float | None = None) -> VideoFramePacket:
        """Wait for and return the next frame packet."""


__all__ = [
    "CameraPose",
    "PinholeCameraIntrinsics",
    "VideoFramePacket",
    "VideoPacketStream",
]
