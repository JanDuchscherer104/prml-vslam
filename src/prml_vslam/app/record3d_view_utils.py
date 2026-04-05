"""Pure view helpers for the Record3D page."""

from __future__ import annotations

from typing import Any

from prml_vslam.io.record3d import Record3DTransportId

from .models import Record3DStreamSnapshot


def build_record3d_frame_details(snapshot: Record3DStreamSnapshot, packet: Any) -> dict[str, object]:
    """Build the compact frame-details payload shown in the Record3D page."""
    details: dict[str, object] = {"arrival_timestamp_s": round(packet.arrival_timestamp_s, 3)}
    if snapshot.source_label:
        details["source"] = snapshot.source_label
    if "original_size" in packet.metadata:
        details["original_size"] = packet.metadata["original_size"]
    if packet.metadata:
        details["metadata"] = packet.metadata
    return details


def record3d_stream_hint(transport: Record3DTransportId) -> str:
    """Return the short transport-specific helper text."""
    return {
        Record3DTransportId.USB: (
            "USB capture uses the native `record3d` Python bindings and is the canonical programmatic ingress for "
            "Record3D in this repo. It can expose RGB, depth, intrinsics, pose, and confidence."
        ),
        Record3DTransportId.WIFI: (
            "Wi-Fi Preview uses a Python-side WebRTC receiver. It is an optional lower-fidelity preview path for "
            "the app, not the canonical ingestion boundary. Enter the device address shown in the iPhone app."
        ),
    }[transport]


__all__ = ["build_record3d_frame_details", "record3d_stream_hint"]
