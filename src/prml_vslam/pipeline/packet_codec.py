"""Pickle-safe packet serialization shared by streaming process workers."""

from __future__ import annotations

import pickle
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prml_vslam.interfaces import FramePacket

_FramePacketPayload = dict[str, Any]


def serialize_frame_packet(frame: FramePacket) -> bytes:
    """Return a multiprocessing-safe serialized frame payload."""
    payload: _FramePacketPayload = {
        "seq": frame.seq,
        "timestamp_ns": frame.timestamp_ns,
        "arrival_timestamp_s": frame.arrival_timestamp_s,
        "rgb": frame.rgb,
        "depth": frame.depth,
        "confidence": frame.confidence,
        "intrinsics": None if frame.intrinsics is None else frame.intrinsics.model_dump(mode="python"),
        "pose": None if frame.pose is None else frame.pose.model_dump(mode="python"),
        "metadata": pickle_stable_metadata(frame.metadata),
    }
    return pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL)


def deserialize_frame_packet(serialized_frame: bytes) -> FramePacket:
    """Rebuild one frame packet in the receiving process."""
    from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FrameTransform  # noqa: PLC0415

    payload: _FramePacketPayload = pickle.loads(serialized_frame)
    intrinsics_payload = payload["intrinsics"]
    pose_payload = payload["pose"]
    return FramePacket(
        seq=payload["seq"],
        timestamp_ns=payload["timestamp_ns"],
        arrival_timestamp_s=payload["arrival_timestamp_s"],
        rgb=payload["rgb"],
        depth=payload["depth"],
        confidence=payload["confidence"],
        intrinsics=None if intrinsics_payload is None else CameraIntrinsics.model_validate(intrinsics_payload),
        pose=None if pose_payload is None else FrameTransform.model_validate(pose_payload),
        metadata=payload["metadata"],
    )


def pickle_stable_metadata(value: Any) -> Any:
    """Normalize metadata values that commonly carry module-bound classes."""
    from enum import Enum
    from pathlib import Path

    if isinstance(value, dict):
        return {str(key): pickle_stable_metadata(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [pickle_stable_metadata(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="python")
    return value


__all__ = ["deserialize_frame_packet", "pickle_stable_metadata", "serialize_frame_packet"]
