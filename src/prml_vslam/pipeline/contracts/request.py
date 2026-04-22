"""Pipeline request, source, backend, and placement contracts.

This module contains the main typed entrypoint into :mod:`prml_vslam.pipeline`.
It collects source selection, backend configuration, benchmark policy,
alignment policy, visualization policy, and runtime placement into one
:class:`RunRequest` that can deterministically compile into a
:class:`prml_vslam.pipeline.contracts.plan.RunPlan`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

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
from prml_vslam.utils import BaseConfig, PathConfig
from prml_vslam.visualization.contracts import VisualizationConfig

if TYPE_CHECKING:
    from .plan import RunPlan
from .stages import StageKey


class PipelineMode(StrEnum):
    """Select whether the run is batch/offline or live/incremental."""

    OFFLINE = "offline"
    STREAMING = "streaming"


# TODO(pipeline-refactor/WP-02): Replace SourceSpec request variants with
# SourceStageConfig plus source-owned backend config variants.
class VideoSourceSpec(FrameSelectionConfig):
    """Describe one raw video source that the pipeline should normalize offline."""

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
    """Describe one live Record3D source selected for streaming execution."""

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
RayLocalHeadLifecycle: TypeAlias = Literal["ephemeral", "reusable"]


# TODO(pipeline-refactor/WP-02): Replace per-stage placement request fragments
# with StageExecutionConfig, ResourceSpec, and PlacementConstraint.
class StagePlacement(BaseConfig):
    """Record scheduling preferences for one individual stage."""

    resources: dict[str, float] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-02): Replace request-level placement collection
# with stage execution policy on target stage configs.
class PlacementPolicy(BaseConfig):
    """Collect per-stage placement hints translated only by the backend layer."""

    by_stage: dict[StageKey, StagePlacement] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-02): Move runtime lifecycle policy into RunConfig
# runtime settings without stage construction semantics.
class RayRuntimeConfig(BaseConfig):
    """Configure repository-owned local Ray lifecycle behavior."""

    local_head_lifecycle: RayLocalHeadLifecycle = "ephemeral"
    """Whether the auto-started local Ray head is torn down or preserved after a run."""


# TODO(pipeline-refactor/WP-02): Move run lifecycle policy into target
# RunConfig.runtime and retire RunRequest compatibility.
class RunRuntimeConfig(BaseConfig):
    """Collect repository-owned execution-lifecycle policy for one run."""

    ray: RayRuntimeConfig = Field(default_factory=RayRuntimeConfig)
    """Local Ray runtime policy translated by the backend layer."""


# TODO(pipeline-refactor/WP-02): Rehome as stage-local declarative
# SlamStageConfig; backend config remains method-owned.
class SlamStageConfig(BaseConfig):
    """Bundle the selected backend config and SLAM output policy for the run."""

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

    A :class:`RunRequest` is the main click-through starting point for the
    package architecture. It brings together the normalized source selection,
    backend configuration, optional benchmark and alignment stages, viewer
    policy, and runtime placement hints that eventually compile into a
    :class:`prml_vslam.pipeline.contracts.plan.RunPlan`.
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

    def build(self, path_config: PathConfig | None = None) -> RunPlan:
        """Compile the canonical :class:`RunPlan` for this request.

        Planning is deterministic and side-effect free. It validates
        request-level invariants and delegates stage compilation to
        :class:`prml_vslam.pipeline.stage_registry.StageRegistry`.
        """
        from prml_vslam.pipeline.stage_registry import StageRegistry

        if self.benchmark.cloud.enabled and not self.slam.outputs.emit_dense_points:
            raise ValueError("Cloud evaluation requires `slam.outputs.emit_dense_points=True`.")
        if self.alignment.ground.enabled and not (
            self.slam.outputs.emit_dense_points or self.slam.outputs.emit_sparse_points
        ):
            raise ValueError("Ground alignment requires at least one point-cloud output from the SLAM stage.")
        config = PathConfig() if path_config is None else path_config
        return StageRegistry.default().compile(request=self, path_config=config)


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
    "Record3DLiveSourceSpec",
    "RunRequest",
    "SlamStageConfig",
    "SourceSpec",
    "StagePlacement",
    "VideoSourceSpec",
]
