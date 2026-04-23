"""Pipeline request, source, backend, and placement contracts.

This module contains the main typed entrypoint into :mod:`prml_vslam.pipeline`.
It collects source selection, backend configuration, benchmark policy,
alignment policy, visualization policy, and runtime placement into one
:class:`RunRequest` that can deterministically compile into a
:class:`prml_vslam.pipeline.contracts.plan.RunPlan`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, TypeAlias

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.alignment.contracts import AlignmentConfig
from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    ReferenceSource,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.datasets.contracts import (
    DatasetId,
    DatasetServingConfig,
    FrameSelectionConfig,
)
from prml_vslam.interfaces import Record3DTransportId
from prml_vslam.methods.config_contracts import MethodId, SlamOutputPolicy
from prml_vslam.methods.configs import (
    BackendConfig,
    Mast3rSlamBackendConfig,
    MockSlamBackendConfig,
    VistaSlamBackendConfig,
)
from prml_vslam.utils import BaseConfig
from prml_vslam.visualization.contracts import VisualizationConfig

from .execution import RayRuntimeConfig, RunRuntimeConfig
from .mode import PipelineMode
from .stages import StageKey


# TODO(pipeline-refactor/WP-02): Replace SourceSpec request variants with
# SourceStageConfig plus source-owned backend config variants.
class VideoSourceSpec(FrameSelectionConfig):
    """Describe one raw video source that the pipeline should normalize offline.

    Raw-video requests provide image data only. Any reference trajectories,
    calibration, or RGB-D observations must be supplied by another source type
    or by later explicit benchmark preparation.
    """

    model_config = ConfigDict(extra="forbid")

    video_path: Path
    """Path to the input video that will be processed."""


# TODO(pipeline-refactor/WP-02): Replace SourceSpec request variants with
# SourceStageConfig plus dataset/source-owned backend config variants.
class DatasetSourceSpec(FrameSelectionConfig):
    """Describe one repository-owned dataset sequence selected for a run.

    This spec keeps dataset discovery at the request boundary while delegating
    actual normalization to :mod:`prml_vslam.datasets` and source resolution in
    :mod:`prml_vslam.pipeline.source_resolver`.
    """

    model_config = ConfigDict(extra="forbid")

    dataset_id: DatasetId
    """Dataset family that owns the sequence."""

    sequence_id: str
    """Dataset-specific sequence identifier."""

    dataset_serving: DatasetServingConfig | None = None
    """Typed dataset-serving semantics carried through request and manifest boundaries."""

    respect_video_rotation: bool = False
    """Whether ADVIO replay should honor video rotation metadata when available."""

    @model_validator(mode="after")
    def validate_dataset_serving(self) -> DatasetSourceSpec:
        """Enforce that dataset-serving semantics match the selected dataset family."""
        if self.dataset_id is DatasetId.ADVIO and self.dataset_serving is None:
            raise ValueError("ADVIO dataset sources must provide `dataset_serving`.")
        if self.dataset_id is not DatasetId.ADVIO and self.dataset_serving is not None:
            raise ValueError("Only ADVIO dataset sources currently support `dataset_serving`.")
        return self


# TODO(pipeline-refactor/WP-02): Replace SourceSpec request variants with
# SourceStageConfig plus IO-owned Record3D transport config.
class Record3DLiveSourceSpec(BaseConfig):
    """Describe one live Record3D source selected for streaming execution.

    USB and Wi-Fi Preview are both supported typed transports. This request
    object selects transport and device addressing only; live packet decoding
    belongs to :mod:`prml_vslam.io`, and SLAM backend selection belongs to the
    separate :class:`SlamStageConfig`.
    """

    model_config = ConfigDict(extra="forbid")

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


SourceSpec = VideoSourceSpec | DatasetSourceSpec | Record3DLiveSourceSpec
BackendConfigValue: TypeAlias = Path | str | int | float | bool | None
BackendSpec: TypeAlias = BackendConfig


# TODO(pipeline-refactor/WP-02): Replace per-stage placement request fragments
# with StageExecutionConfig, ResourceSpec, and PlacementConstraint.
class StagePlacement(BaseConfig):
    """Record legacy scheduling preferences for one individual stage.

    This is a migration contact for target
    :class:`prml_vslam.pipeline.stages.base.config.StageExecutionConfig` and
    :class:`prml_vslam.pipeline.stages.base.config.ResourceSpec`. Keep new code
    stage-config-oriented unless it is preserving old request compatibility.
    """

    resources: dict[str, float] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-02): Replace request-level placement collection
# with stage execution policy on target stage configs.
class PlacementPolicy(BaseConfig):
    """Collect per-stage placement hints translated only by the backend layer."""

    by_stage: dict[StageKey, StagePlacement] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-02): Rehome as stage-local declarative
# SlamStageConfig; backend config remains method-owned.
class SlamStageConfig(BaseConfig):
    """Bundle the selected backend config and SLAM output policy for the run.

    This current request section is the migration predecessor of the
    stage-local target SLAM config. Backend config remains method-owned, output
    materialization policy remains method-owned, and pipeline code owns only
    stage lifecycle and run association for the resulting artifacts.
    """

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """Output materialization wishes for the selected backend."""

    backend: BackendConfig
    """Executable backend spec and source of truth for backend selection."""

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_backend_kind(cls, data: Any) -> Any:
        """Accept the previous `kind` backend discriminator at request boundaries."""
        if not isinstance(data, dict):
            return data
        backend = data.get("backend")
        if not isinstance(backend, dict) or "method_id" in backend or "kind" not in backend:
            return data
        normalized = dict(data)
        normalized_backend = dict(backend)
        normalized_backend["method_id"] = normalized_backend.pop("kind")
        normalized["backend"] = normalized_backend
        return normalized


# TODO(pipeline-refactor/WP-02): Supersede with RunConfig as the persisted
# declarative root after app/CLI compatibility lands.
class RunRequest(BaseConfig):
    """Represent the full typed entry contract for one pipeline run.

    A :class:`RunRequest` is the current compatibility starting point for the
    package architecture. It brings together source selection, method backend
    config, optional benchmark and alignment stages, viewer policy, and runtime
    placement hints that eventually compile into a
    :class:`prml_vslam.pipeline.contracts.plan.RunPlan`. New persisted configs
    should prefer :class:`prml_vslam.pipeline.config.RunConfig`, which keeps
    target stage sections explicit while preserving this request shape for
    existing app and CLI launch paths.
    """

    experiment_name: str
    """Human-readable name for the benchmark run."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Whether the run is offline-only or live-backed."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    source: SourceSpec
    """Source specification normalized before the main benchmark stages run."""

    slam: SlamStageConfig
    """SLAM-stage configuration."""

    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    """Benchmark-policy configuration kept outside the pipeline core."""

    alignment: AlignmentConfig = Field(default_factory=AlignmentConfig)
    """Derived alignment policy kept separate from native backend semantics."""

    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    """Viewer-export policy kept outside pipeline execution semantics."""

    placement: PlacementPolicy = Field(default_factory=PlacementPolicy)
    """Placement policy translated into backend-specific scheduling controls."""

    runtime: RunRuntimeConfig = Field(default_factory=RunRuntimeConfig)
    """Repo-owned execution-lifecycle policy for the selected run."""


def build_run_request(
    *,
    experiment_name: str,
    mode: PipelineMode = PipelineMode.OFFLINE,
    output_dir: Path,
    source: SourceSpec,
    method: MethodId,
    max_frames: int | None = None,
    backend_overrides: dict[str, BackendConfigValue] | None = None,
    emit_dense_points: bool = True,
    emit_sparse_points: bool = True,
    reference_enabled: bool = False,
    trajectory_eval_enabled: bool = False,
    trajectory_baseline: ReferenceSource = ReferenceSource.GROUND_TRUTH,
    evaluate_cloud: bool = False,
    evaluate_efficiency: bool = False,
    ground_alignment_enabled: bool = False,
    connect_live_viewer: bool = False,
    export_viewer_rrd: bool = False,
) -> RunRequest:
    """Build one canonical :class:`RunRequest` from source, backend, and policy selections.

    Use this helper when app, CLI, or tests want the repository-owned defaults
    for optional benchmark, alignment, and visualization policy without
    assembling the full request object manually.
    """
    backend_payload: dict[str, BackendConfigValue] = {"max_frames": max_frames}
    if backend_overrides is not None:
        backend_payload.update(backend_overrides)
    match method:
        case MethodId.MOCK:
            backend = MockSlamBackendConfig.model_validate({"method_id": MethodId.MOCK, **backend_payload})
        case MethodId.VISTA:
            backend = VistaSlamBackendConfig.model_validate({"method_id": MethodId.VISTA, **backend_payload})
        case MethodId.MAST3R:
            backend = Mast3rSlamBackendConfig.model_validate({"method_id": MethodId.MAST3R, **backend_payload})
    return RunRequest(
        experiment_name=experiment_name,
        mode=mode,
        output_dir=output_dir,
        source=source,
        slam=SlamStageConfig(
            backend=backend,
            outputs={
                "emit_dense_points": emit_dense_points,
                "emit_sparse_points": emit_sparse_points,
            },
        ),
        benchmark=BenchmarkConfig(
            reference={"enabled": reference_enabled},
            trajectory=TrajectoryBenchmarkConfig(
                enabled=trajectory_eval_enabled,
                baseline_source=trajectory_baseline,
            ),
            cloud=CloudBenchmarkConfig(enabled=evaluate_cloud),
            efficiency=EfficiencyBenchmarkConfig(enabled=evaluate_efficiency),
        ),
        alignment=AlignmentConfig(
            ground={"enabled": ground_alignment_enabled},
        ),
        visualization=VisualizationConfig(
            connect_live_viewer=connect_live_viewer,
            export_viewer_rrd=export_viewer_rrd,
        ),
    )


def build_backend_spec(
    *,
    method: MethodId,
    max_frames: int | None = None,
    overrides: dict[str, BackendConfigValue] | None = None,
) -> BackendSpec:
    """Build a typed backend config from a selected method and optional overrides."""
    backend_payload: dict[str, BackendConfigValue] = {"max_frames": max_frames}
    if overrides is not None:
        backend_payload.update(overrides)
    match method:
        case MethodId.MOCK:
            return MockSlamBackendConfig.model_validate({"method_id": MethodId.MOCK, **backend_payload})
        case MethodId.VISTA:
            return VistaSlamBackendConfig.model_validate({"method_id": MethodId.VISTA, **backend_payload})
        case MethodId.MAST3R:
            return Mast3rSlamBackendConfig.model_validate({"method_id": MethodId.MAST3R, **backend_payload})


__all__ = [
    "build_backend_spec",
    "build_run_request",
    "BackendSpec",
    "DatasetSourceSpec",
    "PipelineMode",
    "PlacementPolicy",
    "RayRuntimeConfig",
    "Record3DLiveSourceSpec",
    "RunRequest",
    "RunRuntimeConfig",
    "SlamStageConfig",
    "SourceSpec",
    "StagePlacement",
    "VideoSourceSpec",
]
