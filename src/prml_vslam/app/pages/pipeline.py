"""Streamlit page for the runnable ADVIO pipeline demo."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.pipeline.contracts.runtime import RunState

from ..live_session import live_poll_interval, render_live_action_slot, render_live_fragment, rerun_after_action
from ..pipeline_controller import (
    action_from_page_state,
    build_pipeline_snapshot_render_model,
    build_preview_plan,
    build_run_config_from_action,
    discover_pipeline_config_paths,
    handle_pipeline_page_action,
    load_pipeline_request,
    pipeline_config_label,
    request_summary_payload,
    request_support_error,
    source_input_error,
    sync_pipeline_page_state_from_template,
)
from ..ui import render_page_intro
from .pipeline_request_editor import render_request_editor
from .pipeline_snapshot_view import render_pipeline_snapshot

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({RunState.PREPARING, RunState.RUNNING})


def render(context: AppContext) -> None:
    """Render the interactive ADVIO replay demo."""
    render_page_intro(
        eyebrow="Streaming Surface",
        title="Pipeline Demo",
        body=(
            "Select a persisted pipeline request template, edit the bounded in-app source and stage settings, "
            "then run the current pipeline slice and inspect frames, trajectory, plans, and artifacts."
        ),
    )
    statuses = context.advio_service.local_scene_statuses()
    previewable_statuses = [status for status in statuses if status.replay_ready]
    snapshot = context.run_service.snapshot()
    is_active = snapshot.state in _ACTIVE_SESSION_STATES
    with st.container(border=True):
        st.subheader("Pipeline Request Editor")
        st.caption(
            "Use a TOML request as the starting template, then configure the bounded app-supported source and stage "
            "settings before launching the current demo slice."
        )
        config_paths = discover_pipeline_config_paths(context.path_config)
        if not config_paths:
            st.info("Persist at least one pipeline request TOML under `.configs/pipelines/` to unlock this demo.")
            return
        page_state = context.state.pipeline
        selected_config_path = page_state.config_path if page_state.config_path in config_paths else config_paths[0]
        selected_config_path = st.selectbox(
            "Pipeline Config",
            options=config_paths,
            index=config_paths.index(selected_config_path),
            format_func=lambda config_path: pipeline_config_label(context.path_config, config_path),
        )
        template_request, template_error = load_pipeline_request(context.path_config, selected_config_path)
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

        preview_left, preview_right = st.columns(2, gap="large")
        with preview_left:
            st.markdown("**Resolved Request**")
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
            render_model = build_pipeline_snapshot_render_model(
                current_snapshot,
                context.run_service,
                method=context.state.pipeline.method,
                show_evo_preview=bool(st.session_state.get("pipeline_show_evo_preview", False)),
            )
            render_pipeline_snapshot(render_model)

        render_live_fragment(
            run_every=live_poll_interval(is_active=snapshot.state in _ACTIVE_SESSION_STATES, interval_seconds=0.2),
            render_body=_render_pipeline_snapshot_body,
        )


__all__ = ["render"]
