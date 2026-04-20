"""Shared runtime packet-stream behavior seam.

This module defines the minimal blocking interface that replay adapters and live
transport integrations must satisfy before the rest of the package can consume
their frames. It does not define packet meaning; see
:mod:`prml_vslam.interfaces.runtime` for :class:`prml_vslam.interfaces.FramePacket`.
"""

from __future__ import annotations

from typing import Any, Protocol

from prml_vslam.interfaces.runtime import FramePacket


class FramePacketStream(Protocol):
    """Blockingly deliver :class:`prml_vslam.interfaces.FramePacket` values.

    The shared lifecycle is ``connect() -> wait_for_packet(...) ->
    disconnect()``. Streaming sources in :mod:`prml_vslam.io` and dataset replay
    adapters in :mod:`prml_vslam.datasets` both satisfy this seam so
    :mod:`prml_vslam.pipeline` and :mod:`prml_vslam.methods` can consume them
    uniformly.
    """

    def connect(self) -> Any:
        """Connect to the source and prepare subsequent blocking packet reads."""

    def disconnect(self) -> None:
        """Disconnect or release the source and any owned runtime resources."""

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Wait for and return the next normalized frame packet."""


__all__ = ["FramePacketStream"]
