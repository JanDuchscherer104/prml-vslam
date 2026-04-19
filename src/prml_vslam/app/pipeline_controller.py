"""Pure controller helpers for the Pipeline Streamlit page."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

import numpy as np

from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.datasets.advio import AdvioLocalSceneStatus, AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval.contracts import TrajectoryEvaluationPreview
from prml_vslam.eval.services import compute_trajectory_ape_preview
from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.methods.events import KeyframeVisualizationReady
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, RunEvent
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.contracts.request import (
    BackendConfigPayload,
    DatasetSourceSpec,
    Record3DLiveSourceSpec,
    SlamStageConfig,
    build_backend_spec,
)
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.demo import build_runtime_source_from_request, load_run_request_toml
from prml_vslam.utils import BaseData, PathConfig
from prml_vslam.utils.json_types import JsonObject
from prml_vslam.visualization.contracts import VisualizationConfig

from .models import PipelinePageState, PipelineSourceId
from .record3d_controls import record3d_transport_input_error
from .state import save_model_updates

if TYPE_CHECKING:
    from prml_vslam.pipeline.run_service import RunService

    from .bootstrap import AppContext

_SUPPORTED_APP_STAGE_IDS = frozenset(
    {
        StageKey.INGEST,
        StageKey.SLAM,
        StageKey.TRAJECTORY_EVALUATION,
        StageKey.SUMMARY,
    }
)

PipelinePageStateUpdateValue: TypeAlias = (
    PipelineSourceId | AdvioPoseSource | Record3DTransportId | int | str | bool | None
)
PipelinePageStateUpdates: TypeAlias = dict[str, PipelinePageStateUpdateValue]


class PipelinePageAction(PipelinePageState):
    """Typed action payload for the pipeline page controls."""

    start_requested: bool = False
    """Whether the user requested a new run."""

    stop_requested: bool = False
    """Whether the user requested the current run to stop."""


@dataclass(frozen=True, slots=True)
class PipelineBackendNoticeView:
    """App-facing projection of the latest backend notice."""

    kind: str
    payload: JsonObject
    camera_intrinsics: CameraIntrinsics | None = None


@dataclass(frozen=True, slots=True)
class PipelineNoticeRenderModel:
    """Status notice rendered above the shared pipeline metric row."""

    level: str
    message: str


@dataclass(frozen=True, slots=True)
class PipelineStreamingRenderModel:
    """Streaming-only snapshot render payload."""

    frame_panel_title: str
    preview_panel_title: str
    frame_image: np.ndarray | None
    preview_image: np.ndarray | None
    preview_empty_message: str
    preview_status_message: str | None
    packet_metadata: JsonObject | None
    backend_notice: PipelineBackendNoticeView | None
    backend_notice_empty_message: str
    intrinsics: CameraIntrinsics | None
    intrinsics_missing_message: str
    positions_xyz: np.ndarray
    timestamps_s: np.ndarray | None
    trajectory_empty_message: str
    show_evo_preview: bool
    evo_preview: TrajectoryEvaluationPreview | None
    evo_error: str | None
    evo_empty_message: str


@dataclass(frozen=True, slots=True)
class PipelineSnapshotRenderModel:
    """Complete render payload for the Pipeline snapshot view."""

    state: RunState
    metrics: tuple[tuple[str, str], ...]
    caption: str | None
    notice: PipelineNoticeRenderModel
    is_offline: bool
    plan_rows: list[dict[str, str]]
    stage_manifest_rows: list[dict[str, str]]
    recent_events: list[JsonObject]
    sequence_manifest_json: str | None
    summary_json: str | None
    slam_json: str | None
    streaming: PipelineStreamingRenderModel | None


def action_from_page_state(page_state: PipelinePageState, config_path: Path) -> PipelinePageAction:
    """Build the current action payload from persisted page state."""
    return PipelinePageAction.model_validate(page_state.model_dump(mode="python") | {"config_path": config_path})


def sync_pipeline_page_state_from_template(
    *,
    context: AppContext,
    config_path: Path,
    request: RunRequest,
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
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug):
            advio_sequence_id, _ = resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=statuses)
            source_updates = {
                "source_kind": PipelineSourceId.ADVIO,
                "advio_sequence_id": advio_sequence_id,
                "pose_source": request.source.pose_source,
                "respect_video_rotation": request.source.respect_video_rotation,
            }
        case Record3DLiveSourceSpec() as record3d_source:
            source_updates = {
                "source_kind": PipelineSourceId.RECORD3D,
                "record3d_transport": Record3DTransportId(record3d_source.transport.value),
                "record3d_usb_device_index": 0
                if record3d_source.device_index is None
                else record3d_source.device_index,
                "record3d_wifi_device_address": record3d_source.device_address,
                "record3d_persist_capture": record3d_source.persist_capture,
            }
        case _:
            source_updates = {"source_kind": page_state.source_kind, "advio_sequence_id": page_state.advio_sequence_id}
    save_model_updates(
        context.store,
        context.state,
        page_state,
        config_path=config_path,
        experiment_name=request.experiment_name,
        mode=request.mode,
        method=MethodId(request.slam.backend.kind),
        slam_max_frames=request.slam.backend.max_frames,
        slam_backend_spec=request.slam.backend.model_copy(deep=True),
        emit_dense_points=request.slam.outputs.emit_dense_points,
        emit_sparse_points=request.slam.outputs.emit_sparse_points,
        reference_enabled=request.benchmark.reference.enabled,
        trajectory_eval_enabled=request.benchmark.trajectory.enabled,
        evaluate_cloud=request.benchmark.cloud.enabled,
        evaluate_efficiency=request.benchmark.efficiency.enabled,
        connect_live_viewer=request.visualization.connect_live_viewer,
        export_viewer_rrd=request.visualization.export_viewer_rrd,
        **source_updates,
    )


def build_request_from_action(context: AppContext, action: PipelinePageAction) -> tuple[RunRequest | None, str | None]:
    """Build a typed pipeline request from one rendered Pipeline page action."""
    try:
        if action.source_kind is PipelineSourceId.ADVIO:
            if action.advio_sequence_id is None:
                raise ValueError("Select a replay-ready ADVIO scene.")
            source = DatasetSourceSpec(
                dataset_id=DatasetId.ADVIO,
                sequence_id=context.advio_service.scene(action.advio_sequence_id).sequence_slug,
                pose_source=action.pose_source,
                respect_video_rotation=action.respect_video_rotation,
            )
        else:
            source = record3d_source_spec_from_action(action)
        request = RunRequest(
            experiment_name=action.experiment_name.strip() or "pipeline-demo",
            mode=action.mode,
            output_dir=context.path_config.artifacts_dir,
            source=source,
            slam=SlamStageConfig(
                backend=build_backend_spec(
                    method=action.method,
                    max_frames=action.slam_max_frames,
                    overrides=backend_payload_from_action(action),
                ),
                outputs={
                    "emit_dense_points": action.emit_dense_points,
                    "emit_sparse_points": action.emit_sparse_points,
                },
            ),
            benchmark=BenchmarkConfig(
                reference={"enabled": action.reference_enabled},
                trajectory=TrajectoryBenchmarkConfig(enabled=action.trajectory_eval_enabled),
                cloud=CloudBenchmarkConfig(enabled=action.evaluate_cloud),
                efficiency=EfficiencyBenchmarkConfig(enabled=action.evaluate_efficiency),
            ),
            visualization=VisualizationConfig(
                export_viewer_rrd=action.export_viewer_rrd,
                connect_live_viewer=action.connect_live_viewer,
            ),
        )
        return request, None
    except Exception as exc:
        return None, str(exc)


def build_preview_plan(request: RunRequest, path_config: PathConfig) -> tuple[RunPlan | None, str | None]:
    """Build the preview run plan while surfacing validation errors as strings."""
    try:
        return request.build(path_config), None
    except Exception as exc:
        return None, str(exc)


def request_support_error(
    *,
    request: RunRequest | None,
    plan: RunPlan | None,
    previewable_statuses: list[AdvioLocalSceneStatus],
) -> str | None:
    """Return why the Pipeline app page cannot execute the current request."""
    if request is None:
        return None
    if plan is None:
        return "The current request failed validation and could not be planned."
    if request.slam.backend.kind == MethodId.MAST3R.value:
        return "MASt3R-SLAM is not executable yet. Select ViSTA-SLAM or Mock Preview for this pipeline page."
    unavailable_stages = [stage for stage in plan.stages if not stage.available]
    if unavailable_stages:
        return unavailable_stages[0].availability_reason or (
            f"Stage '{unavailable_stages[0].key.value}' is not executable in the current pipeline."
        )
    unsupported_stage_ids = [stage.key.value for stage in plan.stages if stage.key not in _SUPPORTED_APP_STAGE_IDS]
    if unsupported_stage_ids:
        return (
            "The current app demo can execute only ingest, slam, trajectory evaluation, and summary stages. Disable: "
            + ", ".join(unsupported_stage_ids)
        )
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug):
            if resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=previewable_statuses)[0] is None:
                return f"ADVIO sequence '{sequence_slug}' is not replay-ready in the local dataset."
            return None
        case Record3DLiveSourceSpec():
            if request.mode is not PipelineMode.STREAMING:
                return "Record3D live sources currently require `streaming` mode."
            return None
        case DatasetSourceSpec(dataset_id=dataset_id):
            return f"Dataset '{dataset_id.value}' is not supported by this demo page."
        case _:
            return "This demo page only supports ADVIO dataset replay and Record3D live capture."


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
        request, request_error = build_request_from_action(context, action)
        if request is None:
            raise ValueError(request_error or "Failed to build the current request.")
        runtime_source = (
            None
            if request.mode is PipelineMode.OFFLINE
            else build_runtime_source_from_request(request=request, path_config=context.path_config)
        )
        context.run_service.start_run(request=request, runtime_source=runtime_source)
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


def load_pipeline_request(path_config: PathConfig, config_path: Path) -> tuple[RunRequest | None, str | None]:
    """Load one persisted pipeline request while surfacing validation errors as strings."""
    try:
        return load_run_request_toml(path_config=path_config, config_path=config_path), None
    except Exception as exc:
        return None, str(exc)


def resolve_evo_preview(snapshot: RunSnapshot) -> tuple[TrajectoryEvaluationPreview | None, str | None]:
    """Resolve a cached in-memory evo APE preview for a completed pipeline snapshot."""
    if (
        snapshot.slam is None
        or snapshot.slam.trajectory_tum is None
        or snapshot.benchmark_inputs is None
        or not snapshot.benchmark_inputs.reference_trajectories
    ):
        return None, None

    reference_path = snapshot.benchmark_inputs.reference_trajectories[0].path
    estimate_path = snapshot.slam.trajectory_tum.path
    if not reference_path.exists() or not estimate_path.exists():
        return None, None
    try:
        return (
            _compute_evo_preview(
                reference_path=reference_path,
                estimate_path=estimate_path,
                reference_mtime_ns=reference_path.stat().st_mtime_ns,
                estimate_mtime_ns=estimate_path.stat().st_mtime_ns,
            ),
            None,
        )
    except (RuntimeError, ValueError) as exc:
        return None, str(exc)


def latest_backend_notice_view(
    run_service: RunService,
    *,
    limit: int = 25,
) -> PipelineBackendNoticeView | None:
    """Return the latest typed backend notice for the pipeline UI."""
    for event in reversed(run_service.tail_events(limit=limit)):
        if not isinstance(event, BackendNoticeReceived):
            continue
        camera_intrinsics = None
        if isinstance(event.notice, KeyframeVisualizationReady):
            camera_intrinsics = event.notice.camera_intrinsics
        return PipelineBackendNoticeView(
            kind=event.notice.kind,
            payload=event.notice.model_dump(mode="json"),
            camera_intrinsics=camera_intrinsics,
        )
    return None


def build_pipeline_snapshot_render_model(
    snapshot: RunSnapshot,
    run_service: RunService,
    *,
    method: MethodId | None,
    show_evo_preview: bool,
) -> PipelineSnapshotRenderModel:
    """Resolve controller-owned render data for the Pipeline snapshot surface."""
    is_offline = snapshot.plan is not None and snapshot.plan.mode is PipelineMode.OFFLINE
    streaming = None
    if not is_offline and isinstance(snapshot, StreamingRunSnapshot):
        packet = snapshot.latest_packet
        backend_notice = latest_backend_notice_view(run_service)
        evo_preview = None
        evo_error = None
        if show_evo_preview:
            evo_preview, evo_error = resolve_evo_preview(snapshot)
        streaming = PipelineStreamingRenderModel(
            frame_panel_title="RGB Frame",
            preview_panel_title="ViSTA Preview Artifact" if method is MethodId.VISTA else "Preview Artifact",
            frame_image=run_service.read_array(snapshot.latest_frame),
            preview_image=run_service.read_array(snapshot.latest_preview),
            preview_empty_message=_streaming_pointmap_empty_message(method),
            preview_status_message=None if snapshot.latest_preview is None else "Current keyframe artifact.",
            packet_metadata=None
            if packet is None
            else {
                "seq": packet.seq,
                "timestamp_ns": packet.timestamp_ns,
                "provenance": packet.provenance.compact_payload(),
            },
            backend_notice=backend_notice,
            backend_notice_empty_message="No SLAM update is available yet.",
            intrinsics=None if backend_notice is None else backend_notice.camera_intrinsics,
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
            positions_xyz=np.asarray(snapshot.trajectory_positions_xyz, dtype=np.float64).reshape(-1, 3),
            timestamps_s=(
                None
                if len(snapshot.trajectory_timestamps_s) == 0
                else np.asarray(snapshot.trajectory_timestamps_s, dtype=np.float64)
            ),
            trajectory_empty_message=_streaming_trajectory_empty_message(method),
            show_evo_preview=show_evo_preview,
            evo_preview=evo_preview,
            evo_error=evo_error,
            evo_empty_message=(
                "Complete one demo run with a reference trajectory to render the evo APE colormap for this slice."
            ),
        )
    caption = None
    if snapshot.plan is not None:
        caption = f"Run Id: `{snapshot.plan.run_id}` · Artifact Root: `{snapshot.plan.artifact_root}`"
        if method is not None:
            caption += f" · Method: {method.display_name}"
    return PipelineSnapshotRenderModel(
        state=snapshot.state,
        metrics=_pipeline_metrics(snapshot),
        caption=caption,
        notice=_pipeline_notice(snapshot, is_offline=is_offline),
        is_offline=is_offline,
        plan_rows=[] if snapshot.plan is None else snapshot.plan.stage_rows(),
        stage_manifest_rows=[] if not snapshot.stage_manifests else StageManifest.table_rows(snapshot.stage_manifests),
        recent_events=_recent_event_rows(run_service.tail_events(limit=10)),
        sequence_manifest_json=_json_dump(snapshot.sequence_manifest),
        summary_json=_json_dump(snapshot.summary),
        slam_json=_json_dump(snapshot.slam),
        streaming=streaming,
    )


@lru_cache(maxsize=32)
def _compute_evo_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    reference_mtime_ns: int,
    estimate_mtime_ns: int,
) -> TrajectoryEvaluationPreview:
    del reference_mtime_ns, estimate_mtime_ns
    return compute_trajectory_ape_preview(reference_path=reference_path, estimate_path=estimate_path)


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


def request_summary_payload(request: RunRequest) -> JsonObject:
    """Return the compact JSON payload rendered by the Pipeline request preview."""
    payload: JsonObject = {
        "experiment_name": request.experiment_name,
        "mode": request.mode.value,
        "output_dir": request.output_dir.as_posix(),
        "slam": {
            "backend": request.slam.backend.model_dump(mode="json", exclude_none=True),
            "emit_dense_points": request.slam.outputs.emit_dense_points,
            "emit_sparse_points": request.slam.outputs.emit_sparse_points,
        },
        "benchmark": request.benchmark.model_dump(mode="json"),
        "visualization": request.visualization.model_dump(mode="json"),
    }
    match request.source:
        case DatasetSourceSpec(
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            pose_source=pose_source,
            respect_video_rotation=respect_video_rotation,
        ):
            payload["source"] = {
                "kind": "dataset",
                "dataset_id": dataset_id.value,
                "sequence_id": sequence_id,
                "pose_source": pose_source.value,
                "respect_video_rotation": respect_video_rotation,
            }
        case _:
            payload["source"] = request.source.model_dump(mode="json")
    return payload


def record3d_source_spec_from_action(action: PipelinePageAction) -> Record3DLiveSourceSpec:
    """Build the typed Record3D live source contract from one pipeline action."""
    return Record3DLiveSourceSpec(
        persist_capture=action.record3d_persist_capture,
        transport=Record3DTransportId(action.record3d_transport.value),
        device_index=action.record3d_usb_device_index if action.record3d_transport is Record3DTransportId.USB else None,
        device_address=action.record3d_wifi_device_address
        if action.record3d_transport is Record3DTransportId.WIFI
        else "",
    )


def backend_payload_from_action(action: PipelinePageAction) -> BackendConfigPayload:
    """Return backend config overrides for one action."""
    backend_spec = action.slam_backend_spec
    if backend_spec is None or backend_spec.kind != action.method.value:
        return {}
    payload = backend_spec.model_dump(mode="python")
    payload.pop("kind", None)
    payload.pop("max_frames", None)
    return payload


def _pipeline_metrics(snapshot: RunSnapshot) -> tuple[tuple[str, str], ...]:
    received_frames = snapshot.received_frames if isinstance(snapshot, StreamingRunSnapshot) else 0
    measured_fps = snapshot.measured_fps if isinstance(snapshot, StreamingRunSnapshot) else 0.0
    accepted_keyframes = snapshot.accepted_keyframes if isinstance(snapshot, StreamingRunSnapshot) else 0
    backend_fps = snapshot.backend_fps if isinstance(snapshot, StreamingRunSnapshot) else 0.0
    num_sparse_points = snapshot.num_sparse_points if isinstance(snapshot, StreamingRunSnapshot) else 0
    num_dense_points = snapshot.num_dense_points if isinstance(snapshot, StreamingRunSnapshot) else 0
    return (
        ("Status", snapshot.state.value.upper()),
        ("Mode", "Idle" if snapshot.plan is None else snapshot.plan.mode.label),
        ("Received Frames", str(received_frames)),
        ("Packet FPS", f"{measured_fps:.2f} fps"),
        ("Accepted Keyframes", str(accepted_keyframes)),
        ("Keyframe FPS", f"{backend_fps:.2f} fps"),
        ("Sparse Points", str(num_sparse_points)),
        ("Dense Points", str(num_dense_points)),
    )


def _pipeline_notice(snapshot: RunSnapshot, *, is_offline: bool) -> PipelineNoticeRenderModel:
    match snapshot.state:
        case RunState.IDLE:
            return PipelineNoticeRenderModel(
                level="info",
                message="Select a request template, configure the supported source and stages, then start the pipeline demo.",
            )
        case RunState.PREPARING:
            return PipelineNoticeRenderModel(
                level="info",
                message="Preparing the sequence manifest and starting the selected SLAM backend.",
            )
        case RunState.RUNNING:
            return PipelineNoticeRenderModel(
                level="success",
                message=(
                    "Processing the bounded offline slice and materializing artifacts."
                    if is_offline
                    else "Processing frames through the selected SLAM backend."
                ),
            )
        case RunState.COMPLETED:
            return PipelineNoticeRenderModel(
                level="success",
                message=(
                    "The bounded offline demo finished and wrote artifacts."
                    if is_offline
                    else "The bounded demo finished and wrote SLAM artifacts."
                ),
            )
        case RunState.STOPPED:
            return PipelineNoticeRenderModel(
                level="warning",
                message=(
                    "The offline demo stopped. The written artifacts remain visible below."
                    if is_offline
                    else "The demo stopped. The last frame, trajectory, and written artifacts remain visible below."
                ),
            )
        case RunState.FAILED:
            return PipelineNoticeRenderModel(
                level="error", message=snapshot.error_message or "The pipeline demo failed."
            )


def _recent_event_rows(events: list[RunEvent]) -> list[JsonObject]:
    return [
        {
            "event_id": event.event_id,
            "kind": event.kind,
            "tier": event.tier.value,
        }
        for event in events
    ]


def _streaming_pointmap_empty_message(method: MethodId | None) -> str:
    if method is MethodId.VISTA:
        return "ViSTA-SLAM has not produced a renderable preview artifact for the current keyframe yet."
    return "No pointmap preview is available for the current frame."


def _streaming_trajectory_empty_message(method: MethodId | None) -> str:
    if method is MethodId.VISTA:
        return "ViSTA-SLAM has not accepted a keyframe pose yet, so no live trajectory is available."
    return "The selected SLAM backend has not produced any trajectory points yet."


def _json_dump(payload: BaseData | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True)
