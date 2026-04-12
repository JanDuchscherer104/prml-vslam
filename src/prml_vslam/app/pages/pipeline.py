"""Streamlit page for the runnable ADVIO pipeline demo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from evo.core import metrics as evo_metrics
from evo.core import sync as evo_sync

from prml_vslam.benchmark import (
    BenchmarkConfig,
    CloudBenchmarkConfig,
    EfficiencyBenchmarkConfig,
    TrajectoryBenchmarkConfig,
)
from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.eval.contracts import ErrorSeries, MetricStats, TrajectorySeries
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStageId
from prml_vslam.pipeline.contracts.provenance import StageManifest
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, Record3DLiveSourceSpec, SlamStageConfig
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState, StreamingRunSnapshot
from prml_vslam.pipeline.demo import load_run_request_toml
from prml_vslam.plotting import build_evo_ape_colormap_figure
from prml_vslam.utils import BaseData, PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.utils.image_utils import normalize_grayscale_image
from prml_vslam.visualization import VisualizationConfig

from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_camera_intrinsics,
    render_live_action_slot,
    render_live_fragment,
    render_live_session_shell,
    render_live_trajectory,
    rerun_after_action,
)
from ..models import PipelinePageState, PipelineSourceId
from ..record3d_controls import (
    record3d_transport_input_error,
    render_record3d_transport_controls,
    render_record3d_transport_details,
)
from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_SESSION_STATES = frozenset({RunState.PREPARING, RunState.RUNNING})
_EVO_ASSOCIATION_MAX_DIFF_S = 0.01
_SUPPORTED_APP_STAGE_IDS = frozenset({RunPlanStageId.INGEST, RunPlanStageId.SLAM, RunPlanStageId.SUMMARY})
_MOCK_METHOD_LABEL = "Mock Preview"
_VISTA_POINTMAP_EMPTY_MESSAGE = (
    "ViSTA-SLAM has not produced a renderable preview artifact for the current keyframe yet."
)
_VISTA_TRAJECTORY_EMPTY_MESSAGE = "ViSTA-SLAM has not accepted a keyframe pose yet, so no live trajectory is available."


class PipelinePageAction(PipelinePageState):
    """Typed action payload for the pipeline page controls."""

    start_requested: bool = False
    """Whether the user requested a new run."""

    stop_requested: bool = False
    """Whether the user requested the current run to stop."""


class PipelineEvoPreview(BaseData):
    """`evo` APE payload rendered by the pipeline-demo trajectory tab."""

    reference: TrajectorySeries
    estimate: TrajectorySeries
    error_series: ErrorSeries
    stats: MetricStats


def _pipeline_method_label(method: MethodId) -> str:
    """Return the app-facing method label used by the bounded pipeline demo."""
    if method is MethodId.MSTR:
        return _MOCK_METHOD_LABEL
    return method.display_name


def _pipeline_method_help(method: MethodId) -> str:
    """Explain the current streaming-preview semantics for the selected method."""
    if method is MethodId.MSTR:
        return "Repository-local mock backend that emits live pose and pointmap telemetry for UI validation."
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
        config_paths = _discover_pipeline_config_paths(context.path_config)
        if not config_paths:
            st.info("Persist at least one pipeline request TOML under `.configs/pipelines/` to unlock this demo.")
            return
        page_state = context.state.pipeline
        selected_config_path = page_state.config_path if page_state.config_path in config_paths else config_paths[0]
        selected_config_path = st.selectbox(
            "Pipeline Config",
            options=config_paths,
            index=config_paths.index(selected_config_path),
            format_func=lambda config_path: _pipeline_config_label(context.path_config, config_path),
        )
        template_request, template_error = _load_pipeline_request(context.path_config, selected_config_path)
        if template_request is not None:
            _sync_pipeline_page_state_from_template(
                context=context,
                config_path=selected_config_path,
                request=template_request,
                statuses=statuses,
            )
            page_state = context.state.pipeline

        if template_request is None:
            st.warning(template_error or "Failed to load the selected pipeline config.")
            action = _action_from_page_state(page_state, selected_config_path)
            identity_input_error = None
            source_input_error = _source_input_error(action)
        else:
            action, identity_input_error, source_input_error = _render_request_editor(
                context=context,
                page_state=page_state,
                selected_config_path=selected_config_path,
                previewable_statuses=previewable_statuses,
            )

        preview_request, preview_error = _build_request_from_action(context, action)
        preview_plan, preview_plan_error = (
            (None, None) if preview_request is None else _build_preview_plan(preview_request, context.path_config)
        )
        support_error = _request_support_error(
            request=preview_request,
            plan=preview_plan,
            previewable_statuses=previewable_statuses,
        )
        start_error = support_error or identity_input_error or source_input_error

        preview_left, preview_right = st.columns(2, gap="large")
        with preview_left:
            st.markdown("**Resolved Request**")
            if preview_request is None:
                st.warning(preview_error or "The current request is invalid.")
            else:
                st.json(_request_summary_payload(preview_request), expanded=False)
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
        error_message = _handle_pipeline_page_action(
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
        slam_config_path,
        identity_input_error,
    ) = _render_request_identity_controls(
        page_state=page_state,
        path_config=context.path_config,
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
        compare_to_arcore,
        evaluate_cloud,
        evaluate_efficiency,
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
                "slam_config_path": slam_config_path,
                "emit_dense_points": emit_dense_points,
                "emit_sparse_points": emit_sparse_points,
                "reference_enabled": reference_enabled,
                "compare_to_arcore": compare_to_arcore,
                "evaluate_cloud": evaluate_cloud,
                "evaluate_efficiency": evaluate_efficiency,
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


def _action_from_page_state(page_state: PipelinePageState, config_path: Path) -> PipelinePageAction:
    return PipelinePageAction.model_validate(page_state.model_dump(mode="python") | {"config_path": config_path})


def _render_request_identity_controls(
    *,
    page_state: PipelinePageState,
    path_config: PathConfig,
    source_kind: PipelineSourceId,
) -> tuple[str, PipelineMode, MethodId, int | None, Path | None, str | None]:
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
            "Method",
            options=list(MethodId),
            index=list(MethodId).index(page_state.method),
            format_func=_pipeline_method_label,
        )
        st.caption(_pipeline_method_help(method))
        slam_max_frames_raw = st.text_input(
            "SLAM Max Frames",
            value="" if page_state.slam_max_frames is None else str(page_state.slam_max_frames),
            placeholder="blank for no limit",
        ).strip()
        slam_max_frames, slam_max_frames_error = _parse_optional_int(
            raw_value=slam_max_frames_raw,
            field_label="SLAM Max Frames",
        )
        slam_config_path = _parse_optional_repo_path(
            path_config,
            st.text_input(
                "SLAM Config Path",
                value=_display_repo_relative_path(path_config, page_state.slam_config_path),
                placeholder=".configs/methods/vista/demo.toml",
            ).strip(),
        )
    return experiment_name, mode, method, slam_max_frames, slam_config_path, slam_max_frames_error


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
) -> tuple[bool, bool, bool, bool, bool, bool]:
    stage_left, stage_right = st.columns(2, gap="large")
    with stage_left:
        st.markdown("**SLAM Stage**")
        emit_sparse_points = st.toggle("Emit sparse geometry", value=page_state.emit_sparse_points)
        emit_dense_points = st.toggle("Emit dense geometry", value=page_state.emit_dense_points)
        reference_enabled = st.toggle("Plan reference reconstruction", value=page_state.reference_enabled)
    with stage_right:
        st.markdown("**Evaluation Stages**")
        compare_to_arcore = st.toggle("Plan trajectory evaluation", value=page_state.compare_to_arcore)
        evaluate_cloud = st.toggle("Plan dense-cloud evaluation", value=page_state.evaluate_cloud)
        evaluate_efficiency = st.toggle("Plan efficiency evaluation", value=page_state.evaluate_efficiency)
    return (
        emit_sparse_points,
        emit_dense_points,
        reference_enabled,
        compare_to_arcore,
        evaluate_cloud,
        evaluate_efficiency,
    )


def _render_pipeline_snapshot(snapshot: RunSnapshot) -> None:
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_pipeline_notice(snapshot),
        metrics=_pipeline_metrics(snapshot),
        caption=_pipeline_caption(snapshot),
        body_renderer=lambda: _render_pipeline_tabs(snapshot),
    )


def _sync_pipeline_page_state_from_template(
    *,
    context: AppContext,
    config_path: Path,
    request: RunRequest,
    statuses: list[object],
) -> None:
    page_state = context.state.pipeline
    if page_state.config_path == config_path:
        return
    source_updates: dict[str, object] = {
        "source_kind": page_state.source_kind,
        "advio_sequence_id": page_state.advio_sequence_id,
    }
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug):
            advio_sequence_id, _ = _resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=statuses)
            source_updates = {
                "source_kind": PipelineSourceId.ADVIO,
                "advio_sequence_id": advio_sequence_id,
            }
        case Record3DLiveSourceSpec() as record3d_source:
            source_updates = _record3d_page_updates_from_source(record3d_source)
        case _:
            source_updates = {"source_kind": page_state.source_kind, "advio_sequence_id": page_state.advio_sequence_id}
    save_model_updates(
        context.store,
        context.state,
        page_state,
        config_path=config_path,
        experiment_name=request.experiment_name,
        mode=request.mode,
        method=request.slam.method,
        slam_max_frames=request.slam.backend.max_frames,
        slam_config_path=request.slam.backend.config_path,
        emit_dense_points=request.slam.outputs.emit_dense_points,
        emit_sparse_points=request.slam.outputs.emit_sparse_points,
        reference_enabled=request.benchmark.reference.enabled,
        compare_to_arcore=request.benchmark.trajectory.enabled,
        evaluate_cloud=request.benchmark.cloud.enabled,
        evaluate_efficiency=request.benchmark.efficiency.enabled,
        **source_updates,
    )


def _record3d_source_spec_from_action(action: PipelinePageAction) -> Record3DLiveSourceSpec:
    """Build the typed Record3D live source contract from one pipeline action."""
    return Record3DLiveSourceSpec(
        persist_capture=action.record3d_persist_capture,
        transport=action.record3d_transport,
        device_index=action.record3d_usb_device_index if action.record3d_transport is Record3DTransportId.USB else None,
        device_address=action.record3d_wifi_device_address
        if action.record3d_transport is Record3DTransportId.WIFI
        else "",
    )


def _record3d_page_updates_from_source(source: Record3DLiveSourceSpec) -> dict[str, object]:
    """Build pipeline page-state updates from a typed Record3D live source contract."""
    return {
        "source_kind": PipelineSourceId.RECORD3D,
        "record3d_transport": source.transport,
        "record3d_usb_device_index": 0 if source.device_index is None else source.device_index,
        "record3d_wifi_device_address": source.device_address,
        "record3d_persist_capture": source.persist_capture,
    }


def _build_request_from_action(context: AppContext, action: PipelinePageAction) -> tuple[RunRequest | None, str | None]:
    try:
        if action.source_kind is PipelineSourceId.ADVIO:
            if action.advio_sequence_id is None:
                raise ValueError("Select a replay-ready ADVIO scene.")
            source = DatasetSourceSpec(
                dataset_id=DatasetId.ADVIO,
                sequence_id=context.advio_service.scene(action.advio_sequence_id).sequence_slug,
            )
        else:
            source = _record3d_source_spec_from_action(action)
        request = RunRequest(
            experiment_name=action.experiment_name.strip() or "pipeline-demo",
            mode=action.mode,
            output_dir=context.path_config.artifacts_dir,
            source=source,
            slam=SlamStageConfig(
                method=action.method,
                outputs={
                    "emit_dense_points": action.emit_dense_points,
                    "emit_sparse_points": action.emit_sparse_points,
                },
                backend={
                    "max_frames": action.slam_max_frames,
                    "config_path": action.slam_config_path,
                },
            ),
            benchmark=BenchmarkConfig(
                reference={"enabled": action.reference_enabled},
                trajectory=TrajectoryBenchmarkConfig(enabled=action.compare_to_arcore),
                cloud=CloudBenchmarkConfig(enabled=action.evaluate_cloud),
                efficiency=EfficiencyBenchmarkConfig(enabled=action.evaluate_efficiency),
            ),
            visualization=VisualizationConfig(export_viewer_rrd=False, connect_live_viewer=False),
        )
        return request, None
    except Exception as exc:
        return None, str(exc)


def _build_preview_plan(request: RunRequest, path_config: PathConfig) -> tuple[RunPlan | None, str | None]:
    try:
        return request.build(path_config), None
    except Exception as exc:
        return None, str(exc)


def _request_support_error(
    *,
    request: RunRequest | None,
    plan: RunPlan | None,
    previewable_statuses: list[object],
) -> str | None:
    if request is None:
        return None
    if plan is None:
        return "The current request failed validation and could not be planned."
    unsupported_stage_ids = [stage.id.value for stage in plan.stages if stage.id not in _SUPPORTED_APP_STAGE_IDS]
    if unsupported_stage_ids:
        return "The current app demo can execute only ingest, slam, and summary stages. Disable: " + ", ".join(
            unsupported_stage_ids
        )
    match request.source:
        case DatasetSourceSpec(dataset_id=DatasetId.ADVIO, sequence_id=sequence_slug):
            if _resolve_advio_sequence_id(sequence_slug=sequence_slug, statuses=previewable_statuses)[0] is None:
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


def _source_input_error(action: PipelinePageAction) -> str | None:
    if action.source_kind is PipelineSourceId.ADVIO:
        return None if action.advio_sequence_id is not None else "Select a replay-ready ADVIO scene."
    return record3d_transport_input_error(
        transport=action.record3d_transport,
        wifi_device_address=action.record3d_wifi_device_address,
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
        f" · Method: {_pipeline_method_label(snapshot.plan.method)}"
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
            slam_update = snapshot.latest_slam_update
            pointmap_preview = (
                slam_update.preview_rgb
                if slam_update is not None and slam_update.preview_rgb is not None
                else _pointmap_preview_image(slam_update.pointmap if slam_update is not None else None)
            )
            preview_left, preview_right = st.columns(2, gap="large")
            with preview_left:
                st.markdown("**RGB Frame**")
                st.image(packet.rgb, channels="RGB", clamp=True, width="stretch")
            with preview_right:
                st.markdown("**ViSTA Preview Artifact**")
                if pointmap_preview is None:
                    st.info(_streaming_pointmap_empty_message(snapshot))
                else:
                    st.image(pointmap_preview, clamp=True, width="stretch")
            details_left, details_right = st.columns((1.0, 1.0), gap="large")
            with details_left:
                st.markdown("**SLAM Update**")
                if snapshot.latest_slam_update is None:
                    st.info("No SLAM update is available yet.")
                else:
                    st.json(
                        {
                            **snapshot.latest_slam_update.model_dump(mode="json", exclude={"pointmap", "preview_rgb"}),
                            "pointmap_shape": None
                            if snapshot.latest_slam_update.pointmap is None
                            else list(snapshot.latest_slam_update.pointmap.shape),
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
            evo_preview, evo_error = _resolve_evo_preview(snapshot)
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


def _handle_pipeline_page_action(context: AppContext, action: PipelinePageAction) -> str | None:
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
        _start_pipeline_demo_run(
            context,
            action=action,
        )
        return None
    except Exception as exc:
        return str(exc)


def _start_pipeline_demo_run(context: AppContext, *, action: PipelinePageAction) -> None:
    """Start one bounded pipeline run through the shared app facade."""
    request, request_error = _build_request_from_action(context, action)
    if request is None:
        raise ValueError(request_error or "Failed to build the current request.")
    runtime_source = (
        None if request.mode is PipelineMode.OFFLINE else _build_streaming_source_from_action(context, action)
    )
    context.run_service.start_run(request=request, runtime_source=runtime_source)


def _discover_pipeline_config_paths(path_config: PathConfig) -> list[Path]:
    config_dir = path_config.resolve_pipeline_configs_dir()
    if not config_dir.exists():
        return []
    return sorted(path.resolve() for path in config_dir.rglob("*.toml") if path.is_file())


def _pipeline_config_label(path_config: PathConfig, config_path: Path) -> str:
    config_root = path_config.resolve_pipeline_configs_dir()
    try:
        return str(config_path.relative_to(config_root))
    except ValueError:
        return (
            str(config_path.relative_to(path_config.root))
            if config_path.is_relative_to(path_config.root)
            else str(config_path)
        )


def _load_pipeline_request(path_config: PathConfig, config_path: Path) -> tuple[RunRequest | None, str | None]:
    try:
        return load_run_request_toml(path_config=path_config, config_path=config_path), None
    except Exception as exc:
        return None, str(exc)


def _build_streaming_source_from_action(context: AppContext, action: PipelinePageAction):
    if action.source_kind is PipelineSourceId.ADVIO:
        if action.advio_sequence_id is None:
            raise ValueError("Select a replay-ready ADVIO scene.")
        return context.advio_service.build_streaming_source(
            sequence_id=action.advio_sequence_id,
            pose_source=action.pose_source,
            respect_video_rotation=action.respect_video_rotation,
        )
    transport_input_error = record3d_transport_input_error(
        transport=action.record3d_transport,
        wifi_device_address=action.record3d_wifi_device_address,
    )
    if transport_input_error is not None:
        raise ValueError(transport_input_error)
    record3d_source = _record3d_source_spec_from_action(action)
    source = Record3DStreamingSourceConfig(
        transport=record3d_source.transport,
        device_index=0 if record3d_source.device_index is None else record3d_source.device_index,
        device_address=record3d_source.device_address,
    ).setup_target()
    if source is None:
        raise RuntimeError("Failed to initialize the Record3D streaming source.")
    return source


def _advio_sequence_id_from_slug(sequence_slug: str, statuses: list[object]) -> int | None:
    for status in statuses:
        scene = getattr(status, "scene", None)
        if scene is not None and getattr(scene, "sequence_slug", None) == sequence_slug:
            return int(scene.sequence_id)
    if not sequence_slug.startswith("advio-"):
        return None
    suffix = sequence_slug.split("-", maxsplit=1)[1]
    return int(suffix) if suffix.isdigit() else None


def _resolve_advio_sequence_id(*, sequence_slug: str, statuses: list[object]) -> tuple[int | None, str | None]:
    sequence_id = _advio_sequence_id_from_slug(sequence_slug, statuses)
    if sequence_id is None:
        return None, f"ADVIO sequence '{sequence_slug}' is not replay-ready in the local dataset."
    return sequence_id, None


def _parse_optional_int(*, raw_value: str, field_label: str) -> tuple[int | None, str | None]:
    if raw_value == "":
        return None, None
    try:
        return int(raw_value), None
    except ValueError:
        return None, f"Enter a whole number for `{field_label}` or leave the field blank."


def _parse_optional_repo_path(path_config: PathConfig, raw_value: str) -> Path | None:
    return None if raw_value == "" else path_config.resolve_repo_path(raw_value)


def _display_repo_relative_path(path_config: PathConfig, path: Path | None) -> str:
    if path is None:
        return ""
    resolved = path if path.is_absolute() else path_config.resolve_repo_path(path)
    return (
        str(resolved.relative_to(path_config.root))
        if resolved.is_relative_to(path_config.root)
        else resolved.as_posix()
    )


def _request_summary_payload(request: RunRequest) -> dict[str, object]:
    payload = {
        "experiment_name": request.experiment_name,
        "mode": request.mode.value,
        "output_dir": request.output_dir.as_posix(),
        "slam": {
            "method": request.slam.method.value,
            "config_path": None
            if request.slam.backend.config_path is None
            else request.slam.backend.config_path.as_posix(),
            "max_frames": request.slam.backend.max_frames,
            "emit_dense_points": request.slam.outputs.emit_dense_points,
            "emit_sparse_points": request.slam.outputs.emit_sparse_points,
        },
        "benchmark": request.benchmark.model_dump(mode="json"),
        "visualization": request.visualization.model_dump(mode="json"),
    }
    match request.source:
        case DatasetSourceSpec(dataset_id=dataset_id, sequence_id=sequence_id):
            payload["source"] = {
                "kind": "dataset",
                "dataset_id": dataset_id.value,
                "sequence_id": sequence_id,
            }
        case _:
            payload["source"] = request.source.model_dump(mode="json")
    return payload


def _pointmap_preview_image(pointmap: np.ndarray | None) -> np.ndarray | None:
    """Return a renderable preview image for one ViSTA preview artifact."""
    if pointmap is None:
        return None
    preview_array = np.asarray(pointmap)
    if preview_array.size == 0:
        return None
    if preview_array.ndim == 2:
        return normalize_grayscale_image(np.asarray(preview_array, dtype=np.float32))
    if preview_array.ndim != 3:
        return None
    if preview_array.shape[-1] == 1:
        return normalize_grayscale_image(np.asarray(preview_array[..., 0], dtype=np.float32))
    if preview_array.shape[-1] in {3, 4} and (
        np.issubdtype(preview_array.dtype, np.integer)
        or (np.isfinite(preview_array).all() and np.nanmin(preview_array) >= 0.0 and np.nanmax(preview_array) <= 1.0)
    ):
        return np.asarray(preview_array)
    magnitude = np.linalg.norm(np.asarray(preview_array, dtype=np.float32), axis=-1)
    return normalize_grayscale_image(magnitude)


def _resolve_evo_preview(snapshot: RunSnapshot) -> tuple[PipelineEvoPreview | None, str | None]:
    if snapshot.sequence_manifest is None or snapshot.slam is None:
        return None, None
    reference_path = snapshot.sequence_manifest.reference_tum_path
    estimate_path = snapshot.slam.trajectory_tum.path
    if reference_path is None:
        return None, "No `ground_truth.tum` reference is available for this ADVIO slice."
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


@lru_cache(maxsize=32)
def _compute_evo_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    reference_mtime_ns: int,
    estimate_mtime_ns: int,
) -> PipelineEvoPreview:
    del reference_mtime_ns, estimate_mtime_ns
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = evo_sync.associate_trajectories(
            reference_trajectory,
            estimate_trajectory,
            max_diff=_EVO_ASSOCIATION_MAX_DIFF_S,
        )
    except evo_sync.SyncException as exc:
        raise ValueError(
            f"No matching timestamps were found for evo APE (max_diff={_EVO_ASSOCIATION_MAX_DIFF_S:.3f}s)."
        ) from exc

    metric = evo_metrics.APE(evo_metrics.PoseRelation.translation_part)
    metric.process_data((associated_reference, associated_estimate))
    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo APE produced zero matched trajectory pairs for the current run.")

    return PipelineEvoPreview(
        reference=TrajectorySeries(
            name="Reference",
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            positions_xyz=np.asarray(associated_reference.positions_xyz, dtype=np.float64),
        ),
        estimate=TrajectorySeries(
            name="Estimate",
            timestamps_s=np.asarray(associated_estimate.timestamps, dtype=np.float64),
            positions_xyz=np.asarray(associated_estimate.positions_xyz, dtype=np.float64),
        ),
        error_series=ErrorSeries(
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            values=error_values,
        ),
        stats=MetricStats.from_error_values(error_values),
    )


__all__ = ["render"]
