"""Pure view helpers for the Record3D page."""

from __future__ import annotations

from prml_vslam.interfaces import FramePacket

from .models import Record3DStreamSnapshot


def build_record3d_frame_details(snapshot: Record3DStreamSnapshot, packet: FramePacket) -> dict[str, object]:
    """Build the compact frame-details payload shown in the Record3D page."""
    arrival_timestamp_s = packet.arrival_timestamp_s
    if arrival_timestamp_s is None:
        arrival_timestamp_s = packet.timestamp_ns / 1e9
    details: dict[str, object] = {"arrival_timestamp_s": round(arrival_timestamp_s, 3)}
    if snapshot.source_label:
        details["source"] = snapshot.source_label
    if "original_size" in packet.metadata:
        details["original_size"] = packet.metadata["original_size"]
    if packet.metadata:
        details["metadata"] = packet.metadata

    return details


__all__ = ["build_record3d_frame_details"]
