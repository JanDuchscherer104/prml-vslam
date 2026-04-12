"""Shared packet-session primitives for live preview and replay workers."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from threading import Event, Lock, Thread
from typing import Generic, TypeVar

import numpy as np
from pydantic import Field

from prml_vslam.interfaces import FramePacket
from prml_vslam.protocols import FramePacketStream

from .base_data import BaseData

SnapshotT = TypeVar("SnapshotT", bound=BaseData)
_EMPTY_TRAJECTORY_POSITIONS_XYZ = np.empty((0, 3), dtype=np.float64)
_EMPTY_TRAJECTORY_TIMESTAMPS_S = np.empty((0,), dtype=np.float64)


class PacketSessionSnapshot(BaseData):
    """Generic snapshot fields shared by packet-stream consumers."""

    latest_packet: FramePacket | None = None
    """Most recent frame packet, if any."""

    received_frames: int = 0
    """Number of processed packets since the current session started."""

    measured_fps: float = 0.0
    """Rolling measured packet rate."""

    accepted_keyframes: int = 0
    """Number of keyframe-like updates accepted during the current session."""

    backend_fps: float = 0.0
    """Rolling accepted-keyframe rate for the current session."""

    trajectory_positions_xyz: np.ndarray = Field(default_factory=_EMPTY_TRAJECTORY_POSITIONS_XYZ.copy)
    """Bounded keyframe trajectory history in world coordinates."""

    trajectory_timestamps_s: np.ndarray = Field(default_factory=_EMPTY_TRAJECTORY_TIMESTAMPS_S.copy)
    """Timestamps associated with `trajectory_positions_xyz`."""

    error_message: str = ""
    """Last surfaced runtime error."""


def extract_pose_position(sample: object) -> np.ndarray | None:
    """Extract one finite XYZ camera position from an object with a `pose` field."""
    pose = getattr(sample, "pose", None)
    if pose is None:
        return None
    position = np.array([pose.tx, pose.ty, pose.tz], dtype=np.float64)
    return position if np.all(np.isfinite(position)) else None


class PacketSessionMetrics:
    """Rolling packet metrics shared by preview and replay sessions."""

    def __init__(self, *, fps_window_size: int, trajectory_window_size: int) -> None:
        self._arrival_times: deque[float] = deque(maxlen=fps_window_size)
        self._keyframe_arrival_times: deque[float] = deque(maxlen=fps_window_size)
        self._trajectory_positions: deque[np.ndarray] = deque(maxlen=trajectory_window_size)
        self._trajectory_timestamps: deque[float] = deque(maxlen=trajectory_window_size)
        self._received_frames = 0
        self._accepted_keyframes = 0

    def record_packet(self, *, arrival_time_s: float) -> None:
        """Append one packet arrival to the rolling packet-rate window."""
        self._received_frames += 1
        self._arrival_times.append(arrival_time_s)

    def record_keyframe(
        self,
        *,
        arrival_time_s: float,
        position_xyz: np.ndarray | None,
        trajectory_time_s: float | None,
    ) -> None:
        """Append one accepted keyframe sample to the rolling backend window."""
        self._accepted_keyframes += 1
        self._keyframe_arrival_times.append(arrival_time_s)
        if position_xyz is not None and trajectory_time_s is not None:
            self._trajectory_positions.append(position_xyz)
            self._trajectory_timestamps.append(trajectory_time_s)

    def record(
        self,
        *,
        arrival_time_s: float,
        position_xyz: np.ndarray | None,
        trajectory_time_s: float | None,
    ) -> None:
        """Append one packet arrival and optional keyframe sample."""
        self.record_packet(arrival_time_s=arrival_time_s)
        if position_xyz is not None and trajectory_time_s is not None:
            self.record_keyframe(
                arrival_time_s=arrival_time_s,
                position_xyz=position_xyz,
                trajectory_time_s=trajectory_time_s,
            )

    def packet_snapshot_fields(self) -> dict[str, int | float]:
        """Return packet-rate snapshot fields."""
        return {
            "received_frames": self._received_frames,
            "measured_fps": self._measure_fps(self._arrival_times),
        }

    def keyframe_snapshot_fields(self) -> dict[str, int | float | np.ndarray]:
        """Return backend-keyframe snapshot fields."""
        return {
            "accepted_keyframes": self._accepted_keyframes,
            "backend_fps": self._measure_fps(self._keyframe_arrival_times),
            "trajectory_positions_xyz": self._positions_to_array(self._trajectory_positions),
            "trajectory_timestamps_s": np.asarray(tuple(self._trajectory_timestamps), dtype=np.float64),
        }

    def snapshot_fields(self) -> dict[str, int | float | np.ndarray]:
        """Return the current metrics in snapshot-ready form."""
        return self.packet_snapshot_fields() | self.keyframe_snapshot_fields()

    @staticmethod
    def _measure_fps(arrival_times: deque[float]) -> float:
        if len(arrival_times) < 2:
            return 0.0
        elapsed = arrival_times[-1] - arrival_times[0]
        return 0.0 if elapsed <= 0.0 else float((len(arrival_times) - 1) / elapsed)

    @staticmethod
    def _positions_to_array(positions: deque[np.ndarray]) -> np.ndarray:
        return (
            np.vstack(tuple(positions)).astype(np.float64, copy=False)
            if positions
            else _EMPTY_TRAJECTORY_POSITIONS_XYZ.copy()
        )


class PacketSessionRuntime(Generic[SnapshotT]):
    """Own one threaded `FramePacketStream` worker plus its snapshot state."""

    def __init__(
        self,
        *,
        empty_snapshot: Callable[[], SnapshotT],
        stop_timeout_message: str,
    ) -> None:
        self._empty_snapshot = empty_snapshot
        self._stop_timeout_message = stop_timeout_message
        self._lock = Lock()
        self._snapshot = empty_snapshot()
        self._active_stream: FramePacketStream | None = None
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None

    def snapshot(self) -> SnapshotT:
        """Return a deep copy of the latest session snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def launch(
        self,
        *,
        connecting_snapshot: SnapshotT,
        thread_name: str,
        worker_target: Callable[[Event], None],
    ) -> None:
        """Start a fresh worker after stopping any currently active one."""
        self.stop()
        stop_event = Event()
        worker = Thread(target=worker_target, args=(stop_event,), name=thread_name, daemon=True)
        with self._lock:
            self._active_stop_event = stop_event
            self._worker_thread = worker
            self._snapshot = connecting_snapshot
        worker.start()

    def register_stream(self, *, stop_event: Event, stream: FramePacketStream) -> None:
        """Register the active stream for cooperative stop/disconnect handling."""
        with self._lock:
            if self._active_stop_event is stop_event:
                self._active_stream = stream

    def update_fields(self, **fields: object) -> None:
        """Apply a partial snapshot update under the internal lock."""
        with self._lock:
            self._snapshot = self._snapshot.model_copy(update=fields)

    def replace_snapshot(self, snapshot: SnapshotT) -> None:
        """Replace the snapshot under the internal lock."""
        with self._lock:
            self._snapshot = snapshot

    def stop(
        self,
        *,
        snapshot_update: Callable[[SnapshotT], SnapshotT] | None = None,
        join_timeout_seconds: float = 2.0,
    ) -> None:
        """Stop the worker, disconnect the stream, and update the terminal snapshot."""
        snapshot_update = snapshot_update or (lambda _snapshot: self._empty_snapshot())
        with self._lock:
            worker = self._worker_thread
            stop_event = self._active_stop_event
            stream = self._active_stream
            self._active_stream = None
        if stop_event is not None:
            stop_event.set()
        if stream is not None:
            stream.disconnect()
        if worker is not None:
            worker.join(timeout=join_timeout_seconds)
            if worker.is_alive():
                raise RuntimeError(self._stop_timeout_message)
        with self._lock:
            self._active_stream = None
            self._active_stop_event = None
            self._worker_thread = None
            self._snapshot = snapshot_update(self._snapshot)

    def finalize(
        self,
        *,
        stop_event: Event,
        snapshot_update: Callable[[SnapshotT], SnapshotT],
    ) -> None:
        """Clear the active worker state and persist the final snapshot."""
        stream: FramePacketStream | None = None
        with self._lock:
            if self._active_stop_event is stop_event:
                stream = self._active_stream
                self._active_stream = None
                self._active_stop_event = None
                self._worker_thread = None
            self._snapshot = snapshot_update(self._snapshot)
        if stream is not None:
            stream.disconnect()


__all__ = [
    "PacketSessionMetrics",
    "PacketSessionRuntime",
    "PacketSessionSnapshot",
    "extract_pose_position",
]
