"""Streamlit page for the Pipeline run console."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.pipeline.contracts.runtime import RunState
from prml_vslam.pipeline.contracts.stages import StageKey

from ..live_session import live_poll_interval, render_live_action_slot, render_live_fragment, rerun_after_action
from ..models import PipelineTelemetryMetricId, PipelineTelemetryViewMode
from ..pipeline_controller import (
    build_pipeline_snapshot_render_model,
    build_pipeline_viewer_link_model,
    refreshed_pipeline_telemetry_history,
    telemetry_stage_options,
)
from ..pipeline_controls import (
    action_from_page_state,
    build_preview_plan,
    build_run_config_from_action,
    discover_pipeline_config_paths,
    handle_pipeline_page_action,
    load_pipeline_run_config,
    pipeline_config_label,
    request_summary_payload,
    request_support_error,
    source_input_error,
    sync_pipeline_page_state_from_template,
)
from ..state import save_model_updates
from ..ui import render_page_intro
from .pipeline_request_editor import render_request_editor
from .pipeline_snapshot_view import render_pipeline_snapshot

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts.runtime import RunSnapshot

    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({RunState.PREPARING, RunState.RUNNING})


def render(context: AppContext) -> None:
    """Render the interactive Pipeline run console."""
    render_page_intro(
        eyebrow="Run Console",
        title="Pipeline Run Console",
        body=(
            "Launch supported pipeline slices from a persisted request template, then monitor stage status, "
            "live previews, trajectory output, and artifacts."
        ),
    )
    statuses = context.advio_service.local_scene_statuses()
    previewable_statuses = [status for status in statuses if status.replay_ready]
    snapshot = context.run_service.snapshot()
    is_active = snapshot.state in _ACTIVE_SESSION_STATES
    with st.container():
        st.subheader("Run Configuration")
        config_paths = discover_pipeline_config_paths(context.path_config)
        if not config_paths:
            st.info("Persist at least one pipeline request TOML under `.configs/pipelines/` to unlock this console.")
            return
        page_state = context.state.pipeline
        selected_config_path = page_state.config_path if page_state.config_path in config_paths else config_paths[0]
        selected_config_path = st.selectbox(
            "Pipeline Config",
            options=config_paths,
            index=config_paths.index(selected_config_path),
            format_func=lambda config_path: pipeline_config_label(context.path_config, config_path),
        )
        template_request, template_error = load_pipeline_run_config(context.path_config, selected_config_path)
        if template_request is not None:
            sync_pipeline_page_state_from_template(
                context=context,
                config_path=selected_config_path,
                run_config=template_request,
                statuses=statuses,
            )
            page_state = context.state.pipeline

        if template_request is None:
            st.warning(template_error or "Failed to load the selected pipeline config.")
            action = action_from_page_state(page_state, selected_config_path)
            identity_input_error = None
            source_error = source_input_error(action)
        else:
            action, identity_input_error, source_error = render_request_editor(
                context=context,
                page_state=page_state,
                selected_config_path=selected_config_path,
                previewable_statuses=previewable_statuses,
            )

        preview_request, preview_error = build_run_config_from_action(context, action)
        preview_plan, preview_plan_error = (
            (None, None) if preview_request is None else build_preview_plan(preview_request, context.path_config)
        )
        support_error = request_support_error(
            request=preview_request,
            plan=preview_plan,
            previewable_statuses=previewable_statuses,
        )
        start_error = support_error or identity_input_error or source_error

        st.subheader("Plan Preview")
        preview_left, preview_right = st.columns(2, gap="large")
        with preview_left:
            st.markdown("**Resolved RunConfig**")
            if preview_request is None:
                st.warning(preview_error or "The current request is invalid.")
            else:
                st.json(request_summary_payload(preview_request), expanded=False)
        with preview_right:
            st.markdown("**Planned Stages**")
            if preview_plan is None:
                st.warning(preview_plan_error or "The current request could not be planned.")
            else:
                st.dataframe(preview_plan.stage_rows(), hide_index=True, width="stretch")
            if start_error is not None:
                st.warning(start_error)
        start_requested, stop_requested = render_live_action_slot(
            is_active=is_active,
            start_label="Start run",
            stop_label="Stop run",
            start_disabled=preview_request is None or start_error is not None,
        )
        action.start_requested = start_requested
        action.stop_requested = stop_requested
        error_message = handle_pipeline_page_action(
            context=context,
            action=action,
        )
        if rerun_after_action(
            action_requested=action.start_requested or action.stop_requested,
            error_message=error_message,
        ):
            return
        snapshot = context.run_service.snapshot()
        if error_message:
            st.error(error_message)

        def _render_pipeline_snapshot_body() -> None:
            current_snapshot = context.run_service.snapshot()
            _refresh_pipeline_telemetry_state(context, current_snapshot)
            _render_pipeline_telemetry_controls(context, current_snapshot)
            page_state = context.state.pipeline
            render_model = build_pipeline_snapshot_render_model(
                current_snapshot,
                context.run_service,
                method=context.state.pipeline.method,
                show_evo_preview=bool(st.session_state.get("pipeline_show_evo_preview", False)),
                telemetry_history=page_state.telemetry_history,
                telemetry_visible=page_state.telemetry_visible,
                telemetry_view_mode=page_state.telemetry_view_mode,
                telemetry_selected_stage_key=page_state.telemetry_selected_stage_key,
                telemetry_selected_metric=page_state.telemetry_selected_metric,
            )
            render_pipeline_snapshot(render_model)

        render_live_fragment(
            run_every=live_poll_interval(is_active=snapshot.state in _ACTIVE_SESSION_STATES, interval_seconds=0.2),
            render_body=_render_pipeline_snapshot_body,
        )


def _refresh_pipeline_telemetry_state(context: AppContext, snapshot: RunSnapshot) -> None:
    run_id, telemetry_history, changed = refreshed_pipeline_telemetry_history(context.state.pipeline, snapshot)
    if not changed:
        return
    save_model_updates(
        context.store,
        context.state,
        context.state.pipeline,
        telemetry_history_run_id=run_id,
        telemetry_history=telemetry_history,
    )


def _render_pipeline_telemetry_controls(context: AppContext, snapshot: RunSnapshot) -> None:
    page_state = context.state.pipeline
    st.subheader("Run Status")
    _render_pipeline_viewer_link(
        connect_live_viewer=page_state.connect_live_viewer,
        grpc_url=page_state.grpc_url,
    )
    telemetry_visible = st.toggle(
        "Show Stage Telemetry",
        value=page_state.telemetry_visible,
        key="pipeline_telemetry_visible",
    )
    telemetry_view_mode = page_state.telemetry_view_mode
    telemetry_selected_stage_key = page_state.telemetry_selected_stage_key
    telemetry_selected_metric = page_state.telemetry_selected_metric
    if telemetry_visible:
        left, middle, right = st.columns((0.8, 1.1, 1.1), gap="small")
        with left:
            selected_mode = st.segmented_control(
                "Telemetry Mode",
                options=list(PipelineTelemetryViewMode),
                default=page_state.telemetry_view_mode,
                format_func=lambda item: item.label,
                selection_mode="single",
                width="stretch",
                key="pipeline_telemetry_mode",
            )
            telemetry_view_mode = page_state.telemetry_view_mode if selected_mode is None else selected_mode
        stage_options = telemetry_stage_options(snapshot, page_state.telemetry_history)
        with middle:
            telemetry_selected_stage_key = _render_telemetry_stage_selector(
                stage_options,
                selected_stage_key=page_state.telemetry_selected_stage_key,
            )
        with right:
            telemetry_selected_metric = st.selectbox(
                "Rolling Metric",
                options=list(PipelineTelemetryMetricId),
                index=list(PipelineTelemetryMetricId).index(page_state.telemetry_selected_metric),
                format_func=lambda item: item.label,
                disabled=telemetry_view_mode is not PipelineTelemetryViewMode.ROLLING,
                key="pipeline_telemetry_metric",
            )
    save_model_updates(
        context.store,
        context.state,
        page_state,
        telemetry_visible=telemetry_visible,
        telemetry_view_mode=telemetry_view_mode,
        telemetry_selected_stage_key=telemetry_selected_stage_key,
        telemetry_selected_metric=telemetry_selected_metric,
    )


def _render_pipeline_viewer_link(*, connect_live_viewer: bool, grpc_url: str) -> None:
    viewer_link = build_pipeline_viewer_link_model(
        connect_live_viewer=connect_live_viewer,
        grpc_url=grpc_url,
    )
    if viewer_link.web_url is None:
        st.caption(viewer_link.status_message)
        return
    left, right = st.columns((0.4, 1.6), gap="small")
    with left:
        st.link_button("Open Rerun Viewer", viewer_link.web_url, width="stretch")
    with right:
        st.caption(f"{viewer_link.status_message} Endpoint: `{viewer_link.grpc_url}`")


def _render_telemetry_stage_selector(
    stage_options: list[StageKey],
    *,
    selected_stage_key: StageKey | None,
) -> StageKey | None:
    if not stage_options:
        st.selectbox(
            "Rolling Stage",
            options=["No stages"],
            index=0,
            disabled=True,
            key="pipeline_telemetry_stage_empty",
        )
        return None
    resolved_stage_key = selected_stage_key if selected_stage_key in stage_options else stage_options[0]
    return st.selectbox(
        "Rolling Stage",
        options=stage_options,
        index=stage_options.index(resolved_stage_key),
        format_func=lambda item: item.label,
        key="pipeline_telemetry_stage",
    )


__all__ = ["render"]
