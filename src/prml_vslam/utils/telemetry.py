"""Small shared telemetry math helpers."""

from __future__ import annotations

from collections import deque

FPS_WINDOW = 20


def rolling_fps(timestamps: deque[float]) -> float:
    """Compute a rolling frames-per-second estimate."""
    if len(timestamps) < 2:
        return 0.0
    elapsed = timestamps[-1] - timestamps[0]
    return 0.0 if elapsed <= 0.0 else (len(timestamps) - 1) / elapsed


__all__ = ["FPS_WINDOW", "rolling_fps"]
