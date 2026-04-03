"""Typed contracts for artifact-first pipeline planning and execution."""

from __future__ import annotations

from enum import Enum, StrEnum
from pathlib import Path
from typing import Literal

from pydantic import Field

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils import BaseConfig, BaseData


class PipelineMode(StrEnum):
    """Supported pipeline operating modes."""

    OFFLINE = "offline"
    STREAMING = "streaming"


class VideoSourceSpec(BaseConfig):
    """Video-backed source used for offline planning and execution."""

    kind: Literal["video"] = "video"
    """Discriminator for Pydantic source unions."""

    video_path: Path
    """Path to the input video that will be processed."""

    frame_stride: int = 1
    """Frame subsampling stride applied during ingestion."""


class DatasetSourceSpec(BaseConfig):
    """Dataset-backed source used for offline planning and execution."""

    kind: Literal["dataset"] = "dataset"
    """Discriminator for Pydantic source unions."""

    dataset_id: DatasetId
    """Dataset family that owns the sequence."""

    sequence_id: str
    """Dataset-specific sequence identifier."""


class LiveSourceSpec(BaseConfig):
    """Live source used for preview, capture, and optional persistence."""

    kind: Literal["live"] = "live"
    """Discriminator for Pydantic source unions."""

    source_id: str
    """Live source identifier such as `record3d_usb` or `record3d_wifi`."""

    persist_capture: bool = True
    """Whether to persist the captured session for downstream offline use."""


class TrackingConfig(BaseConfig):
    """Tracking-stage configuration shared by the planner and runners."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""

    config_path: Path | None = None
    """Optional explicit backend config path."""


class DenseConfig(BaseConfig):
    """Dense-mapping stage toggle."""

    enabled: bool = True
    """Whether the run should include dense map export."""


class ReferenceConfig(BaseConfig):
    """Reference-reconstruction stage toggle."""

    enabled: bool = False
    """Whether the run should include a reference reconstruction stage."""


class BenchmarkEvaluationConfig(BaseConfig):
    """Evaluation-stage toggles for the benchmark pipeline."""

    compare_to_arcore: bool = True
    """Whether the plan should reserve an ARCore comparison stage."""

    evaluate_cloud: bool = False
    """Whether the run should include dense-cloud comparison."""

    evaluate_efficiency: bool = True
    """Whether the run should include efficiency metrics."""


class RunRequest(BaseConfig):
    """Config-defined entry contract for one pipeline run."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Whether the run is offline-only or live-backed."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    source: VideoSourceSpec | DatasetSourceSpec | LiveSourceSpec = Field(discriminator="kind")
    """Source specification normalized before the main benchmark stages run."""

    tracking: TrackingConfig
    """Tracking-stage configuration."""

    dense: DenseConfig = Field(default_factory=DenseConfig)
    """Dense-mapping configuration."""

    reference: ReferenceConfig = Field(default_factory=ReferenceConfig)
    """Reference-reconstruction configuration."""

    evaluation: BenchmarkEvaluationConfig = Field(default_factory=BenchmarkEvaluationConfig)
    """Benchmark evaluation configuration."""


class RunPlanStageId(str, Enum):
    """Canonical stage identifiers in the benchmark planner."""

    INGEST = "ingest"
    SLAM = "slam"
    DENSE_MAPPING = "dense_mapping"
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

    source: VideoSourceSpec | DatasetSourceSpec | LiveSourceSpec = Field(discriminator="kind")
    """Source definition that the run plan was built from."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""


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


class TrackingArtifacts(BaseData):
    """Materialized outputs produced by the tracking stage."""

    trajectory_tum: ArtifactRef
    """Normalized TUM trajectory artifact."""

    sparse_points_ply: ArtifactRef | None = None
    """Optional sparse point cloud artifact."""

    preview_log_jsonl: ArtifactRef | None = None
    """Optional preview/event log produced during live tracking."""


class DenseArtifacts(BaseData):
    """Materialized outputs produced by the dense-mapping stage."""

    dense_points_ply: ArtifactRef
    """Normalized dense point cloud artifact."""


class ReferenceArtifacts(BaseData):
    """Materialized outputs produced by the reference-reconstruction stage."""

    reference_cloud_ply: ArtifactRef
    """Normalized reference cloud artifact."""


class TrajectoryMetrics(BaseData):
    """Persisted trajectory-metric artifact bundle."""

    metrics_json: ArtifactRef
    """Serialized trajectory metric results."""


class CloudMetrics(BaseData):
    """Persisted cloud-metric artifact bundle."""

    metrics_json: ArtifactRef
    """Serialized cloud comparison results."""


class EfficiencyMetrics(BaseData):
    """Persisted efficiency-metric artifact bundle."""

    metrics_json: ArtifactRef
    """Serialized runtime or resource-usage results."""


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


class RunSummary(BaseData):
    """Final persisted outcome for one benchmark run."""

    run_id: str
    """Stable run identifier."""

    artifact_root: Path
    """Root directory that owns all run artifacts."""

    stage_status: dict[RunPlanStageId, StageExecutionStatus] = Field(default_factory=dict)
    """Final status per stage."""


class FramePacket(BaseData):
    """Lightweight runtime frame unit shared by replay and live ingress."""

    seq: int
    """Zero-based frame sequence number."""

    ts_ns: int
    """Frame timestamp in nanoseconds."""

    image_path: Path | None = None
    """Path-backed RGB image when the frame has already been materialized."""

    jpeg_bytes: bytes | None = None
    """Encoded image bytes when the frame is in-memory only."""

    width: int = 0
    """Frame width in pixels."""

    height: int = 0
    """Frame height in pixels."""


__all__ = [
    "ArtifactRef",
    "BenchmarkEvaluationConfig",
    "CloudMetrics",
    "DatasetSourceSpec",
    "DenseArtifacts",
    "DenseConfig",
    "EfficiencyMetrics",
    "FramePacket",
    "LiveSourceSpec",
    "PipelineMode",
    "ReferenceArtifacts",
    "ReferenceConfig",
    "RunPlan",
    "RunPlanStage",
    "RunPlanStageId",
    "RunRequest",
    "RunSummary",
    "SequenceManifest",
    "StageExecutionStatus",
    "StageManifest",
    "TrackingArtifacts",
    "TrackingConfig",
    "TrajectoryMetrics",
    "VideoSourceSpec",
]
