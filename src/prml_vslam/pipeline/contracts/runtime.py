"""Projected runtime snapshot contracts.

This module owns the live metadata view derived from the append-only event
stream in :mod:`prml_vslam.pipeline.contracts.events`. Snapshots are for
inspection and UI convenience; they are not the source of truth.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.contracts.events import StageOutcome, StageProgress, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef


class RunState(StrEnum):
    """Name the coarse lifecycle states exposed to app and CLI consumers."""

    IDLE = "idle"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class RunSnapshot(TransportModel):
    """Project the latest run state from the append-only event stream.

    Callers should treat this DTO as a convenience view for status displays and
    polling loops. Durable state is projected from
    :class:`prml_vslam.pipeline.contracts.events.RunEvent` values, while live
    status and payload refs are projected from
    :class:`prml_vslam.pipeline.stages.base.contracts.StageRuntimeUpdate`.
    """

    run_id: str = ""
    state: RunState = RunState.IDLE
    plan: RunPlan | None = None
    current_stage_key: StageKey | None = None
    stage_outcomes: dict[StageKey, StageOutcome] = Field(default_factory=dict)
    """Target keyed terminal outcomes. Compatibility fields remain below."""

    stage_runtime_status: dict[StageKey, StageRuntimeStatus] = Field(default_factory=dict)
    """Target keyed live runtime status projected from StageRuntimeUpdate."""

    live_refs: dict[StageKey, dict[str, TransientPayloadRef]] = Field(default_factory=dict)
    """Target live-only payload refs by stage and semantic slot."""

    artifacts: dict[str, ArtifactRef] = Field(default_factory=dict)
    last_event_id: str | None = None
    error_message: str = ""
    active_executor: str | None = None
    last_event_kind: str | None = None

    @property
    def stage_status(self) -> dict[StageKey, StageStatus]:
        """Compatibility projection of per-stage lifecycle status.

        This derived map is intentionally non-canonical. App and CLI consumers
        should read ``stage_outcomes`` and ``stage_runtime_status`` directly.
        """
        status_by_stage = {stage_key: status.lifecycle_state for stage_key, status in self.stage_runtime_status.items()}
        for stage_key, outcome in self.stage_outcomes.items():
            status_by_stage[stage_key] = outcome.status
        if (
            self.current_stage_key is not None
            and self.current_stage_key not in status_by_stage
            and self.state in {RunState.PREPARING, RunState.RUNNING}
        ):
            status_by_stage[self.current_stage_key] = StageStatus.RUNNING
        return status_by_stage

    @property
    def stage_progress(self) -> dict[StageKey, StageProgress]:
        """Compatibility projection of lightweight stage progress details."""
        return {
            stage_key: StageProgress(
                message=status.progress_message,
                completed_steps=status.completed_steps,
                total_steps=status.total_steps,
                unit=status.progress_unit,
            )
            for stage_key, status in self.stage_runtime_status.items()
            if _has_progress_content(status)
        }


def _has_progress_content(status: StageRuntimeStatus) -> bool:
    return (
        bool(status.progress_message)
        or status.completed_steps is not None
        or status.total_steps is not None
        or status.progress_unit is not None
    )


__all__ = ["RunSnapshot", "RunState"]
