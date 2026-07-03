"""Pipeline run configuration and fixed stage-section bundle."""

from __future__ import annotations

import tomllib
import warnings
from collections.abc import Sequence
from pathlib import Path
from types import UnionType
from typing import Annotated, Any, Literal, Self, TypeAlias, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from prml_vslam.align.gravity.config import GroundAlignmentStageConfig
from prml_vslam.align.icp.config import CloudAlignmentStageConfig
from prml_vslam.align.trajectory_sim3.config import TrajectoryAlignmentStageConfig
from prml_vslam.eval.stage_cloud.config import CloudEvaluationStageConfig
from prml_vslam.eval.stage_image.config import ImageEvaluationStageConfig
from prml_vslam.eval.stage_trajectory.config import (
    TrajectoryEvaluationPolicy,
    TrajectoryEvaluationStageConfig,
)
from prml_vslam.methods.stage.backend_config import (
    BackendConfig,
    BackendConfigValue,
    MethodId,
    SlamOutputPolicy,
    build_slam_backend_config,
)
from prml_vslam.methods.stage.config import SlamStageConfig
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.pipeline.stages.summary.config import SummaryStageConfig
from prml_vslam.reconstruction.config import NksrBackendConfig
from prml_vslam.reconstruction.stage.config import ReconstructionStageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    Record3DSourceConfig,
    SourceBackendConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
    runtime_frame_selection_for_source_config,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudSource,
    ReferenceSource,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import AdvioPoseFrameMode, DatasetId
from prml_vslam.sources.datasets.normalization import (
    dataset_service,
    normalized_runtime_profile_for_dataset,
    normalized_store_for_service,
)
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetEntry, load_timestamps_ns
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths
from prml_vslam.utils.portable_paths import rebase_model_paths
from prml_vslam.visualization.contracts import VisualizationConfig

BackendSpec: TypeAlias = BackendConfig

STAGE_SECTION_ORDER: tuple[tuple[StageKey, str], ...] = (
    (StageKey.SOURCE, "source"),
    (StageKey.SLAM, "slam"),
    (StageKey.GRAVITY_ALIGNMENT, "align_ground"),
    (StageKey.TRAJECTORY_ALIGNMENT, "align_trajectory"),
    (StageKey.TRAJECTORY_EVALUATION, "evaluate_trajectory"),
    (StageKey.CLOUD_ALIGNMENT, "align_cloud"),
    (StageKey.RECONSTRUCTION, "reconstruction"),
    (StageKey.CLOUD_EVALUATION, "evaluate_cloud"),
    (StageKey.IMAGE_EVALUATION, "evaluate_image"),
    (StageKey.SUMMARY, "summary"),
)


class StageBundle(BaseConfig):
    """Fixed persisted stage-section bundle using snake_case TOML sections."""

    model_config = ConfigDict(extra="ignore")

    source: SourceStageConfig = Field(default_factory=SourceStageConfig)
    """Source-normalization stage section."""

    slam: SlamStageConfig = Field(default_factory=SlamStageConfig)
    """SLAM stage section."""

    align_ground: GroundAlignmentStageConfig = Field(default_factory=lambda: GroundAlignmentStageConfig(enabled=False))
    """Ground-alignment stage section."""

    align_trajectory: TrajectoryAlignmentStageConfig = Field(
        default_factory=lambda: TrajectoryAlignmentStageConfig(enabled=False)
    )
    """Trajectory Sim(3)-alignment stage section."""

    evaluate_trajectory: TrajectoryEvaluationStageConfig = Field(
        default_factory=lambda: TrajectoryEvaluationStageConfig(enabled=False)
    )
    """Trajectory-evaluation stage section."""

    reconstruction: ReconstructionStageConfig = Field(default_factory=lambda: ReconstructionStageConfig(enabled=False))
    """Reconstruction stage section."""

    align_cloud: CloudAlignmentStageConfig = Field(default_factory=lambda: CloudAlignmentStageConfig(enabled=False))
    """Offline dense-cloud alignment section."""

    evaluate_cloud: CloudEvaluationStageConfig = Field(
        default_factory=lambda: CloudEvaluationStageConfig(enabled=False)
    )
    """Dense-cloud evaluation stage section."""

    evaluate_image: ImageEvaluationStageConfig = Field(
        default_factory=lambda: ImageEvaluationStageConfig(enabled=False)
    )
    """Rendered-image evaluation stage section."""

    summary: SummaryStageConfig = Field(default_factory=SummaryStageConfig)
    """Summary-projection stage section."""

    @model_validator(mode="after")
    def validate_stage_keys(self) -> Self:
        """Ensure every section carries its canonical target stage key."""
        for stage_key, section_name in STAGE_SECTION_ORDER:
            section = getattr(self, section_name)
            if section.stage_key is not None and section.stage_key != stage_key:
                raise ValueError(f"Expected `{section_name}` to use stage key `{stage_key.value}`.")
            object.__setattr__(self, section_name, section.model_copy(update={"stage_key": stage_key}))
        return self

    def section(self, section: StageKey | str) -> StageConfig:
        """Return a section config by canonical stage key or TOML section name."""
        if isinstance(section, StageKey):
            for stage_key, section_name in STAGE_SECTION_ORDER:
                if stage_key is section:
                    return getattr(self, section_name)
            raise KeyError(section.value)
        return getattr(self, section)

    def ordered_sections(self) -> list[StageConfig]:
        """Return stage sections in canonical execution order."""
        return [getattr(self, section_name) for _, section_name in STAGE_SECTION_ORDER]


class RunConfig(BaseConfig):
    """Persisted declarative root config for one pipeline run."""

    model_config = ConfigDict(extra="ignore")

    experiment_name: str
    """Human-readable benchmark run name."""

    mode: PipelineMode = PipelineMode.OFFLINE
    """Offline or streaming execution mode."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    reuse_artifact_root: Path | None = None
    """Existing method-level artifact root used to satisfy disabled source/SLAM stages."""

    stages: StageBundle = Field(default_factory=StageBundle)
    """Fixed stage-section bundle."""

    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    """Viewer/export policy kept outside stage runtime semantics."""

    ray_local_head_lifecycle: Literal["ephemeral", "reusable"] = "ephemeral"
    """Whether an auto-started local Ray head is torn down or preserved after a run."""

    ray_log_to_driver: bool = True
    """Whether Ray worker logs are forwarded to the driver process."""

    _config_warnings: list[str] = PrivateAttr(default_factory=list)

    @classmethod
    def from_toml(cls, source: str | Path | bytes) -> Self:
        """Load one run config and record lenient unknown-field diagnostics."""
        data = _load_toml_payload(source)
        config_warnings = _collect_unknown_field_warnings(cls, data, path=())
        for message in config_warnings:
            warnings.warn(message, UserWarning, stacklevel=2)
        config = cls.model_validate(data)
        config._config_warnings = config_warnings
        return config

    @property
    def config_warnings(self) -> list[str]:
        """Return lenient config warnings captured during TOML load."""
        return list(self._config_warnings)

    @model_validator(mode="after")
    def apply_dataset_default_baselines(self) -> Self:
        """Fill omitted trajectory baselines from the selected source backend."""
        source_backend = self.stages.source.backend
        if source_backend is None:
            return self

        baseline = default_trajectory_baseline_for_source(source_backend)
        if "baseline_source" not in self.stages.align_trajectory.model_fields_set:
            self.stages.align_trajectory.baseline_source = baseline
        if "baseline_source" not in self.stages.evaluate_trajectory.evaluation.model_fields_set:
            self.stages.evaluate_trajectory.evaluation.baseline_source = baseline
        return self

    def compile_plan(
        self,
        path_config: PathConfig | None = None,
        *,
        fail_on_unavailable: bool = False,
        backend: BackendConfig | None = None,
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
    backend: BackendConfig | None = None,
) -> RunPlan:
    source_backend = run_config.stages.source.backend
    if source_backend is None and (run_config.stages.source.enabled or run_config.reuse_artifact_root is None):
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
    reuse_paths: RunArtifactPaths | None = None
    if run_config.reuse_artifact_root is not None:
        reuse_root = run_config.reuse_artifact_root.expanduser().resolve()
        if reuse_root == resolved_run_paths.artifact_root.resolve():
            raise ValueError("`reuse_artifact_root` must not equal the new run artifact root.")
        if not reuse_root.exists():
            raise ValueError(f"`reuse_artifact_root` does not exist: {reuse_root}")
        reuse_paths = RunArtifactPaths.build(reuse_root)
        for label, path in (
            ("source manifest", reuse_paths.sequence_manifest_path),
            ("benchmark inputs", reuse_paths.benchmark_inputs_path),
            ("SLAM trajectory", reuse_paths.trajectory_path),
        ):
            if not path.exists():
                raise ValueError(f"`reuse_artifact_root` is missing {label}: {path}")
    plan_context = PipelinePlanContext(
        run_config=run_config,
        path_config=path_config,
        run_paths=resolved_run_paths,
        slam_backend=backend if backend is not None else slam_backend,
    )
    plan_stages: list[RunPlanStage] = []
    for stage_config in run_config.stages.ordered_sections():
        if not stage_config.enabled:
            continue
        if stage_config.stage_key is None:
            raise ValueError("Stage section is missing its canonical stage key.")
        availability = stage_config.availability(plan_context)
        plan_stages.append(
            RunPlanStage(
                key=stage_config.stage_key,
                outputs=stage_config.planned_outputs(plan_context),
                available=availability[0],
                availability_reason=availability[1],
            )
        )

    return RunPlan(
        run_id=path_config.slugify_experiment_name(run_config.experiment_name),
        mode=run_config.mode,
        artifact_root=run_paths.artifact_root,
        source=(
            _planned_source(source_backend, path_config=path_config)
            if source_backend is not None
            else _planned_reused_source(reuse_paths)
        ),
        stages=plan_stages,
        config_warnings=run_config.config_warnings,
    )


def _planned_source(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> PlannedSource:
    payload: dict[str, Any] = {
        "source_id": source_backend.source_id,
        "frame_stride": source_backend.frame_stride,
        "target_fps": source_backend.target_fps,
        "expected_fps": _expected_source_fps(source_backend, path_config=path_config),
    }
    match source_backend:
        case VideoSourceConfig(video_path=video_path):
            payload["video_path"] = video_path
        case AdvioSourceConfig(
            sequence_id=sequence_id,
            dataset_serving=dataset_serving,
            replay_mode=replay_mode,
        ):
            payload["sequence_id"] = sequence_id
            payload["replay_mode"] = replay_mode.value
            payload["metadata"] = {
                "dataset_id": DatasetId.ADVIO.value,
                "pose_source": dataset_serving.pose_source.value,
                "pose_frame_mode": AdvioPoseFrameMode.FIXEDPOINT_COMMON_START_LOCAL.value,
            }
        case TumRgbdSourceConfig(sequence_id=sequence_id, replay_mode=replay_mode, reference_cloud=reference_cloud):
            payload["sequence_id"] = sequence_id
            payload["replay_mode"] = replay_mode.value
            payload["metadata"] = {
                "dataset_id": DatasetId.TUM_RGBD.value,
                "reference_cloud_source": ReferenceCloudSource.TUM_RGBD.value,
                "reference_cloud_depth_stride_px": reference_cloud.depth_stride_px,
                "reference_cloud_max_points": reference_cloud.max_points,
                "reference_cloud_random_seed": reference_cloud.random_seed,
                "reference_cloud_min_confidence": reference_cloud.min_confidence,
            }
        case Record3DDatasetSourceConfig(
            sequence_id=sequence_id,
            replay_mode=replay_mode,
            materialization=materialization,
            reference_cloud=reference_cloud,
        ):
            payload["sequence_id"] = sequence_id
            payload["replay_mode"] = replay_mode.value
            payload["metadata"] = {
                "dataset_id": DatasetId.RECORD3D.value,
                "pose_source": ReferenceSource.ARKIT.value,
                "pose_frame_mode": materialization.pose_frame_mode.value,
                "reference_cloud_source": ReferenceCloudSource.RECORD3D_LIDAR.value,
                "reference_cloud_depth_stride_px": reference_cloud.depth_stride_px,
                "reference_cloud_max_points": reference_cloud.max_points,
                "reference_cloud_random_seed": reference_cloud.random_seed,
                "reference_cloud_min_confidence": reference_cloud.min_confidence,
            }
        case Record3DSourceConfig(transport=transport, device_index=device_index, device_address=device_address):
            payload["transport"] = transport.value
            payload["device_index"] = device_index
            payload["device_address"] = device_address
    return PlannedSource.model_validate(payload)


def _planned_reused_source(run_paths: RunArtifactPaths | None) -> PlannedSource:
    if run_paths is None:
        raise ValueError("RunConfig planning requires `reuse_artifact_root` when `[stages.source.backend]` is absent.")
    manifest = SequenceManifest.model_validate_json(run_paths.sequence_manifest_path.read_text(encoding="utf-8"))
    return PlannedSource(
        source_id="reused_artifacts",
        sequence_id=manifest.sequence_id,
        metadata={
            "reuse_artifact_root": run_paths.artifact_root.as_posix(),
            "dataset_id": manifest.dataset_id.value if manifest.dataset_id is not None else None,
        },
    )


def _expected_source_fps(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> float | None:
    if isinstance(source_backend, AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig):
        return _normalized_source_fps(source_backend, path_config=path_config)
    if source_backend.target_fps is not None:
        return float(source_backend.target_fps)
    native_fps = _source_fps(source_backend, path_config=path_config)
    if native_fps is None:
        return None
    return native_fps / source_backend.frame_stride


def _source_fps(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> float | None:
    try:
        match source_backend:
            case VideoSourceConfig(video_path=video_path):
                return _video_native_fps(video_path=video_path, path_config=path_config)
            case AdvioSourceConfig() | TumRgbdSourceConfig() | Record3DDatasetSourceConfig():
                return _normalized_source_fps(source_backend, path_config=path_config)
            case Record3DSourceConfig():
                return None
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None


def _normalized_source_fps(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> float | None:
    try:
        match source_backend:
            case AdvioSourceConfig() as source:
                dataset_id = DatasetId.ADVIO
            case TumRgbdSourceConfig() as source:
                dataset_id = DatasetId.TUM_RGBD
            case Record3DDatasetSourceConfig() as source:
                dataset_id = DatasetId.RECORD3D
            case _:
                return None
        service = dataset_service(dataset_id, path_config)
        frame_selection = runtime_frame_selection_for_source_config(source)
        profile = normalized_runtime_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source)
        entry = normalized_store_for_service(dataset_id, path_config).select_entry_for_runtime(
            profile,
            frame_selection=frame_selection,
        )
        manifest = rebase_model_paths(
            SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8")),
            root=entry.root,
        )
        timestamps_ns = _normalized_entry_timestamps_ns(entry, manifest)
        if not timestamps_ns:
            return None
        stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
        return _fps_for_timestamps_ns(timestamps_ns[::stride])
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None


def _video_native_fps(*, video_path: Path, path_config: PathConfig) -> float | None:
    import cv2

    resolved_video_path = path_config.resolve_video_path(video_path)
    if not resolved_video_path.exists():
        return None
    capture = cv2.VideoCapture(str(resolved_video_path))
    try:
        if not capture.isOpened():
            return None
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        return fps if fps > 0.0 else None
    finally:
        capture.release()


def _normalized_entry_timestamps_ns(entry: NormalizedDatasetEntry, manifest: SequenceManifest) -> list[int]:
    benchmark_inputs = rebase_model_paths(
        PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
        root=entry.root,
    )
    observation_sequence = benchmark_inputs.default_observation_sequence()
    if observation_sequence is not None:
        return [row.timestamp_ns for row in load_observation_sequence_index(observation_sequence.index_path).rows]
    if manifest.timestamps_path is None:
        return []
    return load_timestamps_ns(manifest.timestamps_path)


def _fps_for_timestamps_ns(timestamps_ns: Sequence[int]) -> float | None:
    if len(timestamps_ns) < 2:
        return None
    return _fps_for_duration(
        sample_count=len(timestamps_ns),
        duration_s=(int(timestamps_ns[-1]) - int(timestamps_ns[0])) / 1e9,
    )


def _fps_for_duration(*, sample_count: int, duration_s: float) -> float | None:
    return None if duration_s <= 0.0 else (sample_count - 1) / duration_s


def default_trajectory_baseline_for_source(source_backend: SourceBackendConfig) -> ReferenceSource:
    """Return the dataset-owned reference trajectory default for one source."""
    match source_backend:
        case Record3DDatasetSourceConfig():
            return ReferenceSource.ARKIT
        case _:
            return ReferenceSource.GROUND_TRUTH


def build_run_config(
    *,
    experiment_name: str,
    mode: PipelineMode = PipelineMode.OFFLINE,
    output_dir: Path,
    source_backend: SourceBackendConfig,
    method: MethodId,
    max_frames: int | None = None,
    backend_overrides: dict[str, BackendConfigValue] | None = None,
    emit_dense_points: bool = True,
    emit_sparse_points: bool | None = None,
    reference_enabled: bool = False,
    trajectory_eval_enabled: bool = False,
    trajectory_alignment_enabled: bool = False,
    cloud_alignment_enabled: bool = False,
    trajectory_baseline: ReferenceSource | None = None,
    evaluate_cloud: bool = False,
    evaluate_image: bool = False,
    ground_alignment_enabled: bool = False,
    connect_live_viewer: bool = False,
    export_viewer_rrd: bool = False,
    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy",
    viewer_blueprint_path: Path | None = None,
    preserve_native_rerun: bool = True,
    frusta_history_window_offline: int | None = None,
    show_tracking_trajectory: bool = True,
    trajectory_pose_axis_length: float = 0.0,
    log_source_rgb: bool = False,
    log_diagnostic_preview: bool = False,
    log_camera_image_rgb: bool = True,
    point_cloud_decimation_keep_ratio: float = 1.0,
    reference_point_cloud_decimation_keep_ratio: float = 1.0,
    mesh_decimation_keep_ratio: float = 1.0,
    decimation_random_seed: int = 0,
    ray_log_to_driver: bool = True,
) -> RunConfig:
    """Build one canonical target ``RunConfig`` from common selections."""
    slam_backend = build_slam_backend_config(method=method, max_frames=max_frames, overrides=backend_overrides)
    resolved_trajectory_baseline = (
        default_trajectory_baseline_for_source(source_backend) if trajectory_baseline is None else trajectory_baseline
    )
    trajectory_policy = TrajectoryEvaluationPolicy(baseline_source=resolved_trajectory_baseline)
    dense_only_methods = {MethodId.MAST3R, MethodId.LINGBOT_MAP}
    resolved_emit_sparse_points = method not in dense_only_methods if emit_sparse_points is None else emit_sparse_points
    return RunConfig(
        experiment_name=experiment_name,
        mode=mode,
        output_dir=output_dir,
        stages=StageBundle(
            source=SourceStageConfig(backend=source_backend),
            slam=SlamStageConfig(
                backend=slam_backend,
                outputs=SlamOutputPolicy(
                    emit_dense_points=emit_dense_points,
                    emit_sparse_points=resolved_emit_sparse_points,
                ),
            ),
            align_ground=GroundAlignmentStageConfig(enabled=ground_alignment_enabled),
            align_trajectory=TrajectoryAlignmentStageConfig(
                enabled=trajectory_alignment_enabled,
                baseline_source=resolved_trajectory_baseline,
            ),
            evaluate_trajectory=TrajectoryEvaluationStageConfig(
                enabled=trajectory_eval_enabled,
                evaluation=trajectory_policy,
            ),
            reconstruction=ReconstructionStageConfig(
                enabled=reference_enabled,
                backend=NksrBackendConfig(),
            ),
            align_cloud=CloudAlignmentStageConfig(enabled=cloud_alignment_enabled),
            evaluate_cloud=CloudEvaluationStageConfig(enabled=evaluate_cloud),
            evaluate_image=ImageEvaluationStageConfig(enabled=evaluate_image),
            summary=SummaryStageConfig(enabled=True),
        ),
        visualization=VisualizationConfig(
            connect_live_viewer=connect_live_viewer,
            export_viewer_rrd=export_viewer_rrd,
            grpc_url=grpc_url,
            viewer_blueprint_path=viewer_blueprint_path,
            preserve_native_rerun=preserve_native_rerun,
            frusta_history_window_offline=frusta_history_window_offline,
            show_tracking_trajectory=show_tracking_trajectory,
            trajectory_pose_axis_length=trajectory_pose_axis_length,
            log_source_rgb=log_source_rgb,
            log_diagnostic_preview=log_diagnostic_preview,
            log_camera_image_rgb=log_camera_image_rgb,
            point_cloud_decimation_keep_ratio=point_cloud_decimation_keep_ratio,
            reference_point_cloud_decimation_keep_ratio=reference_point_cloud_decimation_keep_ratio,
            mesh_decimation_keep_ratio=mesh_decimation_keep_ratio,
            decimation_random_seed=decimation_random_seed,
        ),
        ray_log_to_driver=ray_log_to_driver,
    )


def build_backend_spec(
    *,
    method: MethodId,
    max_frames: int | None = None,
    overrides: dict[str, BackendConfigValue] | None = None,
) -> BackendSpec:
    """Build a typed SLAM backend config for callers that still need this helper."""
    return build_slam_backend_config(method=method, max_frames=max_frames, overrides=overrides)


def _load_toml_payload(source: str | Path | bytes) -> dict[str, Any]:
    if isinstance(source, Path):
        return tomllib.loads(source.read_text(encoding="utf-8"))
    if isinstance(source, bytes):
        return tomllib.loads(source.decode("utf-8"))
    if "\n" in source or "\r" in source:
        return tomllib.loads(source)
    candidate = Path(source)
    if candidate.exists():
        return tomllib.loads(candidate.read_text(encoding="utf-8"))
    return tomllib.loads(source)


def _collect_unknown_field_warnings(model_type: type[BaseModel], data: Any, *, path: tuple[str, ...]) -> list[str]:
    if not isinstance(data, dict):
        return []
    warnings_out: list[str] = []
    fields = model_type.model_fields
    for key in data:
        if key not in fields:
            location = ".".join((*path, key))
            warnings_out.append(f"Ignoring unknown config field `{location}`.")
    for key, value in data.items():
        field = fields.get(key)
        if field is None:
            continue
        nested_model = _model_type_for_value(field.annotation, value)
        if nested_model is not None:
            warnings_out.extend(_collect_unknown_field_warnings(nested_model, value, path=(*path, key)))
    return warnings_out


def _model_type_for_value(annotation: Any, value: Any) -> type[BaseModel] | None:
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Annotated and args:
        return _model_type_for_value(args[0], value)
    if origin in {list, tuple}:
        return None
    if origin in {Union, UnionType} and args:
        for candidate in args:
            nested = _model_type_for_value(candidate, value)
            if nested is not None and _discriminator_matches(nested, value):
                return nested
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _discriminator_matches(model_type: type[BaseModel], value: Any) -> bool:
    if not isinstance(value, dict):
        return True
    for discriminator in ("source_id", "method_id"):
        if discriminator not in value or discriminator not in model_type.model_fields:
            continue
        default = model_type.model_fields[discriminator].default
        return str(value[discriminator]) == str(default.value if hasattr(default, "value") else default)
    return True


__all__ = [
    "BackendSpec",
    "RunConfig",
    "StageBundle",
    "build_backend_spec",
    "build_run_config",
    "default_trajectory_baseline_for_source",
]
