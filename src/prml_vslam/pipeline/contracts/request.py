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
from typing import TYPE_CHECKING, Literal, TypeAlias

from pydantic import Field, model_validator

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
from prml_vslam.methods.configs import (
    BackendConfig,
    Mast3rSlamBackendConfig,
    MockSlamBackendConfig,
    VistaSlamBackendConfig,
)
from prml_vslam.methods.contracts import MethodId, SlamOutputPolicy
from prml_vslam.utils import BaseConfig, PathConfig
from prml_vslam.visualization.contracts import VisualizationConfig

if TYPE_CHECKING:
    from .plan import RunPlan
from .stages import StageKey


class PipelineMode(StrEnum):
    """Select whether the run is batch/offline or live/incremental."""

    OFFLINE = "offline"
    STREAMING = "streaming"

    @property
    def label(self) -> str:
        """Return the human-readable mode label shown in planning and UI surfaces."""
        return {
            self.OFFLINE: "Offline (batch)",
            self.STREAMING: "Streaming (incremental)",
        }[self]


class VideoSourceSpec(FrameSelectionConfig):
    """Describe one raw video source that the pipeline should normalize offline."""

    video_path: Path
    """Path to the input video that will be processed."""


class DatasetSourceSpec(FrameSelectionConfig):
    """Describe one repository-owned dataset sequence selected for a run.

    This spec keeps dataset discovery at the request boundary while delegating
    actual normalization to :mod:`prml_vslam.datasets` and source resolution in
    :mod:`prml_vslam.pipeline.source_resolver`.
    """

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


class Record3DLiveSourceSpec(BaseConfig):
    """Describe one live Record3D source selected for streaming execution."""

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
RayLocalHeadLifecycle: TypeAlias = Literal["ephemeral", "reusable"]


class StagePlacement(BaseConfig):
    """Record scheduling preferences for one individual stage."""

    resources: dict[str, float] = Field(default_factory=dict)


class PlacementPolicy(BaseConfig):
    """Collect per-stage placement hints translated only by the backend layer."""

    by_stage: dict[StageKey, StagePlacement] = Field(default_factory=dict)


class RayRuntimeConfig(BaseConfig):
    """Configure repository-owned local Ray lifecycle behavior."""

    local_head_lifecycle: RayLocalHeadLifecycle = "ephemeral"
    """Whether the auto-started local Ray head is torn down or preserved after a run."""


class RunRuntimeConfig(BaseConfig):
    """Collect repository-owned execution-lifecycle policy for one run."""

    ray: RayRuntimeConfig = Field(default_factory=RayRuntimeConfig)
    """Local Ray runtime policy translated by the backend layer."""


class SlamStageConfig(BaseConfig):
    """Bundle the selected backend config and SLAM output policy for the run."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """Output materialization wishes for the selected backend."""

    backend: BackendConfig
    """Executable backend spec and source of truth for backend selection."""


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


__all__ = [
    "build_run_request",
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
