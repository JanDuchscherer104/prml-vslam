"""Pipeline execution mode contract."""

from __future__ import annotations

from enum import StrEnum


class PipelineMode(StrEnum):
    """Select whether the run is batch/offline or live/incremental."""

    OFFLINE = "offline"
    STREAMING = "streaming"


__all__ = ["PipelineMode"]
