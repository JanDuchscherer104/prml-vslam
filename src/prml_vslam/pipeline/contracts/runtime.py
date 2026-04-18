"""Projected runtime snapshot contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.events import FramePacketSummary, StageProgress, StageStatus
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageManifest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.visualization.contracts import VisualizationArtifacts


class RunState(StrEnum):
    """Lifecycle states exposed to the app and CLI."""

    IDLE = "idle"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class RunSnapshot(TransportModel):
    """Projected metadata-only runtime snapshot."""

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
    visualization: VisualizationArtifacts | None = None
    summary: RunSummary | None = None
    stage_manifests: list[StageManifest] = Field(default_factory=list)
    latest_packet: FramePacketSummary | None = None
    latest_frame: ArrayHandle | None = None
    latest_preview: PreviewHandle | None = None


class StreamingRunSnapshot(RunSnapshot):
    """Projected snapshot with bounded streaming telemetry."""

    received_frames: int = 0
    measured_fps: float = 0.0
    accepted_keyframes: int = 0
    backend_fps: float = 0.0
    num_sparse_points: int = 0
    num_dense_points: int = 0
    trajectory_positions_xyz: list[tuple[float, float, float]] = Field(default_factory=list)
    trajectory_timestamps_s: list[float] = Field(default_factory=list)


__all__ = ["RunSnapshot", "RunState", "StreamingRunSnapshot"]
