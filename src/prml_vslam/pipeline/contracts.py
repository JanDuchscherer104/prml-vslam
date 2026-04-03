"""Typed contracts for artifact-first pipeline planning and execution."""

from __future__ import annotations

from enum import Enum, StrEnum
from pathlib import Path
from typing import Literal, Self

from pydantic import Field

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils import BaseConfig, BaseData, PathConfig, RunArtifactPaths


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


SourceSpec = VideoSourceSpec | DatasetSourceSpec | LiveSourceSpec


class TrackingConfig(BaseConfig):
    """Tracking-stage configuration shared by the planner and runners."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""
    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""
    config_path: Path | None = None
    """Optional explicit backend config path."""


class StageToggleConfig(BaseConfig):
    """Boolean toggle used by optional one-off pipeline stages."""

    enabled: bool = True
    """Whether the run should include the corresponding stage."""


class DenseConfig(StageToggleConfig):
    """Boolean toggle used by the optional dense-mapping stage."""


class ReferenceConfig(StageToggleConfig):
    """Boolean toggle used by the optional reference-reconstruction stage."""

    enabled: bool = False
    """Whether the run should include the corresponding stage."""


class EvaluationStageConfig(BaseConfig):
    """Configuration accepted by stage-specific evaluation builder methods."""


class TrajectoryEvaluationConfig(EvaluationStageConfig):
    """Builder marker for trajectory-evaluation stage selection."""


class CloudEvaluationConfig(EvaluationStageConfig):
    """Builder marker for dense-cloud evaluation stage selection."""


class EfficiencyEvaluationConfig(EvaluationStageConfig):
    """Builder marker for efficiency-evaluation stage selection."""


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
    source: SourceSpec = Field(discriminator="kind")
    """Source specification normalized before the main benchmark stages run."""
    tracking: TrackingConfig | None = None
    """Tracking-stage configuration."""
    dense: DenseConfig = Field(default_factory=DenseConfig)
    """Dense-mapping configuration."""
    reference: ReferenceConfig = Field(default_factory=ReferenceConfig)
    """Reference-reconstruction configuration."""
    evaluation: BenchmarkEvaluationConfig = Field(default_factory=BenchmarkEvaluationConfig)
    """Benchmark evaluation configuration."""

    def add_tracking(self, config: TrackingConfig) -> Self:
        self.tracking = config
        return self

    def add_dense(self, config: DenseConfig) -> Self:
        return self._set_stage_toggle("dense", config)

    def add_reference(self, config: ReferenceConfig) -> Self:
        return self._set_stage_toggle("reference", config)

    def add_trajectory_evaluation(self, _config: TrajectoryEvaluationConfig) -> Self:
        return self._enable_evaluation("compare_to_arcore")

    def add_cloud_evaluation(self, _config: CloudEvaluationConfig) -> Self:
        return self._enable_evaluation("evaluate_cloud")

    def add_efficiency_evaluation(self, _config: EfficiencyEvaluationConfig) -> Self:
        return self._enable_evaluation("evaluate_efficiency")

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        if self.tracking is None:
            raise ValueError("RunRequest requires tracking configuration before building a plan.")
        path_config = path_config or PathConfig()
        run_paths = path_config.plan_run_paths(
            experiment_name=self.experiment_name,
            method_slug=self.tracking.method.artifact_slug,
            output_dir=self.output_dir,
        )
        return RunPlan(
            run_id=path_config.slugify_experiment_name(self.experiment_name),
            mode=self.mode,
            method=self.tracking.method,
            artifact_root=run_paths.artifact_root,
            source=self.source,
            stages=self._build_stages(run_paths),
        )

    def _build_stages(self, run_paths: RunArtifactPaths) -> list[RunPlanStage]:
        assert self.tracking is not None
        optional_stages = (
            (
                self.dense.enabled,
                (
                    RunPlanStageId.DENSE_MAPPING,
                    "Export Dense Mapping",
                    "Generate dense geometry artifacts suitable for downstream quality evaluation.",
                    ("dense_points_path",),
                ),
            ),
            (
                self.reference.enabled,
                (
                    RunPlanStageId.REFERENCE_RECONSTRUCTION,
                    "Build Reference Reconstruction",
                    "Reserve the offline reconstruction step used as a dense geometry reference.",
                    ("reference_cloud_path",),
                ),
            ),
            (
                self.evaluation.compare_to_arcore,
                (
                    RunPlanStageId.TRAJECTORY_EVALUATION,
                    "Evaluate Trajectory",
                    "Align the trajectory against the available reference and persist trajectory metrics.",
                    ("trajectory_metrics_path",),
                ),
            ),
            (
                self.evaluation.evaluate_cloud,
                (
                    RunPlanStageId.CLOUD_EVALUATION,
                    "Evaluate Dense Cloud",
                    "Compare reconstructed dense geometry against the reference cloud.",
                    ("cloud_metrics_path",),
                ),
            ),
            (
                self.evaluation.evaluate_efficiency,
                (
                    RunPlanStageId.EFFICIENCY_EVALUATION,
                    "Measure Efficiency",
                    "Persist runtime and resource-usage metrics for the run.",
                    ("efficiency_metrics_path",),
                ),
            ),
        )
        return [
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.INGEST,
                    "Normalize Input Sequence",
                    self._ingest_summary(self.source),
                    ("sequence_manifest_path",),
                ),
            ),
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.SLAM,
                    "Run SLAM Backend",
                    self._method_summary(self.tracking.method),
                    ("trajectory_path", "sparse_points_path"),
                ),
            ),
            *(self._stage_from_spec(run_paths, spec) for enabled, spec in optional_stages if enabled),
            self._stage_from_spec(
                run_paths,
                (
                    RunPlanStageId.SUMMARY,
                    "Write Run Summary",
                    "Persist the stage status and top-level artifact summary for the run.",
                    ("summary_path",),
                ),
            ),
        ]

    @staticmethod
    def _stage_from_spec(
        run_paths: RunArtifactPaths,
        spec: tuple[RunPlanStageId, str, str, tuple[str, ...]],
    ) -> RunPlanStage:
        stage_id, title, summary, output_names = spec
        return RunPlanStage(
            id=stage_id,
            title=title,
            summary=summary,
            outputs=[getattr(run_paths, output_name) for output_name in output_names],
        )

    @staticmethod
    def _ingest_summary(source: SourceSpec) -> str:
        match source:
            case VideoSourceSpec(video_path=video_path, frame_stride=frame_stride):
                return f"Decode '{video_path}' at stride {frame_stride} and materialize a normalized sequence manifest."
            case DatasetSourceSpec(dataset_id=dataset_id, sequence_id=sequence_id):
                return f"Normalize dataset sequence '{dataset_id.value}:{sequence_id}' into a shared sequence manifest."
            case LiveSourceSpec(source_id=source_id, persist_capture=persist_capture):
                persistence = "with persistence" if persist_capture else "without persistence"
                return f"Capture the live source '{source_id}' {persistence} into a replayable sequence manifest."

    @staticmethod
    def _method_summary(method: MethodId) -> str:
        return f"Plan the {method.display_name} wrapper and export trajectory plus sparse geometry artifacts."

    def _set_stage_toggle(self, field_name: Literal["dense", "reference"], config: StageToggleConfig) -> Self:
        setattr(self, field_name, config.model_copy(update={"enabled": True}))
        return self

    def _enable_evaluation(
        self,
        field_name: Literal["compare_to_arcore", "evaluate_cloud", "evaluate_efficiency"],
    ) -> Self:
        self.evaluation = self.evaluation.model_copy(update={field_name: True})
        return self


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
    source: SourceSpec = Field(discriminator="kind")
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


class MetricsBundle(BaseData):
    """Persisted metric-artifact bundle."""

    metrics_json: ArtifactRef
    """Serialized metric results."""


class TrajectoryMetrics(MetricsBundle):
    """Persisted trajectory-metric artifact bundle."""


class CloudMetrics(MetricsBundle):
    """Persisted dense-cloud metric artifact bundle."""


class EfficiencyMetrics(MetricsBundle):
    """Persisted efficiency-metric artifact bundle."""


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


__all__ = """
ArtifactRef BenchmarkEvaluationConfig CloudEvaluationConfig CloudMetrics DatasetSourceSpec DenseArtifacts
DenseConfig EfficiencyEvaluationConfig EfficiencyMetrics LiveSourceSpec PipelineMode
ReferenceArtifacts ReferenceConfig RunPlan RunPlanStage RunPlanStageId RunRequest RunSummary
SequenceManifest StageExecutionStatus StageManifest TrackingArtifacts TrackingConfig TrajectoryEvaluationConfig
TrajectoryMetrics VideoSourceSpec
""".split()
