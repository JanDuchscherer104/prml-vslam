"""Projected runtime snapshot contracts.

This module owns the live metadata view derived from the append-only event
stream in :mod:`prml_vslam.pipeline.contracts.events`. Snapshots are for
inspection and UI convenience; they are not the source of truth.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.pipeline.contracts.events import StageOutcome, StageProgress, StageStatus
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.pipeline.stages.base.contracts import StageRuntimeStatus
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef


# TODO: this is a dto / data model that should be defined in a shared model module! given that it contains only transport-model definitions!
class RunState(StrEnum):
    """Name the coarse lifecycle states exposed to app and CLI consumers."""

    IDLE = "idle"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


# TODO(pipeline-refactor/WP-10): Remove compatibility projection fields such as
# stage_status, stage_progress, and stage-specific top-level payloads after
# app/CLI reads keyed outcomes, runtime status, artifact refs, and live refs.
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

    stage_status: dict[StageKey, StageStatus] = Field(default_factory=dict)
    stage_progress: dict[StageKey, StageProgress] = Field(default_factory=dict)
    artifacts: dict[str, ArtifactRef] = Field(default_factory=dict)
    last_event_id: str | None = None
    error_message: str = ""
    active_executor: str | None = None
    last_event_kind: str | None = None
    sequence_manifest: SequenceManifest | None = None
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts | None = None
    ground_alignment: GroundAlignmentMetadata | None = None
    visualization: VisualizationArtifacts | None = None
    summary: RunSummary | None = None
    stage_manifests: list[StageManifest] = Field(default_factory=list)


__all__ = ["RunSnapshot", "RunState"]
