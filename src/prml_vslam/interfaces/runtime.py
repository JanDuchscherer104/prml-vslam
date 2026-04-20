"""Canonical shared runtime frame and provenance contracts."""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils.base_data import BaseData

from .camera import CameraIntrinsics
from .transforms import FrameTransform


class Record3DTransportId(StrEnum):
    """Stable Record3D transport identifiers shared across app, CLI, and IO."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the user-facing transport label."""
        return "Wi-Fi Preview" if self is Record3DTransportId.WIFI else self.value.upper()

    def stream_hint(self) -> str:
        """Return the short transport-specific helper text."""
        match self:
            case Record3DTransportId.USB:
                return (
                    "USB capture uses the native `record3d` Python bindings. It can expose RGB, depth, intrinsics, "
                    "pose, and confidence."
                )
            case Record3DTransportId.WIFI:
                return (
                    "Wi-Fi Preview uses a Python-side WebRTC receiver. It is a supported repo transport. Enter the "
                    "device address shown in the iPhone app."
                )
            case _:
                raise ValueError(f"Unsupported Record3D transport: {self}")


class FramePacketProvenance(BaseData):
    """Typed shared provenance carried with one runtime frame packet."""

    source_id: str = ""
    dataset_id: str = ""
    sequence_id: str = ""
    sequence_name: str = ""
    pose_source: str = ""
    transport: Record3DTransportId | None = None
    device_type: str = ""
    device_address: str = ""
    source_frame_index: int | None = None
    loop_index: int = 0
    video_rotation_degrees: int = 0
    original_width: int | None = None
    original_height: int | None = None

    def compact_payload(self) -> dict[str, object]:
        """Return a JSON-ready payload without empty/default-only fields."""
        payload = self.model_dump(mode="json", exclude_none=True)
        return {key: value for key, value in payload.items() if value not in ("", [], {}, 0)}


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
    pointmap: NDArray[np.float32] | None = None
    """Optional pointmap-like XYZ payload aligned with the emitted frame when available."""
    intrinsics: CameraIntrinsics | None = None
    pose: FrameTransform | None = None
    provenance: FramePacketProvenance = Field(default_factory=FramePacketProvenance)


__all__ = ["FramePacket", "FramePacketProvenance", "Record3DTransportId"]
