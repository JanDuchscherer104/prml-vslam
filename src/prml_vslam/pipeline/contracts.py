"""Typed contracts for reusable pipeline planning and materialization surfaces."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator

from prml_vslam.utils import BaseConfig


# TODO: always use StrEnum
class PipelineMode(str, Enum):
    """Execution mode for a benchmark run."""

    BATCH = "batch"
    STREAMING = "streaming"


class TimestampSource(str, Enum):
    """Source of timestamps stored in normalized artifacts."""

    CAPTURE = "capture"
    METHOD = "method"
    FRAME_INDEX = "frame_index"


class AlignmentMode(str, Enum):
    """Alignment policy attached to an artifact."""

    NONE = "none"
    SE3 = "se3"
    SIM3 = "sim3"


class InsightTone(str, Enum):
    """Visual tone used when interpreting a planned run."""

    ACCENT = "accent"
    INFO = "info"
    WARNING = "warning"


class MethodId(str, Enum):
    """Supported external monocular VSLAM backends."""

    VISTA_SLAM = "vista_slam"
    MAST3R_SLAM = "mast3r_slam"


class RunPlanStageId(str, Enum):
    """Canonical stage identifiers in the benchmark planner."""

    CAPTURE_MANIFEST = "capture_manifest"
    VIDEO_DECODE = "video_decode"
    METHOD_PREPARE = "method_prepare"
    SLAM_RUN = "slam_run"
    TRAJECTORY_NORMALIZATION = "trajectory_normalization"
    DENSE_NORMALIZATION = "dense_normalization"
    ARCORE_ALIGNMENT = "arcore_alignment"
    REFERENCE_RECONSTRUCTION = "reference_reconstruction"
    VISUALIZATION_EXPORT = "visualization_export"
    STREAM_SOURCE_OPEN = "stream_source_open"
    ONLINE_TRACKING = "online_tracking"
    CHUNK_PERSIST = "chunk_persist"
    STREAM_FINALIZE = "stream_finalize"
    INGEST = "ingest"
    SLAM = "slam"
    DENSE_MAPPING = "dense_mapping"
    ARCORE_COMPARISON = "arcore_comparison"


# TODO: All meta data or artifacts must be derived from a common meta_data or artifact baseclass and support functionality to be gathered / be represented as pandas data frame
class CaptureMetadataConfig(BaseConfig):
    """Capture-side metadata attached to a planned benchmark run."""

    device_label: str | None = None
    """Human-readable capture device label."""

    frame_rate_hz: float | None = None
    """Nominal capture frame rate."""

    timestamp_source: TimestampSource = TimestampSource.CAPTURE
    """Timestamp provenance used by normalized outputs."""

    arcore_log_path: Path | None = None
    """Optional ARCore side-channel log path."""

    calibration_hint_path: Path | None = None
    """Optional calibration hint path."""

    notes: str | None = None
    """Short operator or experiment note."""

    @field_validator("frame_rate_hz")
    @classmethod
    def validate_frame_rate_hz(cls, value: float | None) -> float | None:
        """Reject non-positive frame-rate values."""
        if value is not None and value <= 0:
            raise ValueError("frame_rate_hz must be positive when provided")
        return value


class RunPlanRequest(BaseConfig):
    """Input contract for planning a benchmark run."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    video_path: Path
    """Path to the input video that will be processed."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    mode: PipelineMode = PipelineMode.BATCH
    """Execution mode requested for the run."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""

    frame_stride: int = Field(default=1, ge=1)
    """Frame subsampling stride applied during ingestion."""

    enable_dense_mapping: bool = True
    """Whether the plan should include dense map export."""

    compare_to_arcore: bool = True
    """Whether the plan should reserve an ARCore comparison stage."""

    build_ground_truth_cloud: bool = True
    """Whether the plan should include a reference reconstruction stage."""

    capture: CaptureMetadataConfig = Field(default_factory=CaptureMetadataConfig)
    """Capture-side metadata stored in the manifest."""


class RunPlanStage(BaseConfig):
    """One typed stage in a benchmark run plan."""

    id: RunPlanStageId
    """Stable identifier for the stage."""

    title: str
    """Short human-readable stage title."""

    summary: str
    """Short description of the stage intent."""

    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""


class RunPlan(BaseConfig):
    """Planner output returned to the CLI or UI layer."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    mode: PipelineMode
    """Execution mode chosen for the run."""

    method: MethodId
    """External monocular VSLAM backend chosen for the run."""

    input_video: Path
    """Input video path associated with the run."""

    artifact_root: Path
    """Root directory for all run artifacts."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""


class CaptureManifest(BaseConfig):
    """Repo-owned manifest persisted at the start of a run."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    mode: PipelineMode
    """Execution mode chosen for the run."""

    method: MethodId
    """External monocular VSLAM backend chosen for the run."""

    input_video: Path
    """Input video path captured in the manifest."""

    output_root: Path
    """Artifact root reserved for the run."""

    frame_stride: int
    """Frame subsampling stride applied during planning."""

    capture: CaptureMetadataConfig = Field(default_factory=CaptureMetadataConfig)
    """Capture-side metadata persisted with the run."""


class TrajectoryArtifactMetadata(BaseConfig):
    """Sidecar metadata for the normalized trajectory artifact."""

    artifact_path: Path
    """Path to the trajectory artifact."""

    method: MethodId
    """Method that produced the trajectory."""

    format: str = "tum"
    """Normalized trajectory format."""

    frame_name: str = "world"
    """Frame name used for the stored transform target."""

    transform_convention: str = "T_world_camera"
    """Explicit transform naming convention."""

    units: str = "meters"
    """Metric unit used for geometry."""

    timestamp_source: TimestampSource = TimestampSource.CAPTURE
    """Timestamp provenance attached to the trajectory."""

    alignment_mode: AlignmentMode = AlignmentMode.NONE
    """Alignment mode applied before evaluation."""


class DenseArtifactMetadata(BaseConfig):
    """Sidecar metadata for the normalized dense geometry artifact."""

    artifact_path: Path
    """Path to the dense geometry artifact."""

    method: MethodId
    """Method that produced the dense geometry."""

    format: str = "ply"
    """Normalized dense geometry format."""

    frame_name: str = "world"
    """Frame name used for the dense geometry."""

    units: str = "meters"
    """Metric unit used for geometry."""

    color_available: bool = False
    """Whether the geometry artifact currently carries color information."""

    alignment_mode: AlignmentMode = AlignmentMode.NONE
    """Alignment mode applied before comparison."""


class RunPlanInsight(BaseConfig):
    """Interpretable explanation attached to a plan."""

    title: str
    """Short insight title."""

    detail: str
    """Human-readable explanation of the planning consequence."""

    tone: InsightTone = InsightTone.INFO
    """Visual tone used in the workbench."""


class WorkspaceArtifact(BaseConfig):
    """A concrete artifact created during workspace materialization."""

    stage_id: RunPlanStageId
    """Stage that owns the artifact."""

    label: str
    """Human-readable artifact label."""

    path: Path
    """Filesystem path to the artifact."""

    kind: str
    """Artifact kind used by the workbench."""

    is_placeholder: bool = False
    """Whether the artifact contains only placeholder content."""


class MaterializedWorkspace(BaseConfig):
    """Summary returned after materializing a planned run workspace."""

    artifact_root: Path
    """Root directory for the materialized run."""

    capture_manifest_path: Path
    """Path to the persisted capture manifest."""

    run_request_path: Path
    """Path to the persisted run-request snapshot."""

    run_plan_path: Path
    """Path to the persisted run-plan snapshot."""

    artifacts: list[WorkspaceArtifact] = Field(default_factory=list)
    """Artifacts created while materializing the workspace."""


__all__ = [
    "AlignmentMode",
    "CaptureManifest",
    "CaptureMetadataConfig",
    "DenseArtifactMetadata",
    "InsightTone",
    "MaterializedWorkspace",
    "MethodId",
    "PipelineMode",
    "RunPlan",
    "RunPlanInsight",
    "RunPlanRequest",
    "RunPlanStage",
    "RunPlanStageId",
    "TimestampSource",
    "TrajectoryArtifactMetadata",
    "WorkspaceArtifact",
]
