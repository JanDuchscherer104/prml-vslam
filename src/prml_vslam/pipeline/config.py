"""Pipeline run configuration and fixed stage-section bundle."""

from __future__ import annotations

import tomllib
import warnings
from collections.abc import Sequence
from pathlib import Path
from types import UnionType
from typing import Annotated, Any, Literal, Self, TypeAlias, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from prml_vslam.alignment.stage.config import GroundAlignmentStageConfig
from prml_vslam.datasets.advio.advio_layout import resolve_existing_sequence_dir as resolve_existing_advio_sequence_dir
from prml_vslam.datasets.advio.advio_loading import load_advio_frame_timestamps_ns
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.datasets.tum_rgbd.tum_rgbd_layout import (
    resolve_existing_sequence_dir as resolve_existing_tum_rgbd_sequence_dir,
)
from prml_vslam.datasets.tum_rgbd.tum_rgbd_loading import load_tum_rgbd_list
from prml_vslam.eval.stage_cloud.config import CloudEvaluationStageConfig
from prml_vslam.eval.stage_trajectory.config import (
    TrajectoryEvaluationPolicy,
    TrajectoryEvaluationStageConfig,
)
from prml_vslam.methods.stage.config import (
    BackendConfig,
    BackendConfigValue,
    MethodId,
    SlamOutputPolicy,
    SlamStageConfig,
    build_slam_backend_config,
)
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.plan import PlannedSource, RunPlan, RunPlanStage
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig, StagePlanContext
from prml_vslam.pipeline.stages.summary.config import SummaryStageConfig
from prml_vslam.reconstruction.config import Open3dTsdfBackendConfig
from prml_vslam.reconstruction.stage.config import ReconstructionStageConfig
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    SourceBackendConfig,
    SourceStageConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths
from prml_vslam.visualization.contracts import VisualizationConfig

BackendSpec: TypeAlias = BackendConfig

STAGE_SECTION_ORDER: tuple[tuple[StageKey, str], ...] = (
    (StageKey.SOURCE, "source"),
    (StageKey.SLAM, "slam"),
    (StageKey.GRAVITY_ALIGNMENT, "align_ground"),
    (StageKey.TRAJECTORY_EVALUATION, "evaluate_trajectory"),
    (StageKey.RECONSTRUCTION, "reconstruction"),
    (StageKey.CLOUD_EVALUATION, "evaluate_cloud"),
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

    evaluate_trajectory: TrajectoryEvaluationStageConfig = Field(
        default_factory=lambda: TrajectoryEvaluationStageConfig(enabled=False)
    )
    """Trajectory-evaluation stage section."""

    reconstruction: ReconstructionStageConfig = Field(default_factory=lambda: ReconstructionStageConfig(enabled=False))
    """Reconstruction stage section."""

    evaluate_cloud: CloudEvaluationStageConfig = Field(
        default_factory=lambda: CloudEvaluationStageConfig(enabled=False)
    )
    """Dense-cloud diagnostic stage section."""

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

    stages: StageBundle = Field(default_factory=StageBundle)
    """Fixed stage-section bundle."""

    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    """Viewer/export policy kept outside stage runtime semantics."""

    ray_local_head_lifecycle: Literal["ephemeral", "reusable"] = "ephemeral"
    """Whether an auto-started local Ray head is torn down or preserved after a run."""

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

    def compile_plan(
        self,
        path_config: PathConfig | None = None,
        *,
        fail_on_unavailable: bool = False,
        backend: BackendConfigValue | None = None,
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
    backend: BackendConfigValue | None = None,
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
    plan_context = StagePlanContext(
        run_config=run_config,
        path_config=path_config,
        run_paths=resolved_run_paths,
        backend=backend if backend is not None else slam_backend,
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
        source=_planned_source(source_backend, path_config=path_config),
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


def _expected_source_fps(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> float | None:
    if source_backend.target_fps is not None:
        return float(source_backend.target_fps)
    native_fps = _native_source_fps(source_backend, path_config=path_config)
    if native_fps is None:
        return None
    return native_fps / source_backend.frame_stride


def _native_source_fps(source_backend: SourceBackendConfig, *, path_config: PathConfig) -> float | None:
    try:
        match source_backend:
            case VideoSourceConfig(video_path=video_path):
                return _video_native_fps(video_path=video_path, path_config=path_config)
            case AdvioSourceConfig(sequence_id=sequence_id):
                return _advio_native_fps(sequence_id=sequence_id, path_config=path_config)
            case TumRgbdSourceConfig(sequence_id=sequence_id):
                return _tum_rgbd_native_fps(sequence_id=sequence_id, path_config=path_config)
            case Record3DSourceConfig():
                return None
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


def _advio_native_fps(*, sequence_id: str, path_config: PathConfig) -> float | None:
    dataset_dir = path_config.resolve_dataset_dir(DatasetId.ADVIO.value)
    sequence_dir = resolve_existing_advio_sequence_dir(dataset_dir, sequence_id)
    if sequence_dir is None:
        return None
    timestamps_ns = load_advio_frame_timestamps_ns(sequence_dir / "iphone" / "frames.csv")
    return _fps_for_timestamps_ns(timestamps_ns)


def _tum_rgbd_native_fps(*, sequence_id: str, path_config: PathConfig) -> float | None:
    dataset_dir = path_config.resolve_dataset_dir(DatasetId.TUM_RGBD.value)
    sequence_dir = resolve_existing_tum_rgbd_sequence_dir(dataset_dir, sequence_id)
    if sequence_dir is None:
        return None
    timestamps_s = [timestamp_s for timestamp_s, _path in load_tum_rgbd_list(sequence_dir / "rgb.txt")]
    return _fps_for_timestamps_s(timestamps_s)


def _fps_for_timestamps_ns(timestamps_ns: Sequence[int]) -> float | None:
    if len(timestamps_ns) < 2:
        return None
    return _fps_for_duration(
        sample_count=len(timestamps_ns),
        duration_s=(int(timestamps_ns[-1]) - int(timestamps_ns[0])) / 1e9,
    )


def _fps_for_timestamps_s(timestamps_s: Sequence[float]) -> float | None:
    if len(timestamps_s) < 2:
        return None
    return _fps_for_duration(
        sample_count=len(timestamps_s),
        duration_s=float(timestamps_s[-1]) - float(timestamps_s[0]),
    )


def _fps_for_duration(*, sample_count: int, duration_s: float) -> float | None:
    return None if duration_s <= 0.0 else (sample_count - 1) / duration_s


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
    emit_sparse_points: bool = True,
    reference_enabled: bool = False,
    trajectory_eval_enabled: bool = False,
    trajectory_baseline: ReferenceSource = ReferenceSource.GROUND_TRUTH,
    evaluate_cloud: bool = False,
    ground_alignment_enabled: bool = False,
    connect_live_viewer: bool = False,
    export_viewer_rrd: bool = False,
    grpc_url: str = "rerun+http://127.0.0.1:9876/proxy",
    viewer_blueprint_path: Path | None = None,
    preserve_native_rerun: bool = True,
    frusta_history_window_streaming: int = 20,
    frusta_history_window_offline: int | None = None,
    show_tracking_trajectory: bool = True,
    log_source_rgb: bool = False,
    log_diagnostic_preview: bool = False,
    log_camera_image_rgb: bool = False,
) -> RunConfig:
    """Build one canonical target ``RunConfig`` from common selections."""
    slam_backend = build_slam_backend_config(method=method, max_frames=max_frames, overrides=backend_overrides)
    trajectory_policy = TrajectoryEvaluationPolicy(baseline_source=trajectory_baseline)
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
                    emit_sparse_points=emit_sparse_points,
                ),
            ),
            align_ground=GroundAlignmentStageConfig(enabled=ground_alignment_enabled),
            evaluate_trajectory=TrajectoryEvaluationStageConfig(
                enabled=trajectory_eval_enabled,
                evaluation=trajectory_policy,
            ),
            reconstruction=ReconstructionStageConfig(
                enabled=reference_enabled,
                backend=Open3dTsdfBackendConfig(),
            ),
            evaluate_cloud=CloudEvaluationStageConfig(enabled=evaluate_cloud),
            summary=SummaryStageConfig(enabled=True),
        ),
        visualization=VisualizationConfig(
            connect_live_viewer=connect_live_viewer,
            export_viewer_rrd=export_viewer_rrd,
            grpc_url=grpc_url,
            viewer_blueprint_path=viewer_blueprint_path,
            preserve_native_rerun=preserve_native_rerun,
            frusta_history_window_streaming=frusta_history_window_streaming,
            frusta_history_window_offline=frusta_history_window_offline,
            show_tracking_trajectory=show_tracking_trajectory,
            log_source_rgb=log_source_rgb,
            log_diagnostic_preview=log_diagnostic_preview,
            log_camera_image_rgb=log_camera_image_rgb,
        ),
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
]
