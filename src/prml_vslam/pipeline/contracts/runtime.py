"""Projected runtime snapshot contracts.

This module owns the live metadata view derived from the append-only event
stream in :mod:`prml_vslam.pipeline.contracts.events`. Snapshots are for
inspection and UI convenience; they are not the source of truth.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import ArtifactRef
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


__all__ = ["RunSnapshot", "RunState"]
