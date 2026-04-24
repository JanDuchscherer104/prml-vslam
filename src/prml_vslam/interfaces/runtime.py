"""Canonical runtime packet and provenance DTOs.

This module owns the normalized live or replay frame packet that flows from
:mod:`prml_vslam.io` and :mod:`prml_vslam.datasets` into streaming method
sessions and pipeline telemetry. It explains what a runtime packet means across
the whole package, while packet-stream behavior itself lives in
:mod:`prml_vslam.protocols.runtime`.
"""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from numpy.typing import NDArray
from pydantic import ConfigDict, Field

from prml_vslam.utils.base_data import BaseData

from .camera import CameraIntrinsics
from .geometry import PointCloud
from .transforms import FrameTransform


class Record3DTransportId(StrEnum):
    """Name the supported Record3D ingress transports across app, CLI, and IO."""

    USB = "usb"
    WIFI = "wifi"

    @property
    def label(self) -> str:
        """Return the transport label shown by launch surfaces and logs."""
        return "Wi-Fi Preview" if self is Record3DTransportId.WIFI else self.value.upper()

    def stream_hint(self) -> str:
        """Return a short explanation of how the selected transport behaves in this repository."""
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
    """Carry source-side provenance that survives transport normalization.

    This metadata lets downstream consumers understand where one
    :class:`FramePacket` came from without widening the core packet into a
    dataset- or transport-specific subtype. It is intentionally lightweight and
    transport-safe so it can flow through runtime events and snapshots.
    """

    source_id: str = ""
    """Stable source family such as ``advio`` or ``record3d``."""
    dataset_id: str = ""
    """Dataset family when the frame came from a repository-owned dataset adapter."""
    sequence_id: str = ""
    """Dataset- or source-specific sequence identifier."""
    sequence_name: str = ""
    """Human-readable sequence or source label."""
    pose_source: str = ""
    """Pose provider label preserved from dataset- or transport-specific serving semantics."""
    transport: Record3DTransportId | None = None
    """Record3D transport used for the frame when applicable."""
    device_type: str = ""
    """Transport-native device category, when one exists."""
    device_address: str = ""
    """Wi-Fi preview address or other source-side device locator."""
    source_frame_index: int | None = None
    """Index in the original source stream before stride or loop handling."""
    loop_index: int = 0
    """Replay loop counter for cyclic preview or dataset sessions."""
    video_rotation_degrees: int = 0
    """Original source-frame rotation metadata preserved for replay-aware consumers."""
    original_width: int | None = None
    """Original source-frame width before any repo-owned adaptation."""
    original_height: int | None = None
    """Original source-frame height before any repo-owned adaptation."""

    def compact_payload(self) -> dict[str, object]:
        """Return a compact JSON-ready subset for UI details and telemetry sinks."""
        payload = self.model_dump(mode="json", exclude_none=True)
        return {key: value for key, value in payload.items() if value not in ("", [], {}, 0)}


class FramePacket(BaseData):
    """Represent one normalized runtime frame delivered to streaming consumers.

    This is the shared packet boundary between ingress code and runtime method
    sessions. It may carry only RGB for simple video replay, or richer payloads
    such as depth, confidence, intrinsics, pose, and provenance when the source
    can provide them. Downstream code should treat it as the live counterpart
    to :class:`prml_vslam.interfaces.ingest.SequenceManifest` and should not
    rely on it as a durable artifact format.

    Coordinate and raster semantics are producer-owned and must be documented
    by the source adapter. When :attr:`pose` is present it follows the canonical
    repo convention ``world <- camera`` through
    :class:`prml_vslam.interfaces.transforms.FrameTransform`.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    seq: int = Field(ge=0)
    """Monotonic packet sequence number within the active stream."""
    timestamp_ns: int = Field(ge=0)
    """Source-aligned packet timestamp in nanoseconds."""
    arrival_timestamp_s: float | None = None
    """Wall-clock arrival timestamp used for display and diagnostics."""
    rgb: NDArray[np.uint8] | None = None
    """Optional HxWx3 RGB raster in source or model space as documented by the producer."""
    depth: NDArray[np.float32] | None = None
    """Optional HxW metric depth raster aligned with :attr:`rgb` when present."""
    confidence: NDArray[np.float32] | None = None
    """Optional HxW sensor-confidence raster aligned with the depth image."""
    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 raster-aligned camera-local XYZ pointmap for the emitted frame."""
    point_cloud: PointCloud | None = None
    """Optional unstructured XYZ point cloud sample with explicit frame semantics."""
    intrinsics: CameraIntrinsics | None = None
    """Optional intrinsics describing the raster carried by :attr:`rgb` and related payloads."""
    pose: FrameTransform | None = None
    """Optional canonical pose estimate carried through replay or live ingress."""
    provenance: FramePacketProvenance = Field(default_factory=FramePacketProvenance)
    """Typed provenance that explains where the packet originated."""


__all__ = ["FramePacket", "FramePacketProvenance", "Record3DTransportId"]
