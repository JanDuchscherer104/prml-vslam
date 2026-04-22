"""Target pipeline run configuration and stage-section mapping.

This module introduces the target-facing ``RunConfig`` root while preserving a
compatibility bridge to the current ``RunRequest`` planner. The config objects
here validate and describe planning policy only; runtime construction remains
owned by later runtime-manager work packages.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Self

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.alignment.contracts import AlignmentConfig
from prml_vslam.benchmark import BenchmarkConfig
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.interfaces import Record3DTransportId
from prml_vslam.methods.config_contracts import MethodId, SlamOutputPolicy
from prml_vslam.methods.configs import BackendConfig
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.request import (
    DatasetSourceSpec,
    PipelineMode,
    PlacementPolicy,
    Record3DLiveSourceSpec,
    RunRequest,
    RunRuntimeConfig,
    SlamStageConfig,
    SourceSpec,
    StagePlacement,
    VideoSourceSpec,
)
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import ResourceSpec, StageConfig
from prml_vslam.pipeline.stages.source.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
    source_backend_config_from_source_spec,
)
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths
from prml_vslam.visualization.contracts import VisualizationConfig


class TargetStageKey(StrEnum):
    """Name the target public stage-key vocabulary."""

    SOURCE = "source"
    SLAM = "slam"
    ALIGN_GROUND = "align.ground"
    EVALUATE_TRAJECTORY = "evaluate.trajectory"
    RECONSTRUCTION = "reconstruction"
    EVALUATE_CLOUD = "evaluate.cloud"
    EVALUATE_EFFICIENCY = "evaluate.efficiency"
    SUMMARY = "summary"


# TODO(pipeline-refactor/WP-10): Remove current-to-target stage-key alias maps
# after persisted configs, summaries, manifests, and old-run inspection use the
# target stage-key vocabulary directly.
CURRENT_TO_TARGET_STAGE_KEYS: dict[StageKey, TargetStageKey] = {
    StageKey.INGEST: TargetStageKey.SOURCE,
    StageKey.SLAM: TargetStageKey.SLAM,
    StageKey.GROUND_ALIGNMENT: TargetStageKey.ALIGN_GROUND,
    StageKey.TRAJECTORY_EVALUATION: TargetStageKey.EVALUATE_TRAJECTORY,
    StageKey.REFERENCE_RECONSTRUCTION: TargetStageKey.RECONSTRUCTION,
    StageKey.CLOUD_EVALUATION: TargetStageKey.EVALUATE_CLOUD,
    StageKey.EFFICIENCY_EVALUATION: TargetStageKey.EVALUATE_EFFICIENCY,
    StageKey.SUMMARY: TargetStageKey.SUMMARY,
}
TARGET_TO_CURRENT_STAGE_KEYS: dict[TargetStageKey, StageKey] = {
    target_key: current_key for current_key, target_key in CURRENT_TO_TARGET_STAGE_KEYS.items()
}
TARGET_STAGE_SECTIONS: dict[TargetStageKey, str] = {
    TargetStageKey.SOURCE: "source",
    TargetStageKey.SLAM: "slam",
    TargetStageKey.ALIGN_GROUND: "align_ground",
    TargetStageKey.EVALUATE_TRAJECTORY: "evaluate_trajectory",
    TargetStageKey.RECONSTRUCTION: "reconstruction",
    TargetStageKey.EVALUATE_CLOUD: "evaluate_cloud",
    TargetStageKey.EVALUATE_EFFICIENCY: "evaluate_efficiency",
    TargetStageKey.SUMMARY: "summary",
}
SECTION_TO_TARGET_STAGE_KEYS: dict[str, TargetStageKey] = {
    section: target_key for target_key, section in TARGET_STAGE_SECTIONS.items()
}
# TODO(pipeline-refactor/WP-10): Remove this placement-projection helper payload
# type after `StageExecutionConfig` fully replaces `PlacementPolicy`.
ExecutionPayload = dict[str, dict[str, float | dict[str, float]]]


class SourceStageSectionConfig(StageConfig):
    """Target source stage section with optional source backend config."""

    model_config = ConfigDict(extra="forbid")

    stage_key: StageKey | None = StageKey.INGEST
    """Current executable stage key used during migration."""

    backend: SourceBackendConfig | None = None
    """Concrete source backend config used for RunConfig launch/planning."""


class SlamStageSectionConfig(StageConfig):
    """Target SLAM stage section with backend and output policy."""

    model_config = ConfigDict(extra="forbid")

    stage_key: StageKey | None = StageKey.SLAM
    """Current executable stage key used during migration."""

    backend: BackendConfig | None = None
    """Selected SLAM backend config."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """SLAM output materialization policy."""


class StageBundle(BaseConfig):
    """Fixed target stage-section bundle for one run config."""

    model_config = ConfigDict(extra="forbid")

    source: SourceStageSectionConfig = Field(default_factory=SourceStageSectionConfig)
    """Source-normalization stage section."""

    slam: SlamStageSectionConfig = Field(default_factory=SlamStageSectionConfig)
    """SLAM stage section."""

    align_ground: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.GROUND_ALIGNMENT, enabled=False)
    )
    """Ground-alignment stage section."""

    evaluate_trajectory: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.TRAJECTORY_EVALUATION, enabled=False)
    )
    """Trajectory-evaluation stage section."""

    reconstruction: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.REFERENCE_RECONSTRUCTION, enabled=False)
    )
    """Reference/future reconstruction umbrella stage section."""

    evaluate_cloud: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.CLOUD_EVALUATION, enabled=False)
    )
    """Dense-cloud evaluation stage section."""

    evaluate_efficiency: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.EFFICIENCY_EVALUATION, enabled=False)
    )
    """Runtime-efficiency evaluation stage section."""

    summary: StageConfig = Field(default_factory=lambda: StageConfig(stage_key=StageKey.SUMMARY))
    """Summary-projection stage section."""

    # TODO(pipeline-refactor/WP-10): Stop normalizing target sections to current
    # `StageKey` values after persisted/public stage-key aliases are removed.
    @model_validator(mode="after")
    def validate_stage_keys(self) -> Self:
        """Ensure every section carries the expected migration stage key."""
        object.__setattr__(self, "source", _section_config(self.source, StageKey.INGEST))
        object.__setattr__(self, "slam", _section_config(self.slam, StageKey.SLAM))
        object.__setattr__(self, "align_ground", _section_config(self.align_ground, StageKey.GROUND_ALIGNMENT))
        object.__setattr__(
            self,
            "evaluate_trajectory",
            _section_config(self.evaluate_trajectory, StageKey.TRAJECTORY_EVALUATION),
        )
        object.__setattr__(
            self,
            "reconstruction",
            _section_config(self.reconstruction, StageKey.REFERENCE_RECONSTRUCTION),
        )
        object.__setattr__(self, "evaluate_cloud", _section_config(self.evaluate_cloud, StageKey.CLOUD_EVALUATION))
        object.__setattr__(
            self,
            "evaluate_efficiency",
            _section_config(self.evaluate_efficiency, StageKey.EFFICIENCY_EVALUATION),
        )
        object.__setattr__(self, "summary", _section_config(self.summary, StageKey.SUMMARY))
        return self

    # TODO(pipeline-refactor/WP-09): Remove RunRequest-to-RunConfig projection
    # after app/CLI launch paths submit RunConfig directly.
    @classmethod
    def from_run_request(cls, request: RunRequest) -> StageBundle:
        """Project current request gates into the target section bundle."""
        return cls(
            source={
                "execution": _execution_payload_from_placement(request.placement, StageKey.INGEST),
                "backend": source_backend_config_from_source_spec(request.source),
            },
            slam={
                "execution": _execution_payload_from_placement(request.placement, StageKey.SLAM),
                "backend": request.slam.backend,
                "outputs": request.slam.outputs,
            },
            align_ground={
                "enabled": request.alignment.ground.enabled,
                "execution": _execution_payload_from_placement(request.placement, StageKey.GROUND_ALIGNMENT),
            },
            evaluate_trajectory={
                "enabled": request.benchmark.trajectory.enabled,
                "execution": _execution_payload_from_placement(request.placement, StageKey.TRAJECTORY_EVALUATION),
            },
            reconstruction={
                "enabled": request.benchmark.reference.enabled,
                "execution": _execution_payload_from_placement(request.placement, StageKey.REFERENCE_RECONSTRUCTION),
            },
            evaluate_cloud={
                "enabled": request.benchmark.cloud.enabled,
                "execution": _execution_payload_from_placement(request.placement, StageKey.CLOUD_EVALUATION),
            },
            evaluate_efficiency={
                "enabled": request.benchmark.efficiency.enabled,
                "execution": _execution_payload_from_placement(request.placement, StageKey.EFFICIENCY_EVALUATION),
            },
            summary={"execution": _execution_payload_from_placement(request.placement, StageKey.SUMMARY)},
        )

    def section(self, section: TargetStageKey | str) -> StageConfig:
        """Return a section config by target stage key or TOML section name."""
        return getattr(self, section_for_target_stage(_target_stage_key_from_section_or_key(section)))


class RunConfig(BaseConfig):
    """Target persisted root config with a current-planner compatibility bridge."""

    model_config = ConfigDict(extra="forbid")

    experiment_name: str
    """Human-readable benchmark run name."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Offline or streaming execution mode."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    stages: StageBundle = Field(default_factory=StageBundle)
    """Target stage-section bundle."""

    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    """Viewer/export policy kept outside stage runtime semantics."""

    runtime: RunRuntimeConfig = Field(default_factory=RunRuntimeConfig)
    """Run execution lifecycle policy translated by runtime packages."""

    # TODO(pipeline-refactor/WP-09): Remove compatibility source/slam request
    # fields after stage-specific config sections drive app and CLI launch.
    source: SourceSpec | None = None
    """Compatibility source spec used until source stage configs are implemented."""

    slam: SlamStageConfig | None = None
    """Compatibility SLAM stage config used until stage-local config lands."""

    # TODO(pipeline-refactor/WP-09): Remove benchmark/alignment/placement
    # compatibility fields after target stage sections and app/CLI adapters
    # preserve current config behavior without RunRequest projection.
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    """Benchmark policy bundle preserved for current request compatibility."""

    alignment: AlignmentConfig = Field(default_factory=AlignmentConfig)
    """Alignment policy bundle preserved for current request compatibility."""

    placement: PlacementPolicy = Field(default_factory=PlacementPolicy)
    """Compatibility placement policy preserved until stage execution config drives placement."""

    # TODO(pipeline-refactor/WP-09): Remove legacy RunRequest shape parsing after
    # current TOML files migrate to `[stages.*]` or app/CLI compatibility ends.
    @model_validator(mode="before")
    @classmethod
    def add_legacy_stage_bundle(cls, data: Any) -> Any:
        """Populate target stage sections when parsing the legacy request shape."""
        if not isinstance(data, dict) or "stages" in data:
            return data
        normalized = dict(data)
        normalized["stages"] = _legacy_stage_bundle_payload(normalized)
        return normalized

    # TODO(pipeline-refactor/WP-09): Remove RunRequest-to-RunConfig projection
    # after app/CLI launch paths submit RunConfig directly.
    @classmethod
    def from_run_request(cls, request: RunRequest) -> RunConfig:
        """Build the target root config from the current request contract."""
        return cls(
            experiment_name=request.experiment_name,
            mode=request.mode,
            output_dir=request.output_dir,
            stages=StageBundle.from_run_request(request),
            visualization=request.visualization,
            runtime=request.runtime,
            source=request.source,
            slam=request.slam,
            benchmark=request.benchmark,
            alignment=request.alignment,
            placement=request.placement,
        )

    # TODO(pipeline-refactor/WP-09): Remove RunRequest compatibility projection
    # after RunConfig is the direct app/CLI launch contract.
    def to_run_request(self) -> RunRequest:
        """Project this config into the current request contract."""
        self._validate_required_compatibility_sections()
        source = self._resolve_runtime_source_spec()
        slam = self._resolve_runtime_slam_stage_config()
        benchmark = self.benchmark.model_copy(
            update={
                "reference": self.benchmark.reference.model_copy(
                    update={"enabled": self.stages.reconstruction.enabled}
                ),
                "trajectory": self.benchmark.trajectory.model_copy(
                    update={"enabled": self.stages.evaluate_trajectory.enabled}
                ),
                "cloud": self.benchmark.cloud.model_copy(update={"enabled": self.stages.evaluate_cloud.enabled}),
                "efficiency": self.benchmark.efficiency.model_copy(
                    update={"enabled": self.stages.evaluate_efficiency.enabled}
                ),
            }
        )
        alignment = self.alignment.model_copy(
            update={"ground": self.alignment.ground.model_copy(update={"enabled": self.stages.align_ground.enabled})}
        )
        placement = self._project_placement_policy()
        return RunRequest(
            experiment_name=self.experiment_name,
            mode=self.mode,
            output_dir=self.output_dir,
            source=source,
            slam=slam,
            benchmark=benchmark,
            alignment=alignment,
            visualization=self.visualization,
            placement=placement,
            runtime=self.runtime,
        )

    def compile_plan(
        self,
        path_config: PathConfig | None = None,
        *,
        fail_on_unavailable: bool = False,
        backend: BackendDescriptor | None = None,
    ) -> RunPlan:
        """Compile a deterministic plan directly from target stage sections."""
        config = PathConfig() if path_config is None else path_config
        plan = _compile_run_plan(run_config=self, path_config=config, backend=backend)
        if fail_on_unavailable:
            unavailable = [stage for stage in plan.stages if not stage.available]
            if unavailable:
                details = ", ".join(
                    f"{stage.key.value}: {stage.availability_reason or 'unavailable'}" for stage in unavailable
                )
                raise ValueError(f"Enabled stage(s) are unavailable: {details}")
        return plan

    # TODO(pipeline-refactor/WP-09): Remove RunRequest projection helpers after
    # RunConfig is the direct app/CLI launch contract.
    def _validate_required_compatibility_sections(self) -> None:
        disabled_required = [
            section
            for section, config in {
                TargetStageKey.SOURCE: self.stages.source,
                TargetStageKey.SLAM: self.stages.slam,
                TargetStageKey.SUMMARY: self.stages.summary,
            }.items()
            if not config.enabled
        ]
        if disabled_required:
            names = ", ".join(section_for_target_stage(section) for section in disabled_required)
            raise ValueError(f"RunConfig launch requires enabled stage section(s): {names}.")

    def _project_placement_policy(self) -> PlacementPolicy:
        by_stage = dict(self.placement.by_stage)
        for target_key in TargetStageKey:
            stage_config = self.stages.section(target_key)
            if stage_config.stage_key is None:
                continue
            resources = _placement_resources_from_resource_spec(stage_config.execution.resources)
            if resources:
                by_stage[stage_config.stage_key] = StagePlacement(resources=resources)
        return self.placement.model_copy(update={"by_stage": by_stage})

    def _resolve_runtime_source_spec(self) -> SourceSpec:
        if self.source is not None:
            return self.source
        backend = self.stages.source.backend
        if backend is None:
            raise ValueError(
                "RunConfig launch requires one source definition via compatibility `source` "
                "or `[stages.source.backend]`."
            )
        return _source_spec_from_backend_config(backend)

    def _resolve_runtime_slam_stage_config(self) -> SlamStageConfig:
        if self.slam is not None:
            return self.slam
        backend = self.stages.slam.backend
        if backend is None:
            raise ValueError(
                "RunConfig launch requires one SLAM backend via compatibility `slam` or `[stages.slam.backend]`."
            )
        return SlamStageConfig(backend=backend, outputs=self.stages.slam.outputs)


def _compile_run_plan(
    *,
    run_config: RunConfig,
    path_config: PathConfig,
    backend: BackendDescriptor | None = None,
) -> RunPlan:
    run_config._validate_required_compatibility_sections()
    source = run_config._resolve_runtime_source_spec()
    slam = run_config._resolve_runtime_slam_stage_config()
    run_paths = path_config.plan_run_paths(
        experiment_name=run_config.experiment_name,
        method_slug=slam.backend.method_id.value,
        output_dir=run_config.output_dir,
    )
    resolved_run_paths = RunArtifactPaths.build(run_paths.artifact_root)
    slam_available, slam_reason = _slam_stage_availability(run_config=run_config, slam=slam, backend=backend)
    plan_stages: list[RunPlanStage] = [
        _plan_stage(key=StageKey.INGEST, outputs=_source_outputs(resolved_run_paths)),
        _plan_stage(
            key=StageKey.SLAM,
            outputs=_slam_outputs(slam=slam, run_paths=resolved_run_paths),
            available=slam_available,
            availability_reason=slam_reason,
        ),
    ]

    if run_config.stages.align_ground.enabled:
        alignment_available, alignment_reason = _ground_alignment_stage_availability(slam=slam, backend=backend)
        plan_stages.append(
            _plan_stage(
                key=StageKey.GROUND_ALIGNMENT,
                outputs=[resolved_run_paths.ground_alignment_path],
                available=alignment_available,
                availability_reason=alignment_reason,
            )
        )
    if run_config.stages.evaluate_trajectory.enabled:
        trajectory_available, trajectory_reason = _trajectory_stage_availability(slam=slam, backend=backend)
        plan_stages.append(
            _plan_stage(
                key=StageKey.TRAJECTORY_EVALUATION,
                outputs=[resolved_run_paths.trajectory_metrics_path],
                available=trajectory_available,
                availability_reason=trajectory_reason,
            )
        )
    if run_config.stages.reconstruction.enabled:
        reconstruction_available, reconstruction_reason = _reference_reconstruction_stage_availability(source=source)
        plan_stages.append(
            _plan_stage(
                key=StageKey.REFERENCE_RECONSTRUCTION,
                outputs=[resolved_run_paths.reference_cloud_path],
                available=reconstruction_available,
                availability_reason=reconstruction_reason,
            )
        )
    if run_config.stages.evaluate_cloud.enabled:
        plan_stages.append(
            _plan_stage(
                key=StageKey.CLOUD_EVALUATION,
                outputs=[resolved_run_paths.cloud_metrics_path],
                available=False,
                availability_reason="Dense-cloud evaluation remains a planned placeholder in this refactor.",
            )
        )
    if run_config.stages.evaluate_efficiency.enabled:
        plan_stages.append(
            _plan_stage(
                key=StageKey.EFFICIENCY_EVALUATION,
                outputs=[resolved_run_paths.efficiency_metrics_path],
                available=False,
                availability_reason="Efficiency evaluation remains a planned placeholder in this refactor.",
            )
        )
    plan_stages.append(
        _plan_stage(
            key=StageKey.SUMMARY,
            outputs=[resolved_run_paths.summary_path, resolved_run_paths.stage_manifests_path],
        )
    )

    return RunPlan(
        run_id=path_config.slugify_experiment_name(run_config.experiment_name),
        mode=run_config.mode,
        artifact_root=run_paths.artifact_root,
        source=source,
        stages=plan_stages,
    )


def _plan_stage(
    *,
    key: StageKey,
    outputs: list[Path],
    available: bool = True,
    availability_reason: str | None = None,
) -> RunPlanStage:
    return RunPlanStage(
        key=key,
        outputs=outputs,
        available=available,
        availability_reason=availability_reason,
    )


def _slam_stage_availability(
    *,
    run_config: RunConfig,
    slam: SlamStageConfig,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam.backend.display_name if backend is None else backend.display_name
    supports_offline = slam.backend.supports_offline if backend is None else backend.capabilities.offline
    supports_streaming = slam.backend.supports_streaming if backend is None else backend.capabilities.streaming
    if run_config.mode is PipelineMode.OFFLINE and not supports_offline:
        return False, f"{display_name} does not support offline execution."
    if run_config.mode is PipelineMode.STREAMING and not supports_streaming:
        return False, f"{display_name} does not support streaming execution."
    return True, None


def _trajectory_stage_availability(
    *,
    slam: SlamStageConfig,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam.backend.display_name if backend is None else backend.display_name
    supports_trajectory = (
        slam.backend.supports_trajectory_benchmark
        if backend is None
        else backend.capabilities.trajectory_benchmark_support
    )
    if not supports_trajectory:
        return False, f"{display_name} does not support repository trajectory evaluation."
    return True, None


def _ground_alignment_stage_availability(
    *,
    slam: SlamStageConfig,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam.backend.display_name if backend is None else backend.display_name
    supports_dense_points = slam.backend.supports_dense_points if backend is None else backend.capabilities.dense_points
    if not supports_dense_points:
        return False, f"{display_name} does not expose point-cloud outputs for ground alignment."
    if not (slam.outputs.emit_dense_points or slam.outputs.emit_sparse_points):
        return False, "Ground alignment requires sparse or dense point-cloud outputs from the SLAM stage."
    return True, None


def _reference_reconstruction_stage_availability(*, source: SourceSpec) -> tuple[bool, str | None]:
    if not isinstance(source, DatasetSourceSpec) or source.dataset_id is not DatasetId.TUM_RGBD:
        return False, "Reference reconstruction currently requires a TUM RGB-D dataset source."
    return True, None


def _source_outputs(run_paths: RunArtifactPaths) -> list[Path]:
    return [run_paths.sequence_manifest_path, run_paths.benchmark_inputs_path]


def _slam_outputs(*, slam: SlamStageConfig, run_paths: RunArtifactPaths) -> list[Path]:
    outputs = [run_paths.trajectory_path]
    if slam.backend.method_id is MethodId.VISTA:
        if slam.outputs.emit_sparse_points or slam.outputs.emit_dense_points:
            outputs.append(run_paths.point_cloud_path)
        return outputs
    if slam.outputs.emit_sparse_points:
        outputs.append(run_paths.sparse_points_path)
    if slam.outputs.emit_dense_points:
        outputs.append(run_paths.dense_points_path)
    return outputs


# TODO(pipeline-refactor/WP-10): Remove current-key alias helper functions after
# persisted configs and old-run inspection no longer need migration aliases.
def target_stage_key_for_current(stage_key: StageKey) -> TargetStageKey:
    """Return the target public key for one current executable key."""
    return CURRENT_TO_TARGET_STAGE_KEYS[stage_key]


def current_stage_key_for_target(target_key: TargetStageKey | str) -> StageKey:
    """Return the current executable key for one target public key."""
    return TARGET_TO_CURRENT_STAGE_KEYS[TargetStageKey(target_key)]


def target_stage_key_for_section(section: str) -> TargetStageKey:
    """Return the target public key for one target TOML section."""
    return SECTION_TO_TARGET_STAGE_KEYS[section]


def section_for_target_stage(target_key: TargetStageKey | str) -> str:
    """Return the target TOML section for one target public stage key."""
    return TARGET_STAGE_SECTIONS[TargetStageKey(target_key)]


def section_for_current_stage(stage_key: StageKey) -> str:
    """Return the target TOML section for one current executable stage key."""
    return section_for_target_stage(target_stage_key_for_current(stage_key))


def current_stage_key_for_section(section: str) -> StageKey:
    """Return the current executable key for one target TOML section."""
    return current_stage_key_for_target(target_stage_key_for_section(section))


def _target_stage_key_from_section_or_key(value: TargetStageKey | str) -> TargetStageKey:
    if isinstance(value, TargetStageKey):
        return value
    try:
        return TargetStageKey(value)
    except ValueError:
        return target_stage_key_for_section(value)


def _section_config(config: StageConfig, expected_key: StageKey) -> StageConfig:
    if config.stage_key is not None and config.stage_key != expected_key:
        raise ValueError(f"Expected stage section for {expected_key.value}, got {config.stage_key.value}.")
    return config.model_copy(update={"stage_key": expected_key})


# TODO(pipeline-refactor/WP-10): Remove PlacementPolicy projection helpers after
# stage execution configs are the only placement config surface.
def _execution_payload_from_placement(placement: PlacementPolicy, stage_key: StageKey) -> ExecutionPayload:
    stage_placement = placement.by_stage.get(stage_key)
    if stage_placement is None:
        return {}
    resources = dict(stage_placement.resources)
    resource_payload: dict[str, float] = {}
    custom_resources = dict(resources)
    num_cpus = custom_resources.pop("CPU", None)
    if num_cpus is not None:
        resource_payload["num_cpus"] = num_cpus
    num_gpus = custom_resources.pop("GPU", None)
    if num_gpus is not None:
        resource_payload["num_gpus"] = num_gpus
    return {
        "resources": {
            **resource_payload,
            "custom_resources": custom_resources,
        }
    }


def _placement_resources_from_resource_spec(resource_spec: ResourceSpec) -> dict[str, float]:
    resources = dict(resource_spec.custom_resources)
    if resource_spec.num_cpus is not None:
        resources["CPU"] = resource_spec.num_cpus
    if resource_spec.num_gpus is not None:
        resources["GPU"] = resource_spec.num_gpus
    return resources


def _source_spec_from_backend_config(backend: SourceBackendConfig) -> SourceSpec:
    match backend:
        case VideoSourceConfig(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps):
            return VideoSourceSpec(video_path=video_path, frame_stride=frame_stride, target_fps=target_fps)
        case AdvioSourceConfig(
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
        ):
            return DatasetSourceSpec(
                dataset_id=DatasetId.ADVIO,
                sequence_id=sequence_id,
                frame_stride=frame_stride,
                target_fps=target_fps,
                dataset_serving=dataset_serving,
                respect_video_rotation=respect_video_rotation,
            )
        case TumRgbdSourceConfig(sequence_id=sequence_id, frame_stride=frame_stride, target_fps=target_fps):
            return DatasetSourceSpec(
                dataset_id=DatasetId.TUM_RGBD,
                sequence_id=sequence_id,
                frame_stride=frame_stride,
                target_fps=target_fps,
            )
        case Record3DSourceConfig(
            frame_stride=frame_stride,
            target_fps=target_fps,
            transport=transport,
            device_index=device_index,
            device_address=device_address,
        ):
            if frame_stride != 1 or target_fps is not None:
                raise ValueError(
                    "RunRequest compatibility launch does not support non-default Record3D source sampling policy."
                )
            return Record3DLiveSourceSpec(
                transport=transport,
                device_index=device_index if transport is Record3DTransportId.USB else None,
                device_address=device_address if transport is Record3DTransportId.WIFI else "",
            )


# TODO(pipeline-refactor/WP-09): Remove legacy RunRequest shape parsing after
# current TOML files migrate to `[stages.*]` or app/CLI compatibility ends.
def _legacy_stage_bundle_payload(data: dict[str, Any]) -> dict[str, dict[str, bool]]:
    benchmark = data.get("benchmark")
    benchmark_payload = benchmark if isinstance(benchmark, dict) else {}
    alignment = data.get("alignment")
    alignment_payload = alignment if isinstance(alignment, dict) else {}
    return {
        "source": {"enabled": True},
        "slam": {"enabled": True},
        "align_ground": {"enabled": _nested_enabled(alignment_payload, "ground")},
        "evaluate_trajectory": {"enabled": _nested_enabled(benchmark_payload, "trajectory")},
        "reconstruction": {"enabled": _nested_enabled(benchmark_payload, "reference")},
        "evaluate_cloud": {"enabled": _nested_enabled(benchmark_payload, "cloud")},
        "evaluate_efficiency": {"enabled": _nested_enabled(benchmark_payload, "efficiency")},
        "summary": {"enabled": True},
    }


def _nested_enabled(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    return bool(value.get("enabled", False)) if isinstance(value, dict) else False


__all__ = [
    "CURRENT_TO_TARGET_STAGE_KEYS",
    "RunConfig",
    "StageBundle",
    "SECTION_TO_TARGET_STAGE_KEYS",
    "TARGET_TO_CURRENT_STAGE_KEYS",
    "TARGET_STAGE_SECTIONS",
    "TargetStageKey",
    "current_stage_key_for_section",
    "current_stage_key_for_target",
    "section_for_current_stage",
    "section_for_target_stage",
    "target_stage_key_for_current",
    "target_stage_key_for_section",
]
