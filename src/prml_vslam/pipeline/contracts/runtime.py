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
from prml_vslam.pipeline.contracts.events import FramePacketSummary, StageProgress, StageStatus
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel


# TODO: this is a dto / data model that should be defined in a shared model module! given that it contains only transport-model definitions!
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
    polling loops. Durable outcomes still live in artifacts and summaries, while
    runtime truth still lives in :class:`prml_vslam.pipeline.contracts.events.RunEvent`.
    """

    run_id: str = ""
    state: RunState = RunState.IDLE
    plan: RunPlan | None = None
    current_stage_key: StageKey | None = None
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
    latest_packet: FramePacketSummary | None = None
    latest_frame: ArrayHandle | None = None
    latest_preview: PreviewHandle | None = None


class StreamingRunSnapshot(RunSnapshot):
    """Extend :class:`RunSnapshot` with bounded streaming telemetry fields."""

    received_frames: int = 0
    measured_fps: float = 0.0
    accepted_keyframes: int = 0
    backend_fps: float = 0.0
    num_sparse_points: int = 0
    num_dense_points: int = 0
    trajectory_positions_xyz: list[tuple[float, float, float]] = Field(default_factory=list)
    trajectory_timestamps_s: list[float] = Field(default_factory=list)


__all__ = ["RunSnapshot", "RunState", "StreamingRunSnapshot"]
