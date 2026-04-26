"""Lifecycle-only helpers for stage runtimes."""

from __future__ import annotations

import time

from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus, StageRuntimeUpdate


class LifecycleStageRuntimeMixin:
    """Reusable lifecycle/status state for concrete stage runtimes.

    The mixin deliberately knows nothing about config, dependencies, artifacts,
    inputs, or domain outputs. Concrete stage runtimes remain responsible for
    execution and terminal :class:`StageResult` construction.
    """

    def __init__(self, *, stage_key: StageKey) -> None:
        self._runtime_status = StageRuntimeStatus(stage_key=stage_key)
        self._stop_requested = False
        self._pending_updates: list[StageRuntimeUpdate] = []

    def status(self) -> StageRuntimeStatus:
        """Return the current lifecycle status."""
        return self._runtime_status

    def stop(self) -> None:
        """Mark the runtime as stopped and remember the stop request."""
        self._stop_requested = True
        self._set_lifecycle(StageStatus.STOPPED)

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Drain queued live updates emitted by the runtime."""
        if max_items is None:
            updates = self._pending_updates
            self._pending_updates = []
            return updates
        updates = self._pending_updates[:max_items]
        self._pending_updates = self._pending_updates[max_items:]
        return updates

    def _set_lifecycle(self, lifecycle_state: StageStatus, *, progress_message: str = "") -> None:
        self._runtime_status = self._runtime_status.model_copy(
            update={
                "lifecycle_state": lifecycle_state,
                "progress_message": progress_message or self._runtime_status.progress_message,
                "updated_at_ns": time.time_ns(),
            }
        )


__all__ = ["LifecycleStageRuntimeMixin"]
