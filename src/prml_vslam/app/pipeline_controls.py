"""Request-editing and run-launch helpers for the Pipeline page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

from prml_vslam.datasets.advio import AdvioLocalSceneStatus, AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods.stage.config import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import BackendSpec, RunConfig, build_run_config
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.demo import build_runtime_source_from_run_config, load_run_config_toml
from prml_vslam.sources.config import AdvioSourceConfig, Record3DSourceConfig
from prml_vslam.utils import BaseData, PathConfig

from .models import PipelinePageState, PipelineSourceId
from .record3d_controls import record3d_transport_input_error
from .state import save_model_updates

if TYPE_CHECKING:
    from .bootstrap import AppContext


_SUPPORTED_APP_STAGE_IDS = frozenset(
    {
        StageKey.SOURCE,
        StageKey.SLAM,
        StageKey.GRAVITY_ALIGNMENT,
        StageKey.TRAJECTORY_EVALUATION,
        StageKey.RECONSTRUCTION,
        StageKey.SUMMARY,
    }
)

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]

PipelinePageStateUpdateValue: TypeAlias = (
    PipelineSourceId
    | AdvioPoseSource
    | AdvioPoseFrameMode
    | Record3DTransportId
    | PipelineMode
    | MethodId
    | BackendSpec
    | Path
    | int
    | float
    | str
    | bool
    | None
)
PipelinePageStateUpdates: TypeAlias = dict[str, PipelinePageStateUpdateValue]


class PipelinePageAction(PipelinePageState):
    """Typed action payload for the pipeline page controls."""

    start_requested: bool = False
    """Whether the user requested a new run."""

    stop_requested: bool = False
    """Whether the user requested the current run to stop."""


def action_from_page_state(page_state: PipelinePageState, config_path: Path) -> PipelinePageAction:
    """Build the current action payload from persisted page state."""
    return PipelinePageAction.model_validate(page_state.model_dump(mode="python") | {"config_path": config_path})


def sync_pipeline_page_state_from_template(
    *,
    context: AppContext,
    config_path: Path,
    run_config: RunConfig,
    statuses: list[AdvioLocalSceneStatus],
) -> None:
    """Hydrate Pipeline page state from a newly selected request template."""
    page_state = context.state.pipeline
    if page_state.config_path == config_path:
        return
    source_updates: PipelinePageStateUpdates = {
        "source_kind": page_state.source_kind,
        "advio_sequence_id": page_state.advio_sequence_id,
    }
    source_backend = run_config.stages.source.backend
    match source_backend:
        case AdvioSourceConfig(sequence_id=sequence_slug):
            advio_sequence_id, _ = resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=statuses)
            source_updates = {
                "source_kind": PipelineSourceId.ADVIO,
                "advio_sequence_id": advio_sequence_id,
                "dataset_frame_stride": source_backend.frame_stride,
                "dataset_target_fps": source_backend.target_fps,
                "pose_source": source_backend.dataset_serving.pose_source,
                "pose_frame_mode": source_backend.dataset_serving.pose_frame_mode,
                "respect_video_rotation": source_backend.respect_video_rotation,
            }
        case Record3DSourceConfig() as record3d_source:
            source_updates = {
                "source_kind": PipelineSourceId.RECORD3D,
                "record3d_transport": Record3DTransportId(record3d_source.transport.value),
                "record3d_usb_device_index": record3d_source.device_index,
                "record3d_wifi_device_address": record3d_source.device_address,
                "record3d_frame_timeout_seconds": record3d_source.frame_timeout_seconds,
            }
        case _:
            source_updates = {"source_kind": page_state.source_kind, "advio_sequence_id": page_state.advio_sequence_id}
    save_model_updates(
        context.store,
        context.state,
        page_state,
        config_path=config_path,
        experiment_name=run_config.experiment_name,
        mode=run_config.mode,
        method=run_config.stages.slam.backend.method_id,
        slam_max_frames=run_config.stages.slam.backend.max_frames,
        slam_backend_spec=run_config.stages.slam.backend.model_copy(deep=True),
        emit_dense_points=run_config.stages.slam.outputs.emit_dense_points,
        emit_sparse_points=run_config.stages.slam.outputs.emit_sparse_points,
        ground_alignment_enabled=run_config.stages.align_ground.enabled,
        reconstruction_enabled=run_config.stages.reconstruction.enabled,
        trajectory_eval_enabled=run_config.stages.evaluate_trajectory.enabled,
        evaluate_cloud=run_config.stages.evaluate_cloud.enabled,
        connect_live_viewer=run_config.visualization.connect_live_viewer,
        export_viewer_rrd=run_config.visualization.export_viewer_rrd,
        grpc_url=run_config.visualization.grpc_url,
        viewer_blueprint_path=run_config.visualization.viewer_blueprint_path,
        preserve_native_rerun=run_config.visualization.preserve_native_rerun,
        frusta_history_window_streaming=run_config.visualization.frusta_history_window_streaming,
        frusta_history_window_offline=run_config.visualization.frusta_history_window_offline,
        show_tracking_trajectory=run_config.visualization.show_tracking_trajectory,
        log_source_rgb=run_config.visualization.log_source_rgb,
        log_diagnostic_preview=run_config.visualization.log_diagnostic_preview,
        log_camera_image_rgb=run_config.visualization.log_camera_image_rgb,
        **source_updates,
    )


def build_run_config_from_action(
    context: AppContext, action: PipelinePageAction
) -> tuple[RunConfig | None, str | None]:
    """Build a typed pipeline run config from one rendered Pipeline page action."""
    try:
        if action.source_kind is PipelineSourceId.ADVIO:
            if action.advio_sequence_id is None:
                raise ValueError("Select a replay-ready ADVIO scene.")
            source_backend = AdvioSourceConfig(
                sequence_id=context.advio_service.scene(action.advio_sequence_id).sequence_slug,
                frame_stride=action.dataset_frame_stride,
                target_fps=action.dataset_target_fps,
                dataset_serving=AdvioServingConfig(
                    pose_source=action.pose_source,
                    pose_frame_mode=action.pose_frame_mode,
                ),
                respect_video_rotation=action.respect_video_rotation,
            )
        else:
            source_backend = record3d_source_config_from_action(action)
        run_config = build_run_config(
            experiment_name=action.experiment_name.strip() or "pipeline-demo",
            mode=action.mode,
            output_dir=context.path_config.artifacts_dir,
            source_backend=source_backend,
            method=action.method,
            max_frames=action.slam_max_frames,
            backend_overrides=backend_payload_from_action(action),
            emit_dense_points=action.emit_dense_points,
            emit_sparse_points=action.emit_sparse_points,
            reference_enabled=action.reconstruction_enabled,
            trajectory_eval_enabled=action.trajectory_eval_enabled,
            evaluate_cloud=action.evaluate_cloud,
            ground_alignment_enabled=action.ground_alignment_enabled,
            connect_live_viewer=action.connect_live_viewer,
            export_viewer_rrd=action.export_viewer_rrd,
            grpc_url=action.grpc_url,
            viewer_blueprint_path=action.viewer_blueprint_path,
            preserve_native_rerun=action.preserve_native_rerun,
            frusta_history_window_streaming=action.frusta_history_window_streaming,
            frusta_history_window_offline=action.frusta_history_window_offline,
            show_tracking_trajectory=action.show_tracking_trajectory,
            log_source_rgb=action.log_source_rgb,
            log_diagnostic_preview=action.log_diagnostic_preview,
            log_camera_image_rgb=action.log_camera_image_rgb,
        )
        return run_config, None
    except Exception as exc:
        return None, str(exc)


def build_preview_plan(run_config: RunConfig, path_config: PathConfig) -> tuple[RunPlan | None, str | None]:
    """Build the preview run plan while surfacing validation errors as strings."""
    try:
        return run_config.compile_plan(path_config), None
    except Exception as exc:
        return None, str(exc)


def request_support_error(
    *,
    request: RunConfig | None,
    plan: RunPlan | None,
    previewable_statuses: list[AdvioLocalSceneStatus],
) -> str | None:
    """Return why the Pipeline app page cannot execute the current request."""
    if request is None:
        return None
    if plan is None:
        return "The current request failed validation and could not be planned."
    if request.stages.slam.backend.method_id is MethodId.MAST3R:
        return "MASt3R-SLAM is not executable yet. Select ViSTA-SLAM for this pipeline page."
    unavailable_stages = [stage for stage in plan.stages if not stage.available]
    if unavailable_stages:
        return unavailable_stages[0].availability_reason or (
            f"Stage '{unavailable_stages[0].key.value}' is not executable in the current pipeline."
        )
    unsupported_stage_ids = [stage.key.value for stage in plan.stages if stage.key not in _SUPPORTED_APP_STAGE_IDS]
    if unsupported_stage_ids:
        return (
            "The current run console can execute only source, slam, gravity.align, evaluate.trajectory, "
            "reconstruction, and summary stages. Disable: "
            + ", ".join(stage.key.value for stage in plan.stages if stage.key not in _SUPPORTED_APP_STAGE_IDS)
        )
    match request.stages.source.backend:
        case AdvioSourceConfig(sequence_id=sequence_slug):
            if resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=previewable_statuses)[0] is None:
                return f"ADVIO sequence '{sequence_slug}' is not replay-ready in the local dataset."
            return None
        case Record3DSourceConfig():
            if request.mode is not PipelineMode.STREAMING:
                return "Record3D live sources currently require `streaming` mode."
            return None
        case _:
            return (
                f"Source '{request.stages.source.backend.source_id}' is not supported by this run console."
                if request.stages.source.backend is not None
                else "This run console only supports ADVIO dataset replay and Record3D live capture."
            )


def source_input_error(action: PipelinePageAction) -> str | None:
    """Return the current source-control validation error."""
    if action.source_kind is PipelineSourceId.ADVIO:
        return None if action.advio_sequence_id is not None else "Select a replay-ready ADVIO scene."
    return record3d_transport_input_error(
        transport=action.record3d_transport,
        wifi_device_address=action.record3d_wifi_device_address,
    )


def handle_pipeline_page_action(context: AppContext, action: PipelinePageAction) -> str | None:
    """Apply one pipeline-page action and return a surfaced error when one occurs."""
    save_model_updates(
        context.store,
        context.state,
        context.state.pipeline,
        **action.model_dump(mode="python", exclude={"start_requested", "stop_requested"}),
    )
    try:
        if action.stop_requested:
            context.run_service.stop_run()
            return None
        if not action.start_requested:
            return None
        run_config, request_error = build_run_config_from_action(context, action)
        if run_config is None:
            raise ValueError(request_error or "Failed to build the current run config.")
        runtime_source = (
            None
            if run_config.mode is PipelineMode.OFFLINE
            else build_runtime_source_from_run_config(run_config=run_config, path_config=context.path_config)
        )
        context.run_service.start_run(run_config=run_config, runtime_source=runtime_source)
        return None
    except Exception as exc:
        return str(exc)


def discover_pipeline_config_paths(path_config: PathConfig) -> list[Path]:
    """Return available persisted pipeline request configs."""
    config_dir = path_config.resolve_pipeline_configs_dir()
    if not config_dir.exists():
        return []
    return sorted(path.resolve() for path in config_dir.rglob("*.toml") if path.is_file())


def pipeline_config_label(path_config: PathConfig, config_path: Path) -> str:
    """Return one compact config selector label."""
    config_root = path_config.resolve_pipeline_configs_dir()
    try:
        return str(config_path.relative_to(config_root))
    except ValueError:
        return (
            str(config_path.relative_to(path_config.root))
            if config_path.is_relative_to(path_config.root)
            else str(config_path)
        )


def load_pipeline_run_config(path_config: PathConfig, config_path: Path) -> tuple[RunConfig | None, str | None]:
    """Load one persisted pipeline run config while surfacing validation errors as strings."""
    try:
        return load_run_config_toml(path_config=path_config, config_path=config_path), None
    except Exception as exc:
        return None, str(exc)


def resolve_advio_sequence_id(
    *,
    sequence_slug: str,
    statuses: list[AdvioLocalSceneStatus],
) -> tuple[int | None, str | None]:
    """Resolve one ADVIO sequence id and matching error message."""
    sequence_id = None
    for status in statuses:
        if status.scene.sequence_slug == sequence_slug:
            sequence_id = int(status.scene.sequence_id)
            break
    if sequence_id is None and sequence_slug.startswith("advio-"):
        suffix = sequence_slug.split("-", maxsplit=1)[1]
        sequence_id = int(suffix) if suffix.isdigit() else None
    if sequence_id is None:
        return None, f"ADVIO sequence '{sequence_slug}' is not replay-ready in the local dataset."
    return sequence_id, None


def parse_optional_int(*, raw_value: str, field_label: str) -> tuple[int | None, str | None]:
    """Parse a blankable integer form field."""
    if raw_value == "":
        return None, None
    try:
        return int(raw_value), None
    except ValueError:
        return None, f"Enter a whole number for `{field_label}` or leave the field blank."


def parse_optional_float(*, raw_value: str, field_label: str) -> tuple[float | None, str | None]:
    """Parse a blankable positive float form field."""
    if raw_value == "":
        return None, None
    try:
        value = float(raw_value)
    except ValueError:
        return None, f"Enter a positive number for `{field_label}` or leave the field blank."
    return (value, None) if value > 0.0 else (None, f"Enter a positive number for `{field_label}`.")


def request_summary_payload(request: RunConfig) -> JsonObject:
    """Return the compact JSON payload rendered by the Pipeline request preview."""
    payload: JsonObject = {
        "experiment_name": request.experiment_name,
        "mode": request.mode.value,
        "output_dir": request.output_dir.as_posix(),
        "slam": {
            "backend": request.stages.slam.backend.model_dump(mode="json", exclude_none=True),
            "emit_dense_points": request.stages.slam.outputs.emit_dense_points,
            "emit_sparse_points": request.stages.slam.outputs.emit_sparse_points,
        },
        "stages": {
            "align_ground": request.stages.align_ground.model_dump(mode="json"),
            "evaluate_trajectory": request.stages.evaluate_trajectory.model_dump(mode="json"),
            "reconstruction": request.stages.reconstruction.model_dump(mode="json"),
            "evaluate_cloud": request.stages.evaluate_cloud.model_dump(mode="json"),
            "summary": request.stages.summary.model_dump(mode="json"),
        },
        "visualization": request.visualization.model_dump(mode="json"),
    }
    match request.stages.source.backend:
        case AdvioSourceConfig(
            sequence_id=sequence_id,
            frame_stride=frame_stride,
            target_fps=target_fps,
            dataset_serving=dataset_serving,
            respect_video_rotation=respect_video_rotation,
        ):
            payload["source"] = {
                "kind": "advio",
                "sequence_id": sequence_id,
                "frame_stride": frame_stride,
                "target_fps": target_fps,
                "dataset_serving": None if dataset_serving is None else dataset_serving.model_dump(mode="json"),
                "respect_video_rotation": respect_video_rotation,
            }
        case _:
            payload["source"] = request.stages.source.backend.model_dump(mode="json")
    return payload


def record3d_source_config_from_action(action: PipelinePageAction) -> Record3DSourceConfig:
    """Build the typed Record3D live source backend config from one pipeline action."""
    return Record3DSourceConfig(
        transport=Record3DTransportId(action.record3d_transport.value),
        device_index=action.record3d_usb_device_index if action.record3d_transport is Record3DTransportId.USB else 0,
        device_address=action.record3d_wifi_device_address
        if action.record3d_transport is Record3DTransportId.WIFI
        else "",
        frame_timeout_seconds=action.record3d_frame_timeout_seconds,
    )


def backend_payload_from_action(
    action: PipelinePageAction,
) -> dict[str, Path | str | int | float | bool | None]:
    """Return backend config overrides for one action."""
    backend_spec = action.slam_backend_spec
    if backend_spec is None or backend_spec.method_id is not action.method:
        return {}
    payload = backend_spec.model_dump(mode="python")
    payload.pop("method_id", None)
    payload.pop("max_frames", None)
    return payload


def json_dump(payload: BaseData | None) -> str | None:
    """Render one typed payload as pretty JSON when present."""
    if payload is None:
        return None
    return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)


__all__ = [
    "JsonObject",
    "PipelinePageAction",
    "action_from_page_state",
    "backend_payload_from_action",
    "build_preview_plan",
    "build_run_config_from_action",
    "discover_pipeline_config_paths",
    "handle_pipeline_page_action",
    "json_dump",
    "load_pipeline_run_config",
    "parse_optional_int",
    "parse_optional_float",
    "pipeline_config_label",
    "record3d_source_config_from_action",
    "request_summary_payload",
    "request_support_error",
    "resolve_advio_sequence_id",
    "source_input_error",
    "sync_pipeline_page_state_from_template",
]
