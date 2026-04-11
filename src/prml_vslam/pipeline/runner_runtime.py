"""Generic threaded runtime support for pipeline runners."""

from __future__ import annotations

from collections.abc import Callable
from threading import Event, Lock, Thread
from typing import Generic, TypeVar

from prml_vslam.utils import BaseData

SnapshotT = TypeVar("SnapshotT", bound=BaseData)


class RunnerRuntime(Generic[SnapshotT]):
    """Own one threaded worker plus its typed snapshot state."""

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
        self._active_stop_event: Event | None = None
        self._worker_thread: Thread | None = None
        self._cleanup: Callable[[], None] | None = None

    def snapshot(self) -> SnapshotT:
        """Return a deep copy of the latest snapshot."""
        with self._lock:
            return self._snapshot.model_copy(deep=True)

    def launch(
        self,
        *,
        starting_snapshot: SnapshotT,
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
            self._cleanup = None
            self._snapshot = starting_snapshot
        worker.start()

    def register_cleanup(self, *, stop_event: Event, cleanup: Callable[[], None]) -> None:
        """Register a cleanup callback associated with the active worker."""
        with self._lock:
            if self._active_stop_event is stop_event:
                self._cleanup = cleanup

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
        """Stop the worker and update the terminal snapshot."""
        snapshot_update = snapshot_update or (lambda _snapshot: self._empty_snapshot())
        with self._lock:
            worker = self._worker_thread
            stop_event = self._active_stop_event
            cleanup = self._cleanup
            self._cleanup = None
        if stop_event is not None:
            stop_event.set()
        if cleanup is not None:
            cleanup()
        if worker is not None:
            worker.join(timeout=join_timeout_seconds)
            if worker.is_alive():
                raise RuntimeError(self._stop_timeout_message)
        with self._lock:
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
        cleanup: Callable[[], None] | None = None
        with self._lock:
            if self._active_stop_event is stop_event:
                cleanup = self._cleanup
                self._cleanup = None
                self._active_stop_event = None
                self._worker_thread = None
            self._snapshot = snapshot_update(self._snapshot)
        if cleanup is not None:
            cleanup()


__all__ = ["RunnerRuntime"]
