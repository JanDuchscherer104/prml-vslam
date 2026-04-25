"""Replay clock used by dataset and video source streams."""

from __future__ import annotations

import time
from enum import StrEnum


class ReplayMode(StrEnum):
    """Select whether replay follows source timing or returns observations immediately."""

    FAST_AS_POSSIBLE = "fast_as_possible"
    REALTIME = "realtime"


class ReplayClock:
    """Apply source-timestamp pacing for real-time replay."""

    def __init__(self, mode: ReplayMode) -> None:
        self.mode = mode
        self._stream_start_monotonic: float | None = None
        self._stream_start_timestamp_ns: int | None = None

    def reset(self) -> None:
        """Reset the clock baseline for a new replay loop or connection."""
        self._stream_start_monotonic = None
        self._stream_start_timestamp_ns = None

    def wait_until(self, timestamp_ns: int) -> None:
        """Sleep until the replay timestamp should be emitted."""
        if self.mode is not ReplayMode.REALTIME:
            return
        if self._stream_start_timestamp_ns is None:
            self._stream_start_timestamp_ns = timestamp_ns
            self._stream_start_monotonic = time.monotonic()
            return
        if self._stream_start_monotonic is None:
            return
        target_elapsed_s = max(timestamp_ns - self._stream_start_timestamp_ns, 0) / 1e9
        actual_elapsed_s = time.monotonic() - self._stream_start_monotonic
        sleep_seconds = target_elapsed_s - actual_elapsed_s
        if sleep_seconds > 0.0:
            time.sleep(sleep_seconds)
