"""Rendering helpers for the Pipeline page run snapshot."""

from __future__ import annotations

import streamlit as st

from prml_vslam.app.models import PipelineTelemetryViewMode
from prml_vslam.plotting import build_evo_ape_colormap_figure, build_stage_telemetry_figure

from ..live_session import (
    render_camera_intrinsics,
    render_live_image,
    render_live_session_shell,
    render_live_trajectory,
)
from ..pipeline_controller import PipelineSnapshotRenderModel


def render_pipeline_snapshot(model: PipelineSnapshotRenderModel) -> None:
    """Render the current pipeline run snapshot."""
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_pipeline_notice(model),
        metrics=model["metrics"],
        caption=model["caption"],
        body_renderer=lambda: _render_pipeline_tabs(model),
    )


def _render_pipeline_tabs(model: PipelineSnapshotRenderModel) -> None:
    if model["is_offline"]:
        st.caption("Offline runs skip the live replay panels and focus on stage progress plus persisted outputs.")
        tabs = st.tabs(["Stage Status", "Plan", "Artifacts"])
        with tabs[0]:
            _render_stage_status_tab(model)
        with tabs[1]:
            _render_pipeline_plan_tab(model)
        with tabs[2]:
            _render_pipeline_artifacts_tab(model)
        return

    streaming = model["streaming"]
    if streaming is None:
        tabs = st.tabs(["Stage Status", "Plan", "Artifacts"])
        with tabs[0]:
            _render_stage_status_tab(model)
        with tabs[1]:
            _render_pipeline_plan_tab(model)
        with tabs[2]:
            _render_pipeline_artifacts_tab(model)
        return
    packet_metadata = streaming["packet_metadata"]
    has_frame_data = (
        packet_metadata is not None or streaming["frame_image"] is not None or streaming["preview_image"] is not None
    )
    tabs = st.tabs(["Stage Status", "Frames", "Trajectory", "Plan", "Artifacts"])
    with tabs[0]:
        _render_stage_status_tab(model)
    with tabs[1]:
        if not has_frame_data:
            st.info("No frame has been processed yet.")
        else:
            preview_left, preview_right = st.columns(2, gap="large")
            with preview_left:
                st.markdown(f"**{streaming['frame_panel_title']}**")
                if streaming["frame_image"] is None:
                    st.info("The latest frame payload is not available in the local handle cache anymore.")
                else:
                    render_live_image(streaming["frame_image"], channels="RGB", clamp=True, width="stretch")
            with preview_right:
                st.markdown(f"**{streaming['preview_panel_title']}**")
                if streaming["preview_image"] is None:
                    st.info(streaming["preview_empty_message"])
                else:
                    render_live_image(streaming["preview_image"], clamp=True, width="stretch")
                    if streaming["preview_status_message"] is not None:
                        st.caption(streaming["preview_status_message"])
            details_left, details_right = st.columns((1.0, 1.0), gap="large")
            with details_left:
                st.markdown("**Latest Backend Event**")
                if streaming["backend_notice"] is None:
                    st.info(streaming["backend_notice_empty_message"])
                else:
                    st.json(streaming["backend_notice"]["payload"], expanded=False)
            with details_right:
                st.markdown("**Frame Metadata**")
                if packet_metadata is None:
                    st.info("Stage runtime metadata is not available yet.")
                else:
                    st.json(packet_metadata, expanded=False)
                if streaming["backend_notice"] is not None:
                    st.markdown("**Camera Intrinsics**")
                    render_camera_intrinsics(
                        intrinsics=streaming["intrinsics"],
                        missing_message=streaming["intrinsics_missing_message"],
                    )
    with tabs[2]:
        render_live_trajectory(
            positions_xyz=streaming["positions_xyz"],
            timestamps_s=streaming["timestamps_s"],
            empty_message=streaming["trajectory_empty_message"],
        )
        st.markdown("**Evo APE Colormap**")
        st.toggle(
            "Enable evo APE preview",
            value=streaming["show_evo_preview"],
            key="pipeline_show_evo_preview",
        )
        if not streaming["show_evo_preview"]:
            st.caption("Enable the toggle to run explicit evo APE preview for the current slice.")
        else:
            if streaming["evo_error"] is not None:
                st.warning(streaming["evo_error"])
            elif streaming["evo_preview"] is None:
                st.info(streaming["evo_empty_message"])
            else:
                evo_preview = streaming["evo_preview"]
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
    with tabs[3]:
        _render_pipeline_plan_tab(model)
    with tabs[4]:
        _render_pipeline_artifacts_tab(model)


def _render_stage_status_tab(model: PipelineSnapshotRenderModel) -> None:
    if not model["telemetry_visible"]:
        st.info("Stage telemetry is hidden.")
        return
    if not model["stage_status_rows"]:
        st.info("Start a run to inspect stage status.")
        return
    st.dataframe(model["stage_status_rows"], hide_index=True, width="stretch")
    if model["telemetry_view_mode"] is not PipelineTelemetryViewMode.ROLLING:
        return
    telemetry_chart = model["telemetry_chart"]
    if telemetry_chart is None or not telemetry_chart["rows"]:
        empty_message = (
            "No rolling telemetry samples are available yet."
            if telemetry_chart is None
            else telemetry_chart["empty_message"]
        )
        st.info(empty_message)
        return
    st.plotly_chart(
        build_stage_telemetry_figure(
            rows=telemetry_chart["rows"],
            metric_label=telemetry_chart["metric_label"],
            unit_label=telemetry_chart["unit_label"],
        ),
        width="stretch",
    )


def _render_pipeline_plan_tab(model: PipelineSnapshotRenderModel) -> None:
    if not model["plan_rows"]:
        st.info("Start a run to inspect the generated plan and execution records.")
        return

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**Planned Stages**")
        st.dataframe(model["plan_rows"], hide_index=True, width="stretch")
    with right:
        st.markdown("**Stage Outcomes**")
        if model["stage_outcome_rows"]:
            st.dataframe(model["stage_outcome_rows"], hide_index=True, width="stretch")
        else:
            st.info("Stage outcomes will appear once the run starts writing outputs.")
        st.markdown("**Recent Events**")
        if not model["recent_events"]:
            st.info("Recent events will appear once the run starts.")
        else:
            st.json(model["recent_events"], expanded=False)


def _render_pipeline_artifacts_tab(model: PipelineSnapshotRenderModel) -> None:
    if (
        model["stage_outcomes_json"] is None
        and model["artifacts_json"] is None
        and model["stage_runtime_status_json"] is None
    ):
        st.info("Run the pipeline to inspect stage outcomes, stage runtime status, and materialized artifacts.")
        return

    left, right = st.columns(2, gap="large")
    with left:
        if model["stage_outcomes_json"] is not None:
            st.markdown("**Stage Outcomes**")
            st.code(model["stage_outcomes_json"], language="json")
        if model["stage_runtime_status_json"] is not None:
            st.markdown("**Stage Runtime Status**")
            st.code(model["stage_runtime_status_json"], language="json")
    with right:
        if model["artifacts_json"] is not None:
            st.markdown("**Artifacts**")
            st.code(model["artifacts_json"], language="json")


def _render_pipeline_notice(model: PipelineSnapshotRenderModel) -> None:
    notice = model["notice"]
    match notice["level"]:
        case "info":
            st.info(notice["message"])
        case "success":
            st.success(notice["message"])
        case "warning":
            st.warning(notice["message"])
        case "error":
            st.error(notice["message"])


__all__ = ["render_pipeline_snapshot"]
