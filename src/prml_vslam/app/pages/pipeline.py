"""Streamlit page for the runnable ADVIO pipeline demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.state import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.plotting import build_evo_ape_colormap_figure
from prml_vslam.plotting.pipeline import preview_image_from_update

from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_camera_intrinsics,
    render_live_action_slot,
    render_live_fragment,
    render_live_image,
    render_live_session_shell,
    render_live_trajectory,
    rerun_after_action,
)
from ..models import PipelinePageState, PipelineSourceId
from ..pipeline_controller import (
    PipelinePageAction,
    action_from_page_state,
    build_preview_plan,
    build_request_from_action,
    discover_pipeline_config_paths,
    handle_pipeline_page_action,
    load_pipeline_request,
    parse_optional_int,
    pipeline_config_label,
    request_summary_payload,
    request_support_error,
    resolve_evo_preview,
    source_input_error,
    sync_pipeline_page_state_from_template,
)
from ..record3d_controls import (
    render_record3d_transport_controls,
    render_record3d_transport_details,
)
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({RunState.PREPARING, RunState.RUNNING})
_VISTA_POINTMAP_EMPTY_MESSAGE = (
    "ViSTA-SLAM has not produced a renderable preview artifact for the current keyframe yet."
)
_VISTA_TRAJECTORY_EMPTY_MESSAGE = "ViSTA-SLAM has not accepted a keyframe pose yet, so no live trajectory is available."
_VISTA_PREVIEW_CURRENT_MESSAGE = "Current keyframe artifact."


def _pipeline_method_help(method: MethodId) -> str:
    """Explain the current streaming-preview semantics for the selected method."""
    if method is MethodId.MOCK:
        return "Repository-local mock backend that emits live pose and pointmap telemetry for UI validation."
    if method is MethodId.MAST3R:
        return (
            "MASt3R-SLAM backend. Offline runs produce real trajectory and dense point cloud artifacts; "
            "streaming runs show incremental keyframe poses and live pointmap previews."
        )
    return (
        "Real ViSTA-SLAM backend. Offline runs produce real artifacts; streaming runs show packet FPS, accepted "
        "keyframe FPS, and live previews only when the backend produces a new keyframe artifact."
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
                request=template_request,
                statuses=statuses,
            )
            page_state = context.state.pipeline

        if template_request is None:
            st.warning(template_error or "Failed to load the selected pipeline config.")
            action = action_from_page_state(page_state, selected_config_path)
            identity_input_error = None
            source_error = source_input_error(action)
        else:
            action, identity_input_error, source_error = _render_request_editor(
                context=context,
                page_state=page_state,
                selected_config_path=selected_config_path,
                previewable_statuses=previewable_statuses,
            )

        preview_request, preview_error = build_request_from_action(context, action)
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
        render_live_fragment(
            run_every=live_poll_interval(is_active=snapshot.state in _ACTIVE_SESSION_STATES, interval_seconds=0.2),
            render_body=lambda: _render_pipeline_snapshot(context.run_service.snapshot()),
        )


def _render_request_editor(
    *,
    context: AppContext,
    page_state: PipelinePageState,
    selected_config_path: Path,
    previewable_statuses: list[object],
) -> tuple[PipelinePageAction, str | None, str | None]:
    source_options = [PipelineSourceId.ADVIO, PipelineSourceId.RECORD3D]
    source_kind = st.segmented_control(
        "Source",
        options=source_options,
        default=page_state.source_kind,
        format_func=lambda item: item.label,
        selection_mode="single",
        width="stretch",
        key="pipeline_source_selector",
    )
    resolved_source_kind = page_state.source_kind if source_kind is None else source_kind
    (
        experiment_name,
        mode,
        method,
        slam_max_frames,
        identity_input_error,
    ) = _render_request_identity_controls(
        page_state=page_state,
        source_kind=resolved_source_kind,
    )
    (
        advio_sequence_id,
        record3d_transport,
        record3d_usb_device_index,
        record3d_wifi_device_address,
        record3d_persist_capture,
        pose_source,
        respect_video_rotation,
        source_input_error,
    ) = _render_source_settings(
        context=context,
        page_state=page_state,
        source_kind=resolved_source_kind,
        previewable_statuses=previewable_statuses,
    )
    (
        emit_sparse_points,
        emit_dense_points,
        reference_enabled,
        trajectory_eval_enabled,
        evaluate_cloud,
        evaluate_efficiency,
        connect_live_viewer,
        export_viewer_rrd,
    ) = _render_stage_settings(page_state)
    return (
        PipelinePageAction.model_validate(
            page_state.model_dump(mode="python")
            | {
                "config_path": selected_config_path,
                "experiment_name": experiment_name,
                "source_kind": resolved_source_kind,
                "advio_sequence_id": advio_sequence_id,
                "mode": mode,
                "method": method,
                "slam_max_frames": slam_max_frames,
                "emit_dense_points": emit_dense_points,
                "emit_sparse_points": emit_sparse_points,
                "reference_enabled": reference_enabled,
                "trajectory_eval_enabled": trajectory_eval_enabled,
                "evaluate_cloud": evaluate_cloud,
                "evaluate_efficiency": evaluate_efficiency,
                "connect_live_viewer": connect_live_viewer,
                "export_viewer_rrd": export_viewer_rrd,
                "record3d_transport": record3d_transport,
                "record3d_usb_device_index": record3d_usb_device_index,
                "record3d_wifi_device_address": record3d_wifi_device_address,
                "record3d_persist_capture": record3d_persist_capture,
                "pose_source": pose_source,
                "respect_video_rotation": respect_video_rotation,
            }
        ),
        identity_input_error,
        source_input_error,
    )


def _render_request_identity_controls(
    *,
    page_state: PipelinePageState,
    source_kind: PipelineSourceId,
) -> tuple[str, PipelineMode, MethodId, int | None, str | None]:
    left, _ = st.columns(2, gap="large")
    with left:
        experiment_name = st.text_input("Experiment Name", value=page_state.experiment_name).strip()
        mode_options = [PipelineMode.STREAMING] if source_kind is PipelineSourceId.RECORD3D else list(PipelineMode)
        default_mode = page_state.mode if page_state.mode in mode_options else mode_options[0]
        mode = st.selectbox(
            "Mode",
            options=mode_options,
            index=mode_options.index(default_mode),
            format_func=lambda item: item.label,
        )
        method = st.selectbox(
            "VSLAM Method",
            options=list(MethodId),
            index=list(MethodId).index(page_state.method),
            format_func=lambda item: item.display_name,
        )
        st.caption(_pipeline_method_help(method))
        slam_max_frames_raw = st.text_input(
            "SLAM Max Frames",
            value="" if page_state.slam_max_frames is None else str(page_state.slam_max_frames),
            placeholder="blank for no limit",
        ).strip()
        slam_max_frames, slam_max_frames_error = parse_optional_int(
            raw_value=slam_max_frames_raw,
            field_label="SLAM Max Frames",
        )
    return experiment_name, mode, method, slam_max_frames, slam_max_frames_error


def _render_source_settings(
    *,
    context: AppContext,
    page_state: PipelinePageState,
    source_kind: PipelineSourceId,
    previewable_statuses: list[object],
) -> tuple[int | None, Record3DTransportId, int, str, bool, AdvioPoseSource, bool, str | None]:
    _, right = st.columns(2, gap="large")
    with right:
        advio_sequence_id = page_state.advio_sequence_id
        record3d_transport = page_state.record3d_transport
        record3d_usb_device_index = page_state.record3d_usb_device_index
        record3d_wifi_device_address = page_state.record3d_wifi_device_address
        record3d_persist_capture = page_state.record3d_persist_capture
        pose_source = page_state.pose_source
        respect_video_rotation = page_state.respect_video_rotation
        source_input_error = None
        if source_kind is PipelineSourceId.ADVIO:
            advio_sequence_id, pose_source, respect_video_rotation = _render_advio_source_settings(
                context=context,
                page_state=page_state,
                previewable_statuses=previewable_statuses,
            )
            source_input_error = None if advio_sequence_id is not None else "Select a replay-ready ADVIO scene."
        else:
            (
                record3d_transport,
                record3d_usb_device_index,
                record3d_wifi_device_address,
                record3d_persist_capture,
                source_input_error,
            ) = _render_record3d_source_settings(page_state=page_state)
    return (
        advio_sequence_id,
        record3d_transport,
        record3d_usb_device_index,
        record3d_wifi_device_address,
        record3d_persist_capture,
        pose_source,
        respect_video_rotation,
        source_input_error,
    )


def _render_advio_source_settings(
    *,
    context: AppContext,
    page_state: PipelinePageState,
    previewable_statuses: list[object],
) -> tuple[int | None, AdvioPoseSource, bool]:
    previewable_ids = [status.scene.sequence_id for status in previewable_statuses]
    if previewable_ids:
        selected_advio_sequence = (
            page_state.advio_sequence_id if page_state.advio_sequence_id in previewable_ids else previewable_ids[0]
        )
        advio_sequence_id = st.selectbox(
            "ADVIO Scene",
            options=previewable_ids,
            index=previewable_ids.index(selected_advio_sequence),
            format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
        )
    else:
        advio_sequence_id = None
        st.info("No replay-ready ADVIO scenes are available.")
    pose_source = st.selectbox(
        "Pose Source",
        options=list(AdvioPoseSource),
        index=list(AdvioPoseSource).index(page_state.pose_source),
        format_func=lambda item: item.label,
    )
    respect_video_rotation = st.toggle(
        "Respect video rotation metadata",
        value=page_state.respect_video_rotation,
    )
    return advio_sequence_id, pose_source, respect_video_rotation


def _render_record3d_source_settings(
    *,
    page_state: PipelinePageState,
) -> tuple[Record3DTransportId, int, str, bool, str | None]:
    selection = render_record3d_transport_controls(
        transport=page_state.record3d_transport,
        usb_device_index=page_state.record3d_usb_device_index,
        wifi_device_address=page_state.record3d_wifi_device_address,
        widget_key_prefix="pipeline_record3d",
    )
    record3d_persist_capture = st.toggle(
        "Persist live capture for downstream offline use",
        value=page_state.record3d_persist_capture,
    )
    render_record3d_transport_details(selection)
    return (
        selection.transport,
        selection.usb_device_index,
        selection.wifi_device_address,
        record3d_persist_capture,
        selection.input_error,
    )


def _render_stage_settings(
    page_state: PipelinePageState,
) -> tuple[bool, bool, bool, bool, bool, bool, bool, bool]:
    stage_left, stage_right = st.columns(2, gap="large")
    with stage_left:
        st.markdown("**SLAM Stage**")
        emit_sparse_points = st.toggle("Emit sparse geometry", value=page_state.emit_sparse_points)
        emit_dense_points = st.toggle("Emit dense geometry", value=page_state.emit_dense_points)
        reference_enabled = st.toggle("Plan reference reconstruction", value=page_state.reference_enabled)

        st.markdown("**Visualization**")
        connect_live_viewer = st.toggle("Connect live Rerun viewer", value=page_state.connect_live_viewer)
        export_viewer_rrd = st.toggle("Export viewer .rrd artifact", value=page_state.export_viewer_rrd)

    with stage_right:
        st.markdown("**Evaluation Stages**")
        trajectory_eval_enabled = st.toggle("Plan trajectory evaluation", value=page_state.trajectory_eval_enabled)
        evaluate_cloud = st.toggle("Plan dense-cloud evaluation", value=page_state.evaluate_cloud)
        evaluate_efficiency = st.toggle("Plan efficiency evaluation", value=page_state.evaluate_efficiency)
    return (
        emit_sparse_points,
        emit_dense_points,
        reference_enabled,
        trajectory_eval_enabled,
        evaluate_cloud,
        evaluate_efficiency,
        connect_live_viewer,
        export_viewer_rrd,
    )


def _render_pipeline_snapshot(snapshot: RunSnapshot) -> None:
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_pipeline_notice(snapshot),
        metrics=_pipeline_metrics(snapshot),
        caption=_pipeline_caption(snapshot),
        body_renderer=lambda: _render_pipeline_tabs(snapshot),
    )


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


def _render_pipeline_tabs(snapshot: RunSnapshot) -> None:
    if _is_offline_pipeline_run(snapshot):
        st.caption("Offline runs skip the live replay panels and focus on stage progress plus persisted outputs.")
        tabs = st.tabs(["Plan", "Artifacts"])
        with tabs[0]:
            _render_pipeline_plan_tab(snapshot)
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
            preview_update = snapshot.latest_preview_update
            pointmap_preview = preview_image_from_update(preview_update)
            preview_left, preview_right = st.columns(2, gap="large")
            with preview_left:
                st.markdown("**RGB Frame**")
                render_live_image(packet.rgb, channels="RGB", clamp=True, width="stretch")
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
                st.markdown("**SLAM Update**")
                if snapshot.latest_slam_update is None:
                    st.info("No SLAM update is available yet.")
                else:
                    st.json(
                        {
                            **snapshot.latest_slam_update.model_dump(
                                mode="json",
                                exclude={"pointmap", "image_rgb", "depth_map", "preview_rgb"},
                            ),
                            "pointmap_shape": None
                            if snapshot.latest_slam_update.pointmap is None
                            else list(snapshot.latest_slam_update.pointmap.shape),
                            "image_shape": None
                            if snapshot.latest_slam_update.image_rgb is None
                            else list(snapshot.latest_slam_update.image_rgb.shape),
                            "depth_shape": None
                            if snapshot.latest_slam_update.depth_map is None
                            else list(snapshot.latest_slam_update.depth_map.shape),
                            "preview_shape": None
                            if snapshot.latest_slam_update.preview_rgb is None
                            else list(snapshot.latest_slam_update.preview_rgb.shape),
                            "accepted_keyframes": snapshot.accepted_keyframes,
                            "keyframe_fps": snapshot.backend_fps,
                        },
                        expanded=False,
                    )
            with details_right:
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
                render_camera_intrinsics(
                    intrinsics=packet.intrinsics,
                    missing_message="Camera intrinsics are not available for the current packet.",
                )
    with tabs[1]:
        render_live_trajectory(
            positions_xyz=snapshot.trajectory_positions_xyz,
            timestamps_s=snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
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
        _render_pipeline_plan_tab(snapshot)
    with tabs[3]:
        _render_pipeline_artifacts_tab(snapshot)


def _render_pipeline_plan_tab(snapshot: RunSnapshot) -> None:
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
    preview_update = snapshot.latest_preview_update
    if preview_update is None:
        return None
    latest_update = snapshot.latest_slam_update
    if latest_update is not None and _updates_share_preview_identity(latest_update, preview_update):
        return _VISTA_PREVIEW_CURRENT_MESSAGE
    keyframe_label = _preview_keyframe_label(preview_update)
    return f"Showing last valid keyframe artifact from {keyframe_label}."


def _updates_share_preview_identity(left: object, right: object) -> bool:
    """Return whether two updates refer to the same preview-bearing keyframe."""
    return (
        getattr(left, "seq", None) == getattr(right, "seq", None)
        and getattr(left, "timestamp_ns", None) == getattr(right, "timestamp_ns", None)
        and getattr(left, "keyframe_index", None) == getattr(right, "keyframe_index", None)
        and preview_image_from_update(left) is not None
    )


def _preview_keyframe_label(update: object) -> str:
    """Return a human-readable keyframe label for one retained preview update."""
    keyframe_index = getattr(update, "keyframe_index", None)
    if keyframe_index is not None:
        return f"keyframe {keyframe_index}"
    seq = getattr(update, "seq", None)
    if seq is not None:
        return f"frame {seq}"
    return "the last available frame"


__all__ = ["render"]
