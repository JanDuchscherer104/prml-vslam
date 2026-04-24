"""Snapshot-presentation helpers for the Pipeline page."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias
from urllib.parse import quote

import numpy as np

from prml_vslam.eval.contracts import TrajectoryEvaluationPreview
from prml_vslam.eval.services import compute_trajectory_ape_preview
from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.slam.config import MethodId

from .models import PipelinePageState, PipelineTelemetryMetricId, PipelineTelemetrySample, PipelineTelemetryViewMode

if TYPE_CHECKING:
    from prml_vslam.pipeline.run_service import RunService

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
TelemetryChartValue: TypeAlias = str | int | float
TelemetryChartRow: TypeAlias = dict[str, TelemetryChartValue]
DEFAULT_RERUN_WEB_VIEWER_URL = "http://127.0.0.1:9090/"
"""Default local Rerun web viewer base URL."""


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
class PipelineViewerLinkModel:
    """Clickable Rerun viewer link state for the Pipeline page."""

    enabled: bool
    grpc_url: str
    web_url: str | None
    status_message: str


@dataclass(frozen=True, slots=True)
class PipelineStageStatusRow:
    """One app-facing stage status row."""

    stage: str
    stage_id: str
    lifecycle: str
    available: str
    progress: str
    fps: str
    throughput: str
    latency: str
    queue: str
    tasks: str
    artifacts: str
    updated: str
    message: str
    executor: str
    resources: str

    def table_row(self) -> dict[str, str]:
        """Return the Streamlit table row payload."""
        return {
            "Stage": self.stage,
            "Id": self.stage_id,
            "State": self.lifecycle,
            "Available": self.available,
            "Progress": self.progress,
            "FPS": self.fps,
            "Throughput": self.throughput,
            "Latency": self.latency,
            "Queue": self.queue,
            "Tasks": self.tasks,
            "Artifacts": self.artifacts,
            "Updated": self.updated,
            "Message": self.message,
            "Executor": self.executor,
            "Resources": self.resources,
        }


@dataclass(frozen=True, slots=True)
class PipelineTelemetryChartModel:
    """Rolling telemetry chart payload."""

    rows: list[TelemetryChartRow]
    metric: PipelineTelemetryMetricId
    metric_label: str
    unit_label: str
    selected_stage_key: StageKey | None
    empty_message: str


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
    stage_status_rows: list[PipelineStageStatusRow]
    telemetry_visible: bool
    telemetry_view_mode: PipelineTelemetryViewMode
    telemetry_chart: PipelineTelemetryChartModel | None
    stage_outcome_rows: list[dict[str, str]]
    recent_events: list[JsonObject]
    stage_outcomes_json: str | None
    artifacts_json: str | None
    stage_runtime_status_json: str | None
    streaming: PipelineStreamingRenderModel | None


def refreshed_pipeline_telemetry_history(
    page_state: PipelinePageState,
    snapshot: RunSnapshot,
) -> tuple[str | None, list[PipelineTelemetrySample], bool]:
    """Return the bounded telemetry history after incorporating one snapshot."""
    run_id = snapshot.run_id or None
    if run_id is None:
        changed = page_state.telemetry_history_run_id is not None or bool(page_state.telemetry_history)
        return None, [], changed

    history = [] if page_state.telemetry_history_run_id != run_id else list(page_state.telemetry_history)
    seen = {(sample.stage_key, sample.updated_at_ns) for sample in history}
    for status in snapshot.stage_runtime_status.values():
        key = (status.stage_key, status.updated_at_ns)
        if key in seen:
            continue
        history.append(
            PipelineTelemetrySample(
                run_id=run_id,
                stage_key=status.stage_key,
                updated_at_ns=status.updated_at_ns,
                lifecycle_state=status.lifecycle_state.value,
                progress_message=status.progress_message,
                processed_items=status.processed_items,
                fps=status.fps,
                throughput=status.throughput,
                latency_ms=status.latency_ms,
                queue_depth=status.queue_depth,
                backlog_count=status.backlog_count,
                submitted_count=status.submitted_count,
                completed_count=status.completed_count,
                failed_count=status.failed_count,
                in_flight_count=status.in_flight_count,
            )
        )
        seen.add(key)

    max_samples = max(1, page_state.telemetry_max_samples)
    if len(history) > max_samples:
        history = history[-max_samples:]
    changed = page_state.telemetry_history_run_id != run_id or history != page_state.telemetry_history
    return run_id, history, changed


def telemetry_stage_options(
    snapshot: RunSnapshot,
    history: Sequence[PipelineTelemetrySample],
) -> list[StageKey]:
    """Return stage keys with planned, live, terminal, or historical telemetry context."""
    ordered: list[StageKey] = []
    if snapshot.plan is not None:
        ordered.extend(stage.key for stage in snapshot.plan.stages)
    ordered.extend(snapshot.stage_runtime_status)
    ordered.extend(snapshot.stage_outcomes)
    ordered.extend(sample.stage_key for sample in history)
    return _unique_stage_keys(ordered)


def build_pipeline_viewer_link_model(
    *,
    connect_live_viewer: bool,
    grpc_url: str,
    viewer_base_url: str = DEFAULT_RERUN_WEB_VIEWER_URL,
) -> PipelineViewerLinkModel:
    """Return the Streamlit-facing Rerun viewer link for one run configuration."""
    resolved_grpc_url = grpc_url.strip()
    if not connect_live_viewer:
        return PipelineViewerLinkModel(
            enabled=False,
            grpc_url=resolved_grpc_url,
            web_url=None,
            status_message="Live Rerun viewer is disabled for this run.",
        )
    if not resolved_grpc_url:
        return PipelineViewerLinkModel(
            enabled=False,
            grpc_url=resolved_grpc_url,
            web_url=None,
            status_message="Live Rerun viewer is enabled, but no gRPC URL is configured.",
        )
    resolved_base_url = viewer_base_url.strip() or DEFAULT_RERUN_WEB_VIEWER_URL
    separator = "&" if "?" in resolved_base_url else "?"
    return PipelineViewerLinkModel(
        enabled=True,
        grpc_url=resolved_grpc_url,
        web_url=f"{resolved_base_url}{separator}url={quote(resolved_grpc_url, safe='')}",
        status_message="Open the local Rerun web viewer for this live endpoint.",
    )


def resolve_evo_preview(snapshot: RunSnapshot) -> tuple[TrajectoryEvaluationPreview | None, str | None]:
    """Resolve a cached in-memory evo APE preview for a completed pipeline snapshot."""
    estimate = snapshot.artifacts.get("trajectory_tum")
    reference = next(
        (
            artifact
            for artifact_key, artifact in snapshot.artifacts.items()
            if artifact_key.startswith("reference_tum:")
        ),
        None,
    )
    if estimate is None or reference is None:
        return None, None

    reference_path = reference.path
    estimate_path = estimate.path
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
    """Return the latest typed backend notice for the pipeline UI.

    Durable backend-notice events were retired in WP-09C. Live backend state is
    now projected through runtime status and live payload refs, so this optional
    render hook remains empty until semantic update history gets its target
    app-facing projection.
    """
    del run_service, limit
    return None


def build_pipeline_snapshot_render_model(
    snapshot: RunSnapshot,
    run_service: RunService,
    *,
    method: MethodId | None,
    show_evo_preview: bool,
    telemetry_history: Sequence[PipelineTelemetrySample] = (),
    telemetry_visible: bool = True,
    telemetry_view_mode: PipelineTelemetryViewMode = PipelineTelemetryViewMode.LATEST,
    telemetry_selected_stage_key: StageKey | None = None,
    telemetry_selected_metric: PipelineTelemetryMetricId = PipelineTelemetryMetricId.FPS,
    now_ns: int | None = None,
) -> PipelineSnapshotRenderModel:
    """Resolve controller-owned render data for the Pipeline snapshot surface."""
    resolved_now_ns = time.time_ns() if now_ns is None else now_ns
    is_offline = snapshot.plan is not None and snapshot.plan.mode is PipelineMode.OFFLINE
    streaming = None
    if not is_offline and _has_streaming_projection(snapshot):
        slam_status = snapshot.stage_runtime_status.get(StageKey.SLAM)
        packet_metadata = None
        if slam_status is not None:
            packet_metadata = {
                "stage": StageKey.SLAM.value,
                "processed_items": slam_status.processed_items,
                "fps": slam_status.fps,
                "throughput": slam_status.throughput,
                "updated_at_ns": slam_status.updated_at_ns,
            }
        backend_notice = latest_backend_notice_view(run_service)
        frame_image = _resolve_frame_image(run_service, snapshot)
        preview_image = _resolve_preview_image(run_service, snapshot)
        evo_preview = None
        evo_error = None
        if show_evo_preview:
            evo_preview, evo_error = resolve_evo_preview(snapshot)
        streaming = PipelineStreamingRenderModel(
            frame_panel_title="RGB Frame",
            preview_panel_title="ViSTA Preview Artifact" if method is MethodId.VISTA else "Preview Artifact",
            frame_image=frame_image,
            preview_image=preview_image,
            preview_empty_message=_streaming_pointmap_empty_message(method),
            preview_status_message=None if preview_image is None else "Current keyframe artifact.",
            packet_metadata=packet_metadata,
            backend_notice=backend_notice,
            backend_notice_empty_message="No SLAM update is available yet.",
            intrinsics=None if backend_notice is None else backend_notice.camera_intrinsics,
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
            positions_xyz=_streaming_positions(snapshot),
            timestamps_s=None,
            trajectory_empty_message=_streaming_trajectory_empty_message(method),
            show_evo_preview=show_evo_preview,
            evo_preview=evo_preview,
            evo_error=evo_error,
            evo_empty_message=(
                "Complete one run with a reference trajectory to render the evo APE colormap for this slice."
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
        stage_status_rows=_stage_status_rows(snapshot, now_ns=resolved_now_ns),
        telemetry_visible=telemetry_visible,
        telemetry_view_mode=telemetry_view_mode,
        telemetry_chart=_telemetry_chart_model(
            telemetry_history,
            selected_stage_key=telemetry_selected_stage_key,
            metric=telemetry_selected_metric,
        )
        if telemetry_visible and telemetry_view_mode is PipelineTelemetryViewMode.ROLLING
        else None,
        stage_outcome_rows=_stage_outcome_rows(snapshot),
        recent_events=_recent_event_rows(run_service.tail_events(limit=10)),
        stage_outcomes_json=_json_dump_mapping(
            {stage_key.value: outcome.model_dump(mode="json") for stage_key, outcome in snapshot.stage_outcomes.items()}
        ),
        artifacts_json=_json_dump_mapping(
            {artifact_key: artifact.model_dump(mode="json") for artifact_key, artifact in snapshot.artifacts.items()}
        ),
        stage_runtime_status_json=_json_dump_mapping(
            {
                stage_key.value: status.model_dump(mode="json")
                for stage_key, status in snapshot.stage_runtime_status.items()
            }
        ),
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


def _pipeline_metrics(snapshot: RunSnapshot) -> tuple[tuple[str, str], ...]:
    slam_status = snapshot.stage_runtime_status.get(StageKey.SLAM)
    processed_frame_count = 0 if slam_status is None else slam_status.processed_items
    measured_fps = 0.0 if slam_status is None or slam_status.fps is None else slam_status.fps
    backend_fps = 0.0 if slam_status is None or slam_status.throughput is None else slam_status.throughput
    accepted_keyframe_count = 0
    num_sparse_points = 0
    num_dense_points = 0
    if (outcome := snapshot.stage_outcomes.get(StageKey.SLAM)) is not None:
        accepted_keyframe_count = _coerce_int_metric(outcome.metrics.get("accepted_keyframe_count"))
        num_sparse_points = _coerce_int_metric(outcome.metrics.get("num_sparse_points"))
        num_dense_points = _coerce_int_metric(outcome.metrics.get("num_dense_points"))
    return (
        ("Status", snapshot.state.value.upper()),
        ("Mode", "Idle" if snapshot.plan is None else snapshot.plan.mode.title()),
        ("Received Frames", str(processed_frame_count)),
        ("Packet FPS", f"{measured_fps:.2f} fps"),
        ("Accepted Keyframes", str(accepted_keyframe_count)),
        ("Keyframe FPS", f"{backend_fps:.2f} fps"),
        ("Sparse Points", str(num_sparse_points)),
        ("Dense Points", str(num_dense_points)),
    )


def _pipeline_notice(snapshot: RunSnapshot, *, is_offline: bool) -> PipelineNoticeRenderModel:
    match snapshot.state:
        case RunState.IDLE:
            return PipelineNoticeRenderModel(
                level="info",
                message=(
                    "Select a request template, configure the supported source and stages, then start the pipeline."
                ),
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
                    "The bounded offline run finished and wrote artifacts."
                    if is_offline
                    else "The bounded run finished and wrote SLAM artifacts."
                ),
            )
        case RunState.STOPPED:
            return PipelineNoticeRenderModel(
                level="warning",
                message=(
                    "The offline run stopped. The written artifacts remain visible below."
                    if is_offline
                    else "The run stopped. The last frame, trajectory, and written artifacts remain visible below."
                ),
            )
        case RunState.FAILED:
            return PipelineNoticeRenderModel(
                level="error", message=snapshot.error_message or "The pipeline run failed."
            )


def _stage_status_rows(snapshot: RunSnapshot, *, now_ns: int) -> list[PipelineStageStatusRow]:
    if snapshot.plan is None and not snapshot.stage_runtime_status and not snapshot.stage_outcomes:
        return []
    planned = {stage.key: stage for stage in snapshot.plan.stages} if snapshot.plan is not None else {}
    stage_key_candidates: list[StageKey] = []
    if snapshot.plan is not None:
        stage_key_candidates.extend(stage.key for stage in snapshot.plan.stages)
    stage_key_candidates.extend(snapshot.stage_runtime_status)
    stage_key_candidates.extend(snapshot.stage_outcomes)
    stage_keys = _unique_stage_keys(stage_key_candidates)
    rows: list[PipelineStageStatusRow] = []
    for stage_key in stage_keys:
        plan_stage = planned.get(stage_key)
        status = snapshot.stage_runtime_status.get(stage_key)
        outcome = snapshot.stage_outcomes.get(stage_key)
        rows.append(
            PipelineStageStatusRow(
                stage=stage_key.label,
                stage_id=stage_key.value,
                lifecycle=_stage_lifecycle(
                    plan_available=None if plan_stage is None else plan_stage.available,
                    status=status,
                    outcome=outcome,
                ),
                available=_stage_available_label(plan_stage),
                progress=_stage_progress_label(status),
                fps=_format_optional_rate(None if status is None else status.fps),
                throughput=_format_throughput(status),
                latency=_format_latency(status),
                queue=_format_queue(status),
                tasks=_format_tasks(status),
                artifacts="0" if outcome is None else str(len(outcome.artifacts)),
                updated=_format_updated_age(status, now_ns=now_ns),
                message=_stage_message(plan_stage, status, outcome),
                executor="" if status is None or status.executor_id is None else status.executor_id,
                resources=_format_resources(status),
            )
        )
    return rows


def _telemetry_chart_model(
    history: Sequence[PipelineTelemetrySample],
    *,
    selected_stage_key: StageKey | None,
    metric: PipelineTelemetryMetricId,
) -> PipelineTelemetryChartModel:
    stage_options = _unique_stage_keys(sample.stage_key for sample in history)
    resolved_stage_key = (
        selected_stage_key if selected_stage_key in stage_options else (stage_options[0] if stage_options else None)
    )
    rows: list[TelemetryChartRow] = []
    if resolved_stage_key is not None:
        sample_index = 0
        for sample in history:
            if sample.stage_key is not resolved_stage_key:
                continue
            value = _telemetry_metric_value(sample, metric)
            if value is None:
                continue
            rows.append(
                {
                    "sample": sample_index,
                    "stage": sample.stage_key.value,
                    "value": float(value),
                    "updated_at_ns": sample.updated_at_ns,
                }
            )
            sample_index += 1
    return PipelineTelemetryChartModel(
        rows=rows,
        metric=metric,
        metric_label=metric.label,
        unit_label=metric.unit_label,
        selected_stage_key=resolved_stage_key,
        empty_message="No rolling telemetry samples are available for the selected stage and metric.",
    )


def _unique_stage_keys(stage_keys: Iterable[StageKey]) -> list[StageKey]:
    unique: list[StageKey] = []
    for stage_key in stage_keys:
        if stage_key not in unique:
            unique.append(stage_key)
    return unique


def _stage_lifecycle(
    *,
    plan_available: bool | None,
    status: object,
    outcome: object,
) -> str:
    if status is not None:
        return status.lifecycle_state.value
    if outcome is not None:
        return outcome.status.value
    if plan_available is False:
        return "unavailable"
    if plan_available is True:
        return "planned"
    return "observed"


def _stage_available_label(plan_stage: object) -> str:
    if plan_stage is None:
        return "n/a"
    return "yes" if plan_stage.available else "no"


def _stage_progress_label(status: object) -> str:
    if status is None:
        return "n/a"
    if status.completed_steps is not None and status.total_steps is not None:
        unit = f" {status.progress_unit}" if status.progress_unit else ""
        return f"{status.completed_steps}/{status.total_steps}{unit}"
    if status.completed_steps is not None:
        unit = f" {status.progress_unit}" if status.progress_unit else ""
        return f"{status.completed_steps}{unit}"
    return status.progress_message or "n/a"


def _stage_message(plan_stage: object, status: object, outcome: object) -> str:
    if status is not None:
        return status.last_error or status.last_warning or status.progress_message
    if outcome is not None:
        return outcome.error_message
    if plan_stage is not None:
        return plan_stage.availability_reason or ""
    return ""


def _format_optional_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def _format_throughput(status: object) -> str:
    if status is None or status.throughput is None:
        return "n/a"
    unit = status.throughput_unit or "items/s"
    return f"{status.throughput:.2f} {unit}"


def _format_latency(status: object) -> str:
    if status is None or status.latency_ms is None:
        return "n/a"
    return f"{status.latency_ms:.1f} ms"


def _format_queue(status: object) -> str:
    if status is None or (status.queue_depth is None and status.backlog_count is None):
        return "n/a"
    queue = "n/a" if status.queue_depth is None else str(status.queue_depth)
    backlog = "n/a" if status.backlog_count is None else str(status.backlog_count)
    return f"q {queue} / back {backlog}"


def _format_tasks(status: object) -> str:
    if status is None:
        return "n/a"
    return (
        f"{status.submitted_count} submitted / {status.completed_count} done / "
        f"{status.failed_count} failed / {status.in_flight_count} in flight"
    )


def _format_resources(status: object) -> str:
    if status is None or not status.resource_assignment:
        return ""
    return ", ".join(f"{key}={value}" for key, value in sorted(status.resource_assignment.items()))


def _format_updated_age(status: object, *, now_ns: int) -> str:
    if status is None or status.updated_at_ns <= 0:
        return "n/a"
    age_ns = now_ns - status.updated_at_ns
    if age_ns < 0:
        return "updated"
    age_s = age_ns / 1_000_000_000
    if age_s < 1.0:
        return "<1 s"
    if age_s < 60.0:
        return f"{age_s:.0f} s"
    return f"{age_s / 60.0:.1f} min"


def _telemetry_metric_value(sample: PipelineTelemetrySample, metric: PipelineTelemetryMetricId) -> float | int | None:
    match metric:
        case PipelineTelemetryMetricId.FPS:
            return sample.fps
        case PipelineTelemetryMetricId.THROUGHPUT:
            return sample.throughput
        case PipelineTelemetryMetricId.LATENCY_MS:
            return sample.latency_ms
        case PipelineTelemetryMetricId.QUEUE_DEPTH:
            return sample.queue_depth
        case PipelineTelemetryMetricId.BACKLOG_COUNT:
            return sample.backlog_count
        case PipelineTelemetryMetricId.PROCESSED_ITEMS:
            return sample.processed_items
        case PipelineTelemetryMetricId.IN_FLIGHT_COUNT:
            return sample.in_flight_count


def _recent_event_rows(events: list[RunEvent]) -> list[JsonObject]:
    return [
        {
            "event_id": event.event_id,
            "kind": event.kind,
        }
        for event in events
    ]


def _has_streaming_projection(snapshot: RunSnapshot) -> bool:
    if snapshot.plan is None or snapshot.plan.mode is not PipelineMode.STREAMING:
        return False
    return (
        snapshot.state is not RunState.IDLE
        or bool(snapshot.stage_runtime_status)
        or bool(snapshot.live_refs)
        or bool(snapshot.stage_outcomes)
    )


def _resolve_frame_image(run_service: RunService, snapshot: RunSnapshot) -> np.ndarray | None:
    return _resolve_first_payload(
        run_service,
        snapshot,
        (
            (StageKey.SLAM, "source_rgb:image"),
            (StageKey.SLAM, "model_rgb:image"),
            (StageKey.SLAM, "model_camera_rgb:image"),
            (StageKey.SLAM, "keyframe_rgb:image"),
            (StageKey.SOURCE, "source_rgb:image"),
        ),
    )


def _resolve_preview_image(run_service: RunService, snapshot: RunSnapshot) -> np.ndarray | None:
    return _resolve_first_payload(
        run_service,
        snapshot,
        (
            (StageKey.SLAM, "model_preview:image"),
            (StageKey.SLAM, "keyframe_preview:image"),
            (StageKey.SLAM, "preview:image"),
        ),
    )


def _resolve_first_payload(
    run_service: RunService,
    snapshot: RunSnapshot,
    candidates: tuple[tuple[StageKey, str], ...],
) -> np.ndarray | None:
    for stage_key, ref_key in candidates:
        ref = _live_ref(snapshot, stage_key=stage_key, ref_key=ref_key)
        if ref is None:
            continue
        payload = run_service.read_payload(ref)
        if payload is not None:
            return payload
    return None


def _live_ref(snapshot: RunSnapshot, *, stage_key: StageKey, ref_key: str) -> TransientPayloadRef | None:
    return snapshot.live_refs.get(stage_key, {}).get(ref_key)


def _streaming_positions(snapshot: RunSnapshot) -> np.ndarray:
    return np.empty((0, 3), dtype=np.float64)


def _coerce_int_metric(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _json_dump_mapping(payload: dict[str, object]) -> str | None:
    if not payload:
        return None
    return json.dumps(payload, indent=2, sort_keys=True)


def _streaming_pointmap_empty_message(method: MethodId | None) -> str:
    if method is MethodId.VISTA:
        return "ViSTA-SLAM has not produced a renderable preview artifact for the current keyframe yet."
    return "No pointmap preview is available for the current frame."


def _streaming_trajectory_empty_message(method: MethodId | None) -> str:
    if method is MethodId.VISTA:
        return "ViSTA-SLAM has not accepted a keyframe pose yet, so no live trajectory is available."
    return "The selected SLAM backend has not produced any trajectory points yet."


def _stage_outcome_rows(snapshot: RunSnapshot) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for stage_key, outcome in sorted(snapshot.stage_outcomes.items(), key=lambda item: item[0].value):
        rows.append(
            {
                "Stage": stage_key.value,
                "Status": outcome.status.value,
                "Config Hash": outcome.config_hash,
                "Outputs": ", ".join(sorted(artifact.path.name for artifact in outcome.artifacts.values())),
            }
        )
    return rows


__all__ = [
    "DEFAULT_RERUN_WEB_VIEWER_URL",
    "PipelineBackendNoticeView",
    "PipelineNoticeRenderModel",
    "PipelineSnapshotRenderModel",
    "PipelineStageStatusRow",
    "PipelineStreamingRenderModel",
    "PipelineViewerLinkModel",
    "build_pipeline_viewer_link_model",
    "PipelineTelemetryChartModel",
    "build_pipeline_snapshot_render_model",
    "latest_backend_notice_view",
    "refreshed_pipeline_telemetry_history",
    "resolve_evo_preview",
    "telemetry_stage_options",
]
