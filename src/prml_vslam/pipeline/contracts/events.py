"""Event-first runtime contracts for the pipeline."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from prml_vslam.alignment.contracts import GroundAlignmentMetadata
from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.interfaces import FramePacketProvenance
from prml_vslam.methods.events import BackendEvent
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.handles import ArrayHandle
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest, StageStatus
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.visualization.contracts import VisualizationArtifacts


class EventTier(StrEnum):
    """Durability tier for one runtime event."""

    DURABLE = "durable"
    TELEMETRY = "telemetry"


class StageProgress(TransportModel):
    """Human-readable progress state for one stage."""

    message: str = ""
    completed_steps: int | None = None
    total_steps: int | None = None
    unit: str | None = None


class FramePacketSummary(TransportModel):
    """Transport-safe summary of one observed input packet."""

    seq: int
    timestamp_ns: int
    provenance: FramePacketProvenance = Field(default_factory=FramePacketProvenance)


class StageOutcome(TransportModel):
    """Terminal stage result used for manifests and summary projection."""

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
    kind: Literal["run.submitted"] = "run.submitted"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunStarted(_RunEventBase):
    kind: Literal["run.started"] = "run.started"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class StageQueued(_RunEventBase):
    kind: Literal["stage.queued"] = "stage.queued"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey


class StageStarted(_RunEventBase):
    kind: Literal["stage.started"] = "stage.started"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey


class StageProgressed(_RunEventBase):
    kind: Literal["stage.progressed"] = "stage.progressed"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    stage_key: StageKey
    progress: StageProgress


class ArtifactRegistered(_RunEventBase):
    kind: Literal["artifact.registered"] = "artifact.registered"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey
    artifact_key: str
    artifact: ArtifactRef


class PacketObserved(_RunEventBase):
    kind: Literal["packet.observed"] = "packet.observed"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    packet: FramePacketSummary
    frame: ArrayHandle | None = None
    received_frames: int = 0
    measured_fps: float = 0.0


class BackendNoticeReceived(_RunEventBase):
    kind: Literal["backend.notice"] = "backend.notice"
    tier: Literal[EventTier.TELEMETRY] = EventTier.TELEMETRY
    stage_key: StageKey
    notice: BackendEvent


class StageCompleted(_RunEventBase):
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
    kind: Literal["stage.failed"] = "stage.failed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE
    stage_key: StageKey
    outcome: StageOutcome


class RunStopRequested(_RunEventBase):
    kind: Literal["run.stop_requested"] = "run.stop_requested"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunStopped(_RunEventBase):
    kind: Literal["run.stopped"] = "run.stopped"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunCompleted(_RunEventBase):
    kind: Literal["run.completed"] = "run.completed"
    tier: Literal[EventTier.DURABLE] = EventTier.DURABLE


class RunFailed(_RunEventBase):
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
