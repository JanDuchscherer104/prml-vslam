"""Streamlit page for the runnable ADVIO pipeline demo."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunPlan, StageManifest

from ..camera_display import format_camera_intrinsics_latex
from ..pipeline_controller import (
    PipelineDemoFormData,
    handle_pipeline_demo_action,
    sync_pipeline_demo_state,
)
from ..pipeline_runtime import PipelineDemoSnapshot, PipelineDemoState
from ..plotting import build_live_trajectory_figure
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the interactive ADVIO replay demo."""
    render_page_intro(
        eyebrow="Streaming Surface",
        title="Pipeline Demo",
        body=(
            "Run the bounded ADVIO replay demo through the repository-local mock tracker "
            "and monitor frames, trajectory, planned stages, and written artifacts."
        ),
    )
    sync_pipeline_demo_state(context)
    statuses = context.advio_service.local_scene_statuses()
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("ADVIO Replay Demo")
        st.caption(
            "Use one replay-ready ADVIO scene as a bounded offline or looped streaming session for the current pipeline demo."
        )
        if not previewable_ids:
            st.info(
                "Download the ADVIO streaming bundle for at least one scene to unlock the interactive pipeline demo."
            )
            return
        page_state = context.state.pipeline
        selected_sequence_id = (
            page_state.sequence_id if page_state.sequence_id in previewable_ids else previewable_ids[0]
        )
        with st.form("pipeline_demo_form", border=False):
            selected_sequence_id = st.selectbox(
                "ADVIO Scene",
                options=previewable_ids,
                index=previewable_ids.index(selected_sequence_id),
                format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
            )
            left, right = st.columns(2, gap="large")
            with left:
                mode = st.selectbox(
                    "Mode",
                    options=list(PipelineMode),
                    index=list(PipelineMode).index(page_state.mode),
                    format_func=_pipeline_mode_label,
                )
                method = st.selectbox(
                    "Mock Method",
                    options=list(MethodId),
                    index=list(MethodId).index(page_state.method),
                    format_func=lambda item: item.display_name,
                )
            with right:
                pose_source = st.selectbox(
                    "Pose Source",
                    options=list(AdvioPoseSource),
                    index=list(AdvioPoseSource).index(page_state.pose_source),
                    format_func=_pose_source_label,
                )
                respect_video_rotation = st.toggle(
                    "Respect video rotation metadata",
                    value=page_state.respect_video_rotation,
                )
            start_requested = st.form_submit_button(
                "Start run" if not page_state.is_running else "Restart run",
                type="primary",
                use_container_width=True,
            )
        stop_requested = st.button("Stop run", disabled=not page_state.is_running, use_container_width=True)
        error_message = handle_pipeline_demo_action(
            context,
            PipelineDemoFormData(
                sequence_id=selected_sequence_id,
                mode=mode,
                method=method,
                pose_source=pose_source,
                respect_video_rotation=respect_video_rotation,
                start_requested=start_requested,
                stop_requested=stop_requested,
            ),
        )
        if error_message:
            st.error(error_message)

        @st.fragment(run_every=0.2 if context.state.pipeline.is_running else None)
        def _render_fragment() -> None:
            _render_pipeline_demo_snapshot(sync_pipeline_demo_state(context))

        _render_fragment()


def _render_pipeline_demo_snapshot(snapshot: PipelineDemoSnapshot) -> None:
    _render_pipeline_demo_notice(snapshot)
    metrics = (
        ("Status", snapshot.state.value.upper()),
        ("Mode", "Idle" if snapshot.mode is None else _pipeline_mode_label(snapshot.mode)),
        ("Received Frames", str(snapshot.received_frames)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Map Points", str(snapshot.num_map_points)),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, value)
    if snapshot.plan is not None:
        st.caption(
            f"Run Id: `{snapshot.plan.run_id}` · Artifact Root: `{snapshot.plan.artifact_root}` · Method: {snapshot.plan.method.display_name}"
        )
    packet = snapshot.latest_packet
    tabs = st.tabs(["Frames", "Trajectory", "Plan", "Artifacts"])
    with tabs[0]:
        if packet is None:
            st.info("No frame has been processed yet.")
        else:
            left, right = st.columns((1.1, 0.9), gap="large")
            with left:
                st.markdown("**RGB Frame**")
                st.image(packet.rgb, channels="RGB", clamp=True)
            with right:
                st.markdown("**Tracking Update**")
                if snapshot.latest_update is None:
                    st.info("No tracking update is available yet.")
                else:
                    st.json(snapshot.latest_update.model_dump(mode="json"), expanded=False)
                st.markdown("**Frame Metadata**")
                st.json(
                    {
                        "seq": packet.seq,
                        "timestamp_ns": packet.timestamp_ns,
                        "metadata": packet.metadata,
                    },
                    expanded=False,
                )
                st.markdown("**Camera Intrinsics**")
                if packet.intrinsics is None:
                    st.info("Camera intrinsics are not available for the current packet.")
                else:
                    st.latex(
                        format_camera_intrinsics_latex(
                            fx=packet.intrinsics.fx,
                            fy=packet.intrinsics.fy,
                            cx=packet.intrinsics.cx,
                            cy=packet.intrinsics.cy,
                        )
                    )
    with tabs[1]:
        if len(snapshot.trajectory_positions_xyz) == 0:
            st.info("The mock tracker has not produced any trajectory points yet.")
        else:
            st.plotly_chart(
                build_live_trajectory_figure(
                    snapshot.trajectory_positions_xyz,
                    snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
                ),
                width="stretch",
            )
    with tabs[2]:
        if snapshot.plan is None:
            st.info("Start a run to inspect the generated plan and execution records.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown("**Planned Stages**")
                st.dataframe(_stage_rows(snapshot.plan), hide_index=True, width="stretch")
            with right:
                st.markdown("**Stage Manifests**")
                if snapshot.stage_manifests:
                    st.dataframe(_stage_manifest_rows(snapshot.stage_manifests), hide_index=True, width="stretch")
                else:
                    st.info("Stage manifests will appear once the run starts writing outputs.")
    with tabs[3]:
        if snapshot.sequence_manifest is None and snapshot.tracking is None and snapshot.summary is None:
            st.info("Run the demo to inspect the materialized manifest, tracking artifacts, and run summary.")
        else:
            left, right = st.columns(2, gap="large")
            with left:
                if snapshot.sequence_manifest is not None:
                    st.markdown("**Sequence Manifest**")
                    st.code(_json_dump(snapshot.sequence_manifest.model_dump(mode="json")), language="json")
                if snapshot.summary is not None:
                    st.markdown("**Run Summary**")
                    st.code(_json_dump(snapshot.summary.model_dump(mode="json")), language="json")
            with right:
                if snapshot.tracking is not None:
                    st.markdown("**Tracking Artifacts**")
                    st.code(_json_dump(snapshot.tracking.model_dump(mode="json")), language="json")


def _render_pipeline_demo_notice(snapshot: PipelineDemoSnapshot) -> None:
    match snapshot.state:
        case PipelineDemoState.IDLE:
            st.info("Select a replay-ready ADVIO scene and start the pipeline demo.")
        case PipelineDemoState.CONNECTING:
            st.info("Preparing the sequence manifest and starting the mock tracking runtime.")
        case PipelineDemoState.RUNNING:
            st.success("Processing ADVIO frames through the mock tracking runtime.")
        case PipelineDemoState.COMPLETED:
            st.success("The offline demo finished and wrote mock tracking artifacts.")
        case PipelineDemoState.STOPPED:
            st.warning("The demo stopped. The last frame, trajectory, and written artifacts remain visible below.")
        case PipelineDemoState.FAILED:
            st.error(snapshot.error_message or "The pipeline demo failed.")


def _pipeline_mode_label(mode: PipelineMode) -> str:
    return {
        PipelineMode.OFFLINE: "Offline (single pass)",
        PipelineMode.STREAMING: "Streaming (looped replay)",
    }[mode]


def _pose_source_label(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "Ground Truth",
        AdvioPoseSource.ARCORE: "ARCore",
        AdvioPoseSource.ARKIT: "ARKit",
        AdvioPoseSource.NONE: "No Pose Overlay",
    }[pose_source]


def _stage_rows(plan: RunPlan) -> list[dict[str, str]]:
    return [
        {
            "Stage": stage.title,
            "Id": stage.id.value,
            "Outputs": ", ".join(path.name for path in stage.outputs),
        }
        for stage in plan.stages
    ]


def _stage_manifest_rows(stage_manifests: list[StageManifest]) -> list[dict[str, str]]:
    return [
        {
            "Stage": manifest.stage_id.value,
            "Status": manifest.status.value,
            "Config Hash": manifest.config_hash,
            "Outputs": ", ".join(path.name for path in manifest.output_paths.values()),
        }
        for manifest in stage_manifests
    ]


def _json_dump(payload: object) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


__all__ = ["render"]
