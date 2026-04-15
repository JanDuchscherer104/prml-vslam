"""Snapshot-presentation helpers plus public Pipeline page controller facade."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from prml_vslam.eval.contracts import TrajectoryEvaluationPreview
from prml_vslam.eval.services import compute_trajectory_ape_preview
from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.methods import MethodId
from prml_vslam.methods.events import KeyframeVisualizationReady
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.events import BackendNoticeReceived, RunEvent
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.utils.json_types import JsonObject

from .pipeline_controls import (
    PipelinePageAction,
    action_from_page_state,
    backend_payload_from_action,
    build_preview_plan,
    build_request_from_action,
    discover_pipeline_config_paths,
    handle_pipeline_page_action,
    json_dump,
    load_pipeline_request,
    parse_optional_float,
    parse_optional_int,
    pipeline_config_label,
    record3d_source_spec_from_action,
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
    stage_manifest_rows: list[dict[str, str]]
    recent_events: list[JsonObject]
    sequence_manifest_json: str | None
    summary_json: str | None
    slam_json: str | None
    streaming: PipelineStreamingRenderModel | None


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
        sequence_manifest_json=json_dump(snapshot.sequence_manifest),
        summary_json=json_dump(snapshot.summary),
        slam_json=json_dump(snapshot.slam),
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
    "build_request_from_action",
    "discover_pipeline_config_paths",
    "handle_pipeline_page_action",
    "latest_backend_notice_view",
    "load_pipeline_request",
    "parse_optional_int",
    "parse_optional_float",
    "pipeline_config_label",
    "record3d_source_spec_from_action",
    "request_summary_payload",
    "request_support_error",
    "resolve_advio_sequence_id",
    "resolve_evo_preview",
    "source_input_error",
    "sync_pipeline_page_state_from_template",
]
