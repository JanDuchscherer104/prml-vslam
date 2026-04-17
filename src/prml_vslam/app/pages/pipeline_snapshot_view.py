"""Rendering helpers for the Pipeline page run snapshot."""

from __future__ import annotations

import json

import numpy as np
import streamlit as st

from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.plotting import build_evo_ape_colormap_figure
from prml_vslam.utils import BaseConfig

from ..live_session import (
    LiveMetric,
    render_camera_intrinsics,
    render_live_image,
    render_live_session_shell,
    render_live_trajectory,
)
from ..pipeline_controller import resolve_evo_preview

_VISTA_POINTMAP_EMPTY_MESSAGE = (
    "ViSTA-SLAM has not produced a renderable preview artifact for the current keyframe yet."
)
_VISTA_TRAJECTORY_EMPTY_MESSAGE = "ViSTA-SLAM has not accepted a keyframe pose yet, so no live trajectory is available."
_VISTA_PREVIEW_CURRENT_MESSAGE = "Current keyframe artifact."


def render_pipeline_snapshot(snapshot: RunSnapshot, run_service: object) -> None:
    """Render the current pipeline run snapshot."""
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_pipeline_notice(snapshot),
        metrics=_pipeline_metrics(snapshot),
        caption=_pipeline_caption(snapshot),
        body_renderer=lambda: _render_pipeline_tabs(snapshot, run_service),
    )


def _streaming_pointmap_empty_message(snapshot: StreamingRunSnapshot) -> str:
    """Return the current pointmap empty-state message for the streaming page."""
    if snapshot.plan is not None and snapshot.plan.method is MethodId.VISTA:
        return _VISTA_POINTMAP_EMPTY_MESSAGE
    return "No pointmap preview is available for the current frame."


def _streaming_trajectory_empty_message(snapshot: StreamingRunSnapshot) -> str:
    """Return the current trajectory empty-state message for the streaming page."""
    if snapshot.plan is not None and snapshot.plan.method is MethodId.VISTA:
        return _VISTA_TRAJECTORY_EMPTY_MESSAGE
    return "The selected SLAM backend has not produced any trajectory points yet."


def _pipeline_metrics(snapshot: RunSnapshot) -> tuple[LiveMetric, ...]:
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


def _pipeline_caption(snapshot: RunSnapshot) -> str | None:
    if snapshot.plan is None:
        return None
    return (
        f"Run Id: `{snapshot.plan.run_id}` · Artifact Root: `{snapshot.plan.artifact_root}`"
        f" · Method: {snapshot.plan.method.display_name}"
    )


def _render_pipeline_tabs(snapshot: RunSnapshot, run_service: object) -> None:
    if _is_offline_pipeline_run(snapshot):
        st.caption("Offline runs skip the live replay panels and focus on stage progress plus persisted outputs.")
        tabs = st.tabs(["Plan", "Artifacts"])
        with tabs[0]:
            _render_pipeline_plan_tab(snapshot, run_service)
        with tabs[1]:
            _render_pipeline_artifacts_tab(snapshot)
        return

    if not isinstance(snapshot, StreamingRunSnapshot):
        st.info("Streaming telemetry is not available for this run.")
        return
    packet = snapshot.latest_packet
    tabs = st.tabs(["Frames", "Trajectory", "Plan", "Artifacts"])
    with tabs[0]:
        if packet is None:
            st.info("No frame has been processed yet.")
        else:
            frame_image = run_service.read_array(snapshot.latest_frame)
            pointmap_preview = run_service.read_array(snapshot.latest_preview)
            preview_left, preview_right = st.columns(2, gap="large")
            with preview_left:
                st.markdown("**RGB Frame**")
                if frame_image is None:
                    st.info("The latest frame payload is not available in the local handle cache anymore.")
                else:
                    render_live_image(frame_image, channels="RGB", clamp=True, width="stretch")
            with preview_right:
                st.markdown("**ViSTA Preview Artifact**")
                if pointmap_preview is None:
                    st.info(_streaming_pointmap_empty_message(snapshot))
                else:
                    render_live_image(pointmap_preview, clamp=True, width="stretch")
                    preview_status_message = _preview_status_message(snapshot)
                    if preview_status_message is not None:
                        st.caption(preview_status_message)
            details_left, details_right = st.columns((1.0, 1.0), gap="large")
            with details_left:
                st.markdown("**Latest Backend Event**")
                if snapshot.latest_backend_event is None:
                    st.info("No SLAM update is available yet.")
                else:
                    st.json(BaseConfig.to_jsonable(snapshot.latest_backend_event), expanded=False)
            with details_right:
                st.markdown("**Frame Metadata**")
                st.json(
                    {
                        "seq": packet.seq,
                        "timestamp_ns": packet.timestamp_ns,
                        "provenance": packet.provenance.compact_payload(),
                    },
                    expanded=False,
                )
                if snapshot.latest_backend_event is not None:
                    intrinsics_payload = snapshot.latest_backend_event.get("camera_intrinsics")
                    st.markdown("**Camera Intrinsics**")
                    render_camera_intrinsics(
                        intrinsics=None if intrinsics_payload is None else intrinsics_payload,
                        missing_message="Camera intrinsics are not available for the current packet.",
                    )
    with tabs[1]:
        render_live_trajectory(
            positions_xyz=np.asarray(snapshot.trajectory_positions_xyz, dtype=np.float64).reshape(-1, 3),
            timestamps_s=(
                None
                if len(snapshot.trajectory_timestamps_s) == 0
                else np.asarray(snapshot.trajectory_timestamps_s, dtype=np.float64)
            ),
            empty_message=_streaming_trajectory_empty_message(snapshot),
        )
        st.markdown("**Evo APE Colormap**")
        show_evo_preview = st.toggle(
            "Enable evo APE preview",
            value=False,
            key="pipeline_show_evo_preview",
        )
        if not show_evo_preview:
            st.caption("Enable the toggle to run explicit evo APE preview for the current demo slice.")
        else:
            evo_preview, evo_error = resolve_evo_preview(snapshot)
            if evo_error is not None:
                st.warning(evo_error)
            elif evo_preview is None:
                st.info(
                    "Complete one demo run with a reference trajectory to render the evo APE colormap for this slice."
                )
            else:
                st.plotly_chart(
                    build_evo_ape_colormap_figure(
                        reference=evo_preview.reference,
                        estimate=evo_preview.estimate,
                        error_series=evo_preview.error_series,
                    ),
                    width="stretch",
                )
                st.caption(
                    f"Matched pairs: `{len(evo_preview.error_series.values)}` · RMSE: `{evo_preview.stats.rmse:.4f} m`"
                )
    with tabs[2]:
        _render_pipeline_plan_tab(snapshot, run_service)
    with tabs[3]:
        _render_pipeline_artifacts_tab(snapshot)


def _render_pipeline_plan_tab(snapshot: RunSnapshot, run_service: object) -> None:
    if snapshot.plan is None:
        st.info("Start a run to inspect the generated plan and execution records.")
        return

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Planned Stages**")
        st.dataframe(snapshot.plan.stage_rows(), hide_index=True, width="stretch")
    with right:
        st.markdown("**Stage Manifests**")
        if snapshot.stage_manifests:
            st.dataframe(StageManifest.table_rows(snapshot.stage_manifests), hide_index=True, width="stretch")
        else:
            st.info("Stage manifests will appear once the run starts writing outputs.")
        st.markdown("**Recent Events**")
        events = run_service.tail_events(limit=10)
        if not events:
            st.info("Recent events will appear once the run starts.")
        else:
            st.json(
                [
                    {
                        "event_id": event.event_id,
                        "kind": event.kind,
                        "tier": event.tier.value,
                    }
                    for event in events
                ],
                expanded=False,
            )


def _render_pipeline_artifacts_tab(snapshot: RunSnapshot) -> None:
    if snapshot.sequence_manifest is None and snapshot.slam is None and snapshot.summary is None:
        st.info("Run the demo to inspect the materialized manifest, SLAM artifacts, and run summary.")
        return

    left, right = st.columns(2, gap="large")
    with left:
        if snapshot.sequence_manifest is not None:
            st.markdown("**Sequence Manifest**")
            st.code(
                json.dumps(snapshot.sequence_manifest.model_dump(mode="json"), indent=2, sort_keys=True),
                language="json",
            )
        if snapshot.summary is not None:
            st.markdown("**Run Summary**")
            st.code(
                json.dumps(snapshot.summary.model_dump(mode="json"), indent=2, sort_keys=True),
                language="json",
            )
    with right:
        if snapshot.slam is not None:
            st.markdown("**SLAM Artifacts**")
            st.code(
                json.dumps(snapshot.slam.model_dump(mode="json"), indent=2, sort_keys=True),
                language="json",
            )


def _is_offline_pipeline_run(snapshot: RunSnapshot) -> bool:
    return snapshot.plan is not None and snapshot.plan.mode is PipelineMode.OFFLINE


def _render_pipeline_notice(snapshot: RunSnapshot) -> None:
    match snapshot.state:
        case RunState.IDLE:
            st.info(
                "Select a request template, configure the supported source and stages, then start the pipeline demo."
            )
        case RunState.PREPARING:
            st.info("Preparing the sequence manifest and starting the selected SLAM backend.")
        case RunState.RUNNING:
            if _is_offline_pipeline_run(snapshot):
                st.success("Processing the bounded offline slice and materializing artifacts.")
            else:
                st.success("Processing frames through the selected SLAM backend.")
        case RunState.COMPLETED:
            if _is_offline_pipeline_run(snapshot):
                st.success("The bounded offline demo finished and wrote artifacts.")
            else:
                st.success("The bounded demo finished and wrote SLAM artifacts.")
        case RunState.STOPPED:
            if _is_offline_pipeline_run(snapshot):
                st.warning("The offline demo stopped. The written artifacts remain visible below.")
            else:
                st.warning("The demo stopped. The last frame, trajectory, and written artifacts remain visible below.")
        case RunState.FAILED:
            st.error(snapshot.error_message or "The pipeline demo failed.")


def _preview_status_message(snapshot: StreamingRunSnapshot) -> str | None:
    """Return the retained-preview status line for the current streaming snapshot."""
    if snapshot.latest_preview is None:
        return None
    return _VISTA_PREVIEW_CURRENT_MESSAGE


__all__ = ["render_pipeline_snapshot"]
