"""Snapshot-presentation helpers plus public Pipeline page controller facade."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from prml_vslam.eval.contracts import TrajectoryEvaluationPreview
from prml_vslam.eval.services import compute_trajectory_ape_preview
from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef

from .pipeline_controls import (
    JsonObject,
    PipelinePageAction,
    action_from_page_state,
    backend_payload_from_action,
    build_preview_plan,
    build_run_config_from_action,
    discover_pipeline_config_paths,
    handle_pipeline_page_action,
    load_pipeline_request,
    parse_optional_float,
    parse_optional_int,
    pipeline_config_label,
    record3d_source_config_from_action,
    request_summary_payload,
    request_support_error,
    resolve_advio_sequence_id,
    source_input_error,
    sync_pipeline_page_state_from_template,
)

if TYPE_CHECKING:
    from prml_vslam.pipeline.run_service import RunService


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
    stage_outcome_rows: list[dict[str, str]]
    recent_events: list[JsonObject]
    stage_outcomes_json: str | None
    artifacts_json: str | None
    stage_runtime_status_json: str | None
    streaming: PipelineStreamingRenderModel | None


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
) -> PipelineSnapshotRenderModel:
    """Resolve controller-owned render data for the Pipeline snapshot surface."""
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
            (StageKey.INGEST, "source_rgb:image"),
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
    "PipelineBackendNoticeView",
    "PipelineNoticeRenderModel",
    "PipelinePageAction",
    "PipelineSnapshotRenderModel",
    "PipelineStreamingRenderModel",
    "action_from_page_state",
    "backend_payload_from_action",
    "build_pipeline_snapshot_render_model",
    "build_preview_plan",
    "build_run_config_from_action",
    "discover_pipeline_config_paths",
    "handle_pipeline_page_action",
    "latest_backend_notice_view",
    "load_pipeline_request",
    "parse_optional_int",
    "parse_optional_float",
    "pipeline_config_label",
    "record3d_source_config_from_action",
    "request_summary_payload",
    "request_support_error",
    "resolve_advio_sequence_id",
    "resolve_evo_preview",
    "source_input_error",
    "sync_pipeline_page_state_from_template",
]
