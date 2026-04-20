"""Event-first runtime contracts for the pipeline.

This module owns the append-only event stream that represents runtime truth for
one run. Projected snapshots, summaries, and UI views are all derived from
these events rather than treated as independent state stores.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from prml_vslam.interfaces import FramePacketProvenance
from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.slam import ArtifactRef, BackendEvent, SlamArtifacts
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel


class EventTier(StrEnum):
    """Classify whether an event is durable provenance or live telemetry."""

    DURABLE = "durable"
    TELEMETRY = "telemetry"


class StageProgress(TransportModel):
    """Carry lightweight human-readable progress details for one running stage."""

    message: str = ""
    completed_steps: int | None = None
    total_steps: int | None = None
    unit: str | None = None


class FramePacketSummary(TransportModel):
    """Summarize one observed :class:`prml_vslam.interfaces.FramePacket` for telemetry."""

    seq: int
    timestamp_ns: int
    provenance: FramePacketProvenance = Field(default_factory=FramePacketProvenance)


class StageOutcome(TransportModel):
    """Capture the terminal result of one stage execution.

    This object is the key bridge from live execution into durable provenance:
    stage-completion events carry it, summary projection consumes it, and
    manifest writing turns it into persisted stage records.
    """

    stage_key: StageKey
    status: StageStatus
    config_hash: str
    input_fingerprint: str
    artifacts: dict[str, ArtifactRef] = Field(default_factory=dict)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    error_message: str = ""


class _RunEventBase(TransportModel):
    event_id: str
    run_id: str
    ts_ns: int
    tier: EventTier


class RunSubmitted(_RunEventBase):
    """Record that a run has been accepted by the backend layer."""

    kind: Literal["run.submitted"] = "run.submitted"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunStarted(_RunEventBase):
    """Record that backend execution has actually started."""

    kind: Literal["run.started"] = "run.started"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class StageQueued(_RunEventBase):
    """Record that one stage has become eligible to run."""

    kind: Literal["stage.queued"] = "stage.queued"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey


class StageStarted(_RunEventBase):
    """Record that one stage has begun executing."""

    kind: Literal["stage.started"] = "stage.started"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey


class StageProgressed(_RunEventBase):
    """Emit telemetry progress for one running stage."""

    kind: Literal["stage.progressed"] = "stage.progressed"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    stage_key: StageKey
    progress: StageProgress


class ArtifactRegistered(_RunEventBase):
    """Record that one durable artifact path has been materialized."""

    kind: Literal["artifact.registered"] = "artifact.registered"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey
    artifact_key: str
    artifact: ArtifactRef


class PacketObserved(_RunEventBase):
    """Emit telemetry about one observed streaming packet and related handles."""

    kind: Literal["packet.observed"] = "packet.observed"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    packet: FramePacketSummary
    frame: ArrayHandle | None = None
    received_frames: int = 0
    measured_fps: float = 0.0


class BackendNoticeReceived(_RunEventBase):
    """Emit translated method-layer telemetry from one streaming backend."""

    kind: Literal["backend.notice"] = "backend.notice"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    stage_key: StageKey
    notice: BackendEvent


class StageCompleted(_RunEventBase):
    """Record durable completion for one stage plus any normalized outputs."""

    kind: Literal["stage.completed"] = "stage.completed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey
    outcome: StageOutcome
    sequence_manifest: SequenceManifest | None = None
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    slam: SlamArtifacts | None = None
    ground_alignment: GroundAlignmentMetadata | None = None
    visualization: VisualizationArtifacts | None = None
    summary: RunSummary | None = None
    stage_manifests: list[StageManifest] = Field(default_factory=list)


class StageFailed(_RunEventBase):
    """Record durable failure for one stage together with its terminal outcome."""

    kind: Literal["stage.failed"] = "stage.failed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey
    outcome: StageOutcome


class RunStopRequested(_RunEventBase):
    """Record that a graceful stop has been requested for the run."""

    kind: Literal["run.stop_requested"] = "run.stop_requested"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunStopped(_RunEventBase):
    """Record that the run has stopped before normal completion."""

    kind: Literal["run.stopped"] = "run.stopped"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunCompleted(_RunEventBase):
    """Record that the full run finished successfully."""

    kind: Literal["run.completed"] = "run.completed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunFailed(_RunEventBase):
    """Record that the run terminated with an unrecoverable error."""

    kind: Literal["run.failed"] = "run.failed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    error_message: str


RunEvent = Annotated[
    RunSubmitted
    | RunStarted
    | StageQueued
    | StageStarted
    | StageProgressed
    | ArtifactRegistered
    | PacketObserved
    | BackendNoticeReceived
    | StageCompleted
    | StageFailed
    | RunStopRequested
    | RunStopped
    | RunCompleted
    | RunFailed,
    Field(discriminator="kind"),
]


__all__ = [
    "ArtifactRegistered",
    "BackendNoticeReceived",
    "EventTier",
    "FramePacketSummary",
    "PacketObserved",
    "RunCompleted",
    "RunEvent",
    "RunFailed",
    "RunStarted",
    "RunStopRequested",
    "RunStopped",
    "RunSubmitted",
    "StageCompleted",
    "StageFailed",
    "StageProgress",
    "StageProgressed",
    "StageQueued",
    "StageStarted",
    "StageStatus",
    "StageOutcome",
]
