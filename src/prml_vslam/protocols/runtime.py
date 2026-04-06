"""Canonical shared runtime protocols."""

from __future__ import annotations

from typing import Any, Protocol

from prml_vslam.interfaces.runtime import FramePacket


class FramePacketStream(Protocol):
    """Common blocking packet-stream interface for replay or live sources."""

    def connect(self) -> Any:
        """Connect to the source and prepare for frame delivery."""

    def disconnect(self) -> None:
        """Disconnect or release the source."""

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Wait for and return the next frame packet."""


__all__ = ["FramePacketStream"]
