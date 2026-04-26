"""Durable runtime event contracts for the pipeline."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel


class StageOutcome(TransportModel):
    """Capture the terminal result of one stage execution."""

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


class RunSubmitted(_RunEventBase):
    """Record that a run has been accepted by the backend layer."""

    kind: Literal["run.submitted"] = "run.submitted"


class RunStarted(_RunEventBase):
    """Record that backend execution has actually started."""

    kind: Literal["run.started"] = "run.started"


class StageQueued(_RunEventBase):
    """Record that one stage has become eligible to run."""

    kind: Literal["stage.queued"] = "stage.queued"
    stage_key: StageKey


class StageStarted(_RunEventBase):
    """Record that one stage has begun executing."""

    kind: Literal["stage.started"] = "stage.started"
    stage_key: StageKey


class ArtifactRegistered(_RunEventBase):
    """Record that one durable artifact path has been materialized."""

    kind: Literal["artifact.registered"] = "artifact.registered"
    stage_key: StageKey
    artifact_key: str
    artifact: ArtifactRef


class StageCompleted(_RunEventBase):
    """Record durable completion for one stage."""

    kind: Literal["stage.completed"] = "stage.completed"
    stage_key: StageKey
    outcome: StageOutcome


class StageFailed(_RunEventBase):
    """Record durable failure for one stage together with its terminal outcome."""

    kind: Literal["stage.failed"] = "stage.failed"
    stage_key: StageKey
    outcome: StageOutcome


class RunStopRequested(_RunEventBase):
    """Record that a graceful stop has been requested for the run."""

    kind: Literal["run.stop_requested"] = "run.stop_requested"


class RunStopped(_RunEventBase):
    """Record that the run has stopped before normal completion."""

    kind: Literal["run.stopped"] = "run.stopped"


class RunCompleted(_RunEventBase):
    """Record that the full run finished successfully."""

    kind: Literal["run.completed"] = "run.completed"


class RunFailed(_RunEventBase):
    """Record that the run terminated with an unrecoverable error."""

    kind: Literal["run.failed"] = "run.failed"
    error_message: str


RunEvent = Annotated[
    RunSubmitted
    | RunStarted
    | StageQueued
    | StageStarted
    | ArtifactRegistered
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
    "RunCompleted",
    "RunEvent",
    "RunFailed",
    "RunStarted",
    "RunStopRequested",
    "RunStopped",
    "RunSubmitted",
    "StageCompleted",
    "StageFailed",
    "StageOutcome",
    "StageQueued",
    "StageStarted",
    "StageStatus",
]
