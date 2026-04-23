"""Target pipeline run configuration and stage-section mapping.

The config objects here validate and describe planning policy only; runtime
construction remains owned by runtime-manager and backend packages.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Self, TypeAlias

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.alignment.contracts import AlignmentConfig
from prml_vslam.benchmark import BenchmarkConfig, ReferenceSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.methods.config_contracts import MethodId, SlamOutputPolicy
from prml_vslam.methods.configs import (
    BackendConfig,
    Mast3rSlamBackendConfig,
    MockSlamBackendConfig,
    VistaSlamBackendConfig,
)
from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.execution import RunRuntimeConfig
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.source.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths
from prml_vslam.visualization.contracts import VisualizationConfig


class TargetStageKey(StrEnum):
    """Name the target public stage-key vocabulary."""

    SOURCE = "source"
    SLAM = "slam"
    ALIGN_GROUND = "gravity.align"
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
    StageKey.GRAVITY_ALIGNMENT: TargetStageKey.ALIGN_GROUND,
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
BackendConfigValue: TypeAlias = Path | str | int | float | bool | None
BackendSpec: TypeAlias = BackendConfig


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
    """Fixed target stage-section bundle for one run config.

    The bundle keeps public TOML shape readable with named sections such as
    ``[stages.source]`` and ``[stages.evaluate_trajectory]`` while preserving
    deterministic linear stage order. During migration each section still maps
    to the current executable :class:`prml_vslam.pipeline.contracts.stages.StageKey`
    so old run inspection and current launch paths remain compatible.
    """

    model_config = ConfigDict(extra="forbid")

    source: SourceStageSectionConfig = Field(default_factory=SourceStageSectionConfig)
    """Source-normalization stage section."""

    slam: SlamStageSectionConfig = Field(default_factory=SlamStageSectionConfig)
    """SLAM stage section."""

    align_ground: StageConfig = Field(
        default_factory=lambda: StageConfig(stage_key=StageKey.GRAVITY_ALIGNMENT, enabled=False)
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
        object.__setattr__(self, "align_ground", _section_config(self.align_ground, StageKey.GRAVITY_ALIGNMENT))
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

    def section(self, section: TargetStageKey | str) -> StageConfig:
        """Return a section config by target stage key or TOML section name."""
        return getattr(self, section_for_target_stage(_target_stage_key_from_section_or_key(section)))


class RunConfig(BaseConfig):
    """Target persisted root config with explicit stage sections.

    ``RunConfig`` is the declarative, TOML-friendly root described by the
    pipeline refactor target. It owns stage policy, visualization policy, and
    run runtime policy, then compiles to a deterministic
    :class:`prml_vslam.pipeline.contracts.plan.RunPlan`. It does not construct
    runtime objects; launch code hands the compiled plan to runtime-manager and
    backend services.
    """

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

    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    """Benchmark policy bundle used by evaluation and reconstruction services."""

    alignment: AlignmentConfig = Field(default_factory=AlignmentConfig)
    """Alignment policy bundle used by the ground-alignment service."""

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


def _compile_run_plan(
    *,
    run_config: RunConfig,
    path_config: PathConfig,
    backend: BackendDescriptor | None = None,
) -> RunPlan:
    source_backend = run_config.stages.source.backend
    if source_backend is None:
        raise ValueError("RunConfig planning requires `[stages.source.backend]`.")
    slam_backend = run_config.stages.slam.backend
    if slam_backend is None:
        raise ValueError("RunConfig planning requires `[stages.slam.backend]`.")
    run_paths = path_config.plan_run_paths(
        experiment_name=run_config.experiment_name,
        method_slug=slam_backend.method_id.value,
        output_dir=run_config.output_dir,
    )
    resolved_run_paths = RunArtifactPaths.build(run_paths.artifact_root)
    slam_available, slam_reason = _slam_stage_availability(
        run_config=run_config, slam_backend=slam_backend, backend=backend
    )
    plan_stages: list[RunPlanStage] = [
        _plan_stage(key=StageKey.INGEST, outputs=_source_outputs(resolved_run_paths)),
        _plan_stage(
            key=StageKey.SLAM,
            outputs=_slam_outputs(
                slam_backend=slam_backend, outputs=run_config.stages.slam.outputs, run_paths=resolved_run_paths
            ),
            available=slam_available,
            availability_reason=slam_reason,
        ),
    ]

    if run_config.stages.align_ground.enabled:
        alignment_available, alignment_reason = _ground_alignment_stage_availability(
            slam_backend=slam_backend,
            outputs=run_config.stages.slam.outputs,
            backend=backend,
        )
        plan_stages.append(
            _plan_stage(
                key=StageKey.GRAVITY_ALIGNMENT,
                outputs=[resolved_run_paths.ground_alignment_path],
                available=alignment_available,
                availability_reason=alignment_reason,
            )
        )
    if run_config.stages.evaluate_trajectory.enabled:
        trajectory_available, trajectory_reason = _trajectory_stage_availability(
            slam_backend=slam_backend,
            backend=backend,
        )
        plan_stages.append(
            _plan_stage(
                key=StageKey.TRAJECTORY_EVALUATION,
                outputs=[resolved_run_paths.trajectory_metrics_path],
                available=trajectory_available,
                availability_reason=trajectory_reason,
            )
        )
    if run_config.stages.reconstruction.enabled:
        reconstruction_available, reconstruction_reason = _reference_reconstruction_stage_availability(
            source_backend=source_backend
        )
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
        source=_planned_source(source_backend),
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
    slam_backend: BackendConfig,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam_backend.display_name if backend is None else backend.display_name
    supports_offline = slam_backend.supports_offline if backend is None else backend.capabilities.offline
    supports_streaming = slam_backend.supports_streaming if backend is None else backend.capabilities.streaming
    if run_config.mode is PipelineMode.OFFLINE and not supports_offline:
        return False, f"{display_name} does not support offline execution."
    if run_config.mode is PipelineMode.STREAMING and not supports_streaming:
        return False, f"{display_name} does not support streaming execution."
    return True, None


def _trajectory_stage_availability(
    *,
    slam_backend: BackendConfig,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam_backend.display_name if backend is None else backend.display_name
    supports_trajectory = (
        slam_backend.supports_trajectory_benchmark
        if backend is None
        else backend.capabilities.trajectory_benchmark_support
    )
    if not supports_trajectory:
        return False, f"{display_name} does not support repository trajectory evaluation."
    return True, None


def _ground_alignment_stage_availability(
    *,
    slam_backend: BackendConfig,
    outputs: SlamOutputPolicy,
    backend: BackendDescriptor | None,
) -> tuple[bool, str | None]:
    display_name = slam_backend.display_name if backend is None else backend.display_name
    supports_dense_points = slam_backend.supports_dense_points if backend is None else backend.capabilities.dense_points
    if not supports_dense_points:
        return False, f"{display_name} does not expose point-cloud outputs for ground alignment."
    if not (outputs.emit_dense_points or outputs.emit_sparse_points):
        return False, "Ground alignment requires sparse or dense point-cloud outputs from the SLAM stage."
    return True, None


def _reference_reconstruction_stage_availability(*, source_backend: SourceBackendConfig) -> tuple[bool, str | None]:
    if not isinstance(source_backend, TumRgbdSourceConfig):
        return False, "Reference reconstruction currently requires a TUM RGB-D dataset source."
    return True, None


def _source_outputs(run_paths: RunArtifactPaths) -> list[Path]:
    return [run_paths.sequence_manifest_path, run_paths.benchmark_inputs_path]


def _planned_source(source_backend: SourceBackendConfig) -> PlannedSource:
    payload = {
        "source_id": source_backend.source_id,
        "frame_stride": source_backend.frame_stride,
        "target_fps": source_backend.target_fps,
    }
    match source_backend:
        case VideoSourceConfig(video_path=video_path):
            payload["video_path"] = video_path
        case AdvioSourceConfig(
            sequence_id=sequence_id,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
        ):
            payload["sequence_id"] = sequence_id
            payload["respect_video_rotation"] = respect_video_rotation
            payload["metadata"] = {
                "dataset_id": DatasetId.ADVIO.value,
                "pose_source": dataset_serving.pose_source.value,
                "pose_frame_mode": dataset_serving.pose_frame_mode.value,
            }
        case TumRgbdSourceConfig(sequence_id=sequence_id):
            payload["sequence_id"] = sequence_id
            payload["metadata"] = {"dataset_id": DatasetId.TUM_RGBD.value}
        case Record3DSourceConfig(transport=transport, device_index=device_index, device_address=device_address):
            payload["transport"] = transport.value
            payload["device_index"] = device_index
            payload["device_address"] = device_address
    return PlannedSource.model_validate(payload)


def _slam_outputs(
    *,
    slam_backend: BackendConfig,
    outputs: SlamOutputPolicy,
    run_paths: RunArtifactPaths,
) -> list[Path]:
    artifact_paths = [run_paths.trajectory_path]
    if slam_backend.method_id is MethodId.VISTA:
        if outputs.emit_sparse_points or outputs.emit_dense_points:
            artifact_paths.append(run_paths.point_cloud_path)
        return artifact_paths
    if outputs.emit_sparse_points:
        artifact_paths.append(run_paths.sparse_points_path)
    if outputs.emit_dense_points:
        artifact_paths.append(run_paths.dense_points_path)
    return artifact_paths


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


def build_run_config(
    *,
    experiment_name: str,
    mode: PipelineMode = PipelineMode.OFFLINE,
    output_dir: Path,
    source_backend: SourceBackendConfig,
    method: MethodId,
    max_frames: int | None = None,
    backend_overrides: dict[str, Any] | None = None,
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
) -> RunConfig:
    """Build one canonical target RunConfig from source, backend, and policy selections."""
    slam_backend = build_backend_spec(method=method, max_frames=max_frames, overrides=backend_overrides)
    return RunConfig(
        experiment_name=experiment_name,
        mode=mode,
        output_dir=output_dir,
        stages=StageBundle(
            source=SourceStageSectionConfig(backend=source_backend),
            slam=SlamStageSectionConfig(
                backend=slam_backend,
                outputs=SlamOutputPolicy(
                    emit_dense_points=emit_dense_points,
                    emit_sparse_points=emit_sparse_points,
                ),
            ),
            align_ground=StageConfig(stage_key=StageKey.GRAVITY_ALIGNMENT, enabled=ground_alignment_enabled),
            evaluate_trajectory=StageConfig(
                stage_key=StageKey.TRAJECTORY_EVALUATION,
                enabled=trajectory_eval_enabled,
            ),
            reconstruction=StageConfig(
                stage_key=StageKey.REFERENCE_RECONSTRUCTION,
                enabled=reference_enabled,
            ),
            evaluate_cloud=StageConfig(
                stage_key=StageKey.CLOUD_EVALUATION,
                enabled=evaluate_cloud,
            ),
            evaluate_efficiency=StageConfig(
                stage_key=StageKey.EFFICIENCY_EVALUATION,
                enabled=evaluate_efficiency,
            ),
            summary=StageConfig(stage_key=StageKey.SUMMARY, enabled=True),
        ),
        benchmark=BenchmarkConfig(
            reference={"enabled": reference_enabled},
            trajectory={
                "enabled": trajectory_eval_enabled,
                "baseline_source": trajectory_baseline,
            },
            cloud={"enabled": evaluate_cloud},
            efficiency={"enabled": evaluate_efficiency},
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
    "BackendSpec",
    "build_backend_spec",
    "build_run_config",
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
