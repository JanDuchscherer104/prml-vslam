"""Pipeline execution contracts for local and process-backed stages."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.eval.contracts import EvaluationArtifact
from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.utils import BaseData
from prml_vslam.visualization.contracts import VisualizationArtifacts

from .artifacts import SlamArtifacts
from .plan import RunPlanStageId
from .provenance import RunSummary, StageExecutionStatus, StageManifest
from .request import StageExecutionMode
from .sequence import SequenceManifest


class StageExecutionKey(StrEnum):
    """Config keys for streaming execution components."""

    INGEST = "ingest"
    PACKET_SOURCE = "packet_source"
    SLAM = "slam"
    TRAJECTORY_EVALUATION = "trajectory_evaluation"
    SUMMARY = "summary"


class StageResult(BaseData):
    """Result record emitted by one pipeline execution component."""

    stage_id: RunPlanStageId
    """Pipeline stage represented by this result."""

    execution_key: StageExecutionKey
    """Execution component that produced this result."""

    status: StageExecutionStatus
    """Terminal status for this execution component."""

    config_hash: str
    """Fingerprint of the relevant stage configuration."""

    input_fingerprint: str
    """Fingerprint of the stage inputs."""

    output_paths: dict[str, Path] = Field(default_factory=dict)
    """Named materialized outputs produced by the stage."""

    error_message: str = ""
    """Error message for failed results."""

    sequence_manifest: SequenceManifest | None = None
    """Prepared sequence manifest produced by ingest."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark inputs produced by ingest."""

    slam: SlamArtifacts | None = None
    """Normalized SLAM artifacts produced by the SLAM stage."""

    visualization: VisualizationArtifacts | None = None
    """Visualization artifacts collected for the run."""

    trajectory_evaluation: EvaluationArtifact | None = None
    """Trajectory evaluation artifact produced by the evaluation stage."""

    summary: RunSummary | None = None
    """Final run summary produced by the summary stage."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Stage manifests produced by the summary stage."""


class StreamingStageEventKind(StrEnum):
    """Event kinds emitted by streaming worker components."""

    PACKET = "packet"
    SLAM_UPDATE = "slam_update"
    STAGE_RESULT = "stage_result"
    EOF = "eof"
    STOPPED = "stopped"
    ERROR = "error"


class StreamingStageEvent(BaseData):
    """One event emitted by a streaming worker component."""

    kind: StreamingStageEventKind
    """Event kind."""

    execution_key: StageExecutionKey
    """Execution component that emitted the event."""

    packet: FramePacket | None = None
    """Frame packet emitted by the packet-source worker."""

    slam_update: SlamUpdate | None = None
    """Incremental SLAM update emitted by the SLAM worker."""

    stage_result: StageResult | None = None
    """Terminal stage result emitted by a worker."""

    error_message: str = ""
    """Error message for error events."""


__all__ = [
    "StageExecutionKey",
    "StageExecutionMode",
    "StageResult",
    "StreamingStageEvent",
    "StreamingStageEventKind",
]
