"""Typed contracts for the current pipeline planner and streaming session."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import SE3Pose
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods.contracts import MethodId
from prml_vslam.utils import BaseConfig, BaseData, PathConfig


class PipelineMode(StrEnum):
    """Supported pipeline operating modes."""

    OFFLINE = "offline"
    STREAMING = "streaming"

    @property
    def label(self) -> str:
        return {
            self.OFFLINE: "Offline (single pass)",
            self.STREAMING: "Streaming (looped replay)",
        }[self]


class VideoSourceSpec(BaseConfig):
    """Video-backed source used for offline planning and execution."""

    video_path: Path
    """Path to the input video that will be processed."""
    frame_stride: int = 1
    """Frame subsampling stride applied during ingestion."""


class DatasetSourceSpec(BaseConfig):
    """Dataset-backed source used for offline planning and execution."""

    dataset_id: DatasetId
    """Dataset family that owns the sequence."""
    sequence_id: str
    """Dataset-specific sequence identifier."""


class LiveSourceSpec(BaseConfig):
    """Live source used for preview, capture, and optional persistence."""

    source_id: str
    """Live source identifier such as `record3d_usb`."""
    persist_capture: bool = True
    """Whether to persist the captured session for downstream offline use."""


class Record3DLiveSourceSpec(BaseConfig):
    """Typed Record3D live source used by the pipeline app and planner."""

    source_id: Literal["record3d"] = "record3d"
    """Stable live-source identifier for Record3D-backed runs."""

    transport: Record3DTransportId = Record3DTransportId.USB
    """Selected Record3D transport."""

    persist_capture: bool = True
    """Whether to persist the captured session for downstream offline use."""

    device_index: int | None = None
    """Selected USB device index when using the USB transport."""

    device_address: str = ""
    """Entered Wi-Fi preview device address when using the Wi-Fi transport."""


SourceSpec = VideoSourceSpec | DatasetSourceSpec | Record3DLiveSourceSpec | LiveSourceSpec


class SlamConfig(BaseConfig):
    """SLAM-stage configuration shared by the planner and runners."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""
    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""
    emit_dense_points: bool = True
    """Whether the SLAM stage should materialize a dense point cloud artifact."""
    emit_sparse_points: bool = True
    """Whether the SLAM stage should materialize sparse geometry artifacts."""


class ReferenceConfig(BaseConfig):
    """Boolean toggle used by the optional reference-reconstruction stage."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""


class BenchmarkEvaluationConfig(BaseConfig):
    """Evaluation-stage toggles for the benchmark pipeline."""

    evaluate_trajectory: bool = True
    """Whether the plan should reserve a trajectory-evaluation stage."""
    compare_to_arcore: bool = False
    """Whether the trajectory-evaluation stage should specifically include an ARCore comparison."""
    evaluate_cloud: bool = False
    """Whether the run should include dense-cloud comparison."""
    evaluate_efficiency: bool = True
    """Whether the run should include efficiency metrics."""


class RunRequest(BaseConfig):
    """Config-defined entry contract for one pipeline run.

    Construct the request directly from nested source, stage, and evaluation
    configs. Call :meth:`build` once the request is fully specified to
    materialize the canonical ordered :class:`RunPlan`.
    """

    experiment_name: str
    """Human-readable name for the benchmark run."""
    mode: PipelineMode = PipelineMode.OFFLINE
    """Whether the run is offline-only or live-backed."""
    output_dir: Path
    """Root directory where planned artifacts should be written."""
    source: SourceSpec
    """Source specification normalized before the main benchmark stages run."""
    slam: SlamConfig
    """SLAM-stage configuration."""
    reference: ReferenceConfig = Field(default_factory=ReferenceConfig)
    """Reference-reconstruction configuration."""
    evaluation: BenchmarkEvaluationConfig = Field(default_factory=BenchmarkEvaluationConfig)
    """Benchmark evaluation configuration."""

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        """Materialize the canonical run plan for this request.

        Args:
            path_config: Optional path helper used to derive canonical artifact
                locations for the run.

        Returns:
            Ordered pipeline plan with stable stage ids, summaries, and
            artifact paths.
        """
        from prml_vslam.pipeline.services import RunPlannerService

        return RunPlannerService().build_run_plan(request=self, path_config=path_config)


class RunPlanStageId(StrEnum):
    """Canonical stage identifiers in the benchmark planner."""

    INGEST = "ingest"
    SLAM = "slam"
    REFERENCE_RECONSTRUCTION = "reference_reconstruction"
    TRAJECTORY_EVALUATION = "trajectory_evaluation"
    CLOUD_EVALUATION = "cloud_evaluation"
    EFFICIENCY_EVALUATION = "efficiency_evaluation"
    SUMMARY = "summary"


class RunPlanStage(BaseData):
    """One typed stage in a benchmark run plan."""

    id: RunPlanStageId
    """Stable identifier for the stage."""
    title: str
    """Short human-readable stage title."""
    summary: str
    """Short description of the stage intent."""
    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""


class RunPlan(BaseData):
    """Planner output returned to the CLI or UI layer."""

    run_id: str
    """Stable filesystem-safe run identifier."""
    mode: PipelineMode
    """Selected pipeline mode."""
    method: MethodId
    """External backend chosen for the run."""
    artifact_root: Path
    """Root directory for all run artifacts."""
    source: SourceSpec
    """Source definition that the run plan was built from."""
    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""

    def stage_rows(self) -> list[dict[str, str]]:
        """Return compact tabular rows for plan summaries."""
        return [
            {
                "Stage": stage.title,
                "Id": stage.id.value,
                "Outputs": ", ".join(path.name for path in stage.outputs),
            }
            for stage in self.stages
        ]


class ArtifactRef(BaseData):
    """Reference to one materialized artifact owned by the repository."""

    path: Path
    """Filesystem path to the materialized artifact."""
    kind: str
    """Short artifact kind identifier."""
    fingerprint: str
    """Content or provenance fingerprint for cache decisions."""


class SequenceManifest(BaseData):
    """Normalized artifact boundary between input ingestion and benchmark execution."""

    sequence_id: str
    """Stable sequence identifier used across artifact stages."""
    video_path: Path | None = None
    """Video path when the sequence stays video-backed."""
    rgb_dir: Path | None = None
    """Materialized RGB frame directory when one exists."""
    timestamps_path: Path | None = None
    """Path to exact or normalized frame timestamps."""
    intrinsics_path: Path | None = None
    """Path to camera intrinsics or calibration metadata."""
    reference_tum_path: Path | None = None
    """Normalized reference trajectory in TUM format when available."""
    arcore_tum_path: Path | None = None
    """Normalized ARCore baseline trajectory in TUM format when available."""


class SlamUpdate(BaseData):
    """Incremental SLAM update emitted by streaming-capable backends."""

    seq: int
    """Frame sequence number associated with the update."""

    timestamp_ns: int
    """Timestamp in nanoseconds."""

    pose: SE3Pose | None = None
    """Optional canonical pose estimate."""

    num_sparse_points: int = 0
    """Current sparse point count when the backend exposes it."""

    num_dense_points: int = 0
    """Current cumulative dense-point count when the backend exposes reconstruction output."""

    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 pointmap in camera coordinates for the current frame."""


class SlamArtifacts(BaseData):
    """Materialized outputs produced by the SLAM stage."""

    trajectory_tum: ArtifactRef
    """Normalized TUM trajectory artifact."""
    sparse_points_ply: ArtifactRef | None = None
    """Optional sparse point cloud artifact."""
    dense_points_ply: ArtifactRef | None = None
    """Optional dense point cloud artifact."""
    preview_log_jsonl: ArtifactRef | None = None
    """Optional preview/event log produced during live SLAM."""


class StageExecutionStatus(StrEnum):
    """Execution status stored in one stage manifest."""

    HIT = "hit"
    RAN = "ran"
    FAILED = "failed"


class StageManifest(BaseData):
    """Cache and provenance record for one executed stage."""

    stage_id: RunPlanStageId
    """Stage identity."""
    config_hash: str
    """Fingerprint of the relevant stage configuration."""
    input_fingerprint: str
    """Fingerprint of the stage inputs."""
    output_paths: dict[str, Path] = Field(default_factory=dict)
    """Named materialized outputs produced or reused by the stage."""
    status: StageExecutionStatus
    """Whether the stage was reused, executed, or failed."""

    @staticmethod
    def table_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
        """Return compact tabular rows for manifest summaries."""
        return [
            {
                "Stage": manifest.stage_id.value,
                "Status": manifest.status.value,
                "Config Hash": manifest.config_hash,
                "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
            }
            for manifest in stage_manifests
        ]


class RunSummary(BaseData):
    """Final persisted outcome for one benchmark run."""

    run_id: str
    """Stable run identifier."""
    artifact_root: Path
    """Root directory that owns all run artifacts."""
    stage_status: dict[RunPlanStageId, StageExecutionStatus] = Field(default_factory=dict)
    """Final status per stage."""


__all__ = [
    "ArtifactRef",
    "BenchmarkEvaluationConfig",
    "DatasetSourceSpec",
    "LiveSourceSpec",
    "PipelineMode",
    "Record3DLiveSourceSpec",
    "ReferenceConfig",
    "RunPlan",
    "RunPlanStage",
    "RunPlanStageId",
    "RunRequest",
    "RunSummary",
    "SequenceManifest",
    "SlamArtifacts",
    "SlamConfig",
    "SlamUpdate",
    "StageExecutionStatus",
    "StageManifest",
    "VideoSourceSpec",
]
