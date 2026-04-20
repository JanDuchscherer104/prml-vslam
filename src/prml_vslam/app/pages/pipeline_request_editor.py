"""Rendering helpers for the Pipeline page request editor."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.advio import AdvioLocalSceneStatus, AdvioModality, AdvioPoseFrameMode, AdvioPoseSource
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode

from ..models import PipelinePageState, PipelineSourceId
from ..pipeline_controller import PipelinePageAction, parse_optional_float, parse_optional_int
from ..record3d_controls import render_record3d_transport_controls, render_record3d_transport_details

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render_request_editor(
    *,
    context: AppContext,
    page_state: PipelinePageState,
    selected_config_path: Path,
    previewable_statuses: list[AdvioLocalSceneStatus],
) -> tuple[PipelinePageAction, str | None, str | None]:
    """Render the request editor and return the resolved action payload."""
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
    experiment_name, mode, method, slam_max_frames, identity_input_error = _render_request_identity_controls(
        page_state=page_state,
        source_kind=resolved_source_kind,
    )
    (
        advio_sequence_id,
        dataset_frame_stride,
        dataset_target_fps,
        record3d_transport,
        record3d_usb_device_index,
        record3d_wifi_device_address,
        record3d_persist_capture,
        pose_source,
        pose_frame_mode,
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
                "dataset_frame_stride": dataset_frame_stride,
                "dataset_target_fps": dataset_target_fps,
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
                "pose_frame_mode": pose_frame_mode,
                "respect_video_rotation": respect_video_rotation,
            }
        ),
        identity_input_error,
        source_input_error,
    )


def _pipeline_method_help(method: MethodId) -> str:
    """Explain the current streaming-preview semantics for the selected method."""
    if method is MethodId.MOCK:
        return "Repository-local mock backend that emits live pose and pointmap telemetry for UI validation."
    if method is MethodId.MAST3R:
        return "MASt3R-SLAM is retained as a method id, but this repository has no executable MASt3R backend yet."
    return (
        "Real ViSTA-SLAM backend. Offline runs produce real artifacts; streaming runs show packet FPS, accepted "
        "keyframe FPS, and live previews only when the backend produces a new keyframe artifact."
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
    previewable_statuses: list[AdvioLocalSceneStatus],
) -> tuple[
    int | None,
    int,
    float | None,
    Record3DTransportId,
    int,
    str,
    bool,
    AdvioPoseSource,
    AdvioPoseFrameMode,
    bool,
    str | None,
]:
    _, right = st.columns(2, gap="large")
    with right:
        advio_sequence_id = page_state.advio_sequence_id
        record3d_transport = page_state.record3d_transport
        record3d_usb_device_index = page_state.record3d_usb_device_index
        record3d_wifi_device_address = page_state.record3d_wifi_device_address
        record3d_persist_capture = page_state.record3d_persist_capture
        pose_source = page_state.pose_source
        pose_frame_mode = page_state.pose_frame_mode
        respect_video_rotation = page_state.respect_video_rotation
        dataset_frame_stride = page_state.dataset_frame_stride
        dataset_target_fps = page_state.dataset_target_fps
        source_input_error = None
        if source_kind is PipelineSourceId.ADVIO:
            (
                advio_sequence_id,
                pose_source,
                pose_frame_mode,
                respect_video_rotation,
                dataset_frame_stride,
                dataset_target_fps,
                source_input_error,
            ) = _render_advio_source_settings(
                context=context,
                page_state=page_state,
                previewable_statuses=previewable_statuses,
            )
            if advio_sequence_id is None:
                source_input_error = "Select a replay-ready ADVIO scene."
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
        dataset_frame_stride,
        dataset_target_fps,
        record3d_transport,
        record3d_usb_device_index,
        record3d_wifi_device_address,
        record3d_persist_capture,
        pose_source,
        pose_frame_mode,
        respect_video_rotation,
        source_input_error,
    )


def _render_advio_source_settings(
    *,
    context: AppContext,
    page_state: PipelinePageState,
    previewable_statuses: list[AdvioLocalSceneStatus],
) -> tuple[int | None, AdvioPoseSource, AdvioPoseFrameMode, bool, int, float | None, str | None]:
    status_by_sequence_id = {status.scene.sequence_id: status for status in previewable_statuses}
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
    provider_options = (
        _advio_provider_options(status_by_sequence_id.get(advio_sequence_id))
        if advio_sequence_id is not None
        else [AdvioPoseSource.GROUND_TRUTH]
    )
    resolved_pose_source = page_state.pose_source if page_state.pose_source in provider_options else provider_options[0]
    pose_source = st.selectbox(
        "Pose Source",
        options=provider_options,
        index=provider_options.index(resolved_pose_source),
        format_func=lambda item: item.label,
    )
    pose_frame_mode = st.selectbox(
        "Pose Frame Mode",
        options=list(AdvioPoseFrameMode),
        index=list(AdvioPoseFrameMode).index(page_state.pose_frame_mode),
        format_func=lambda item: item.label,
    )
    respect_video_rotation = st.toggle(
        "Respect video rotation metadata",
        value=page_state.respect_video_rotation,
    )
    dataset_frame_stride = int(
        st.number_input("Dataset Frame Stride", min_value=1, max_value=120, value=page_state.dataset_frame_stride)
    )
    target_fps_raw = st.text_input(
        "Dataset Target FPS",
        value="" if page_state.dataset_target_fps is None else str(page_state.dataset_target_fps),
        placeholder="blank to use stride",
    ).strip()
    dataset_target_fps, target_fps_error = parse_optional_float(
        raw_value=target_fps_raw,
        field_label="Dataset Target FPS",
    )
    sampling_error = (
        "Configure either `Dataset Frame Stride` or `Dataset Target FPS`, not both."
        if dataset_target_fps is not None and dataset_frame_stride != 1
        else target_fps_error
    )
    return (
        advio_sequence_id,
        pose_source,
        pose_frame_mode,
        respect_video_rotation,
        dataset_frame_stride,
        dataset_target_fps,
        sampling_error,
    )


def _advio_provider_options(status: AdvioLocalSceneStatus | None) -> list[AdvioPoseSource]:
    if status is None:
        return [AdvioPoseSource.GROUND_TRUTH]
    options = [AdvioPoseSource.GROUND_TRUTH]
    if AdvioModality.PIXEL_ARCORE in status.local_modalities:
        options.append(AdvioPoseSource.ARCORE)
    if AdvioModality.IPHONE_ARKIT in status.local_modalities:
        options.append(AdvioPoseSource.ARKIT)
    if AdvioModality.TANGO in status.local_modalities:
        options.extend([AdvioPoseSource.TANGO_RAW, AdvioPoseSource.TANGO_AREA_LEARNING])
    return options


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


def _render_stage_settings(page_state: PipelinePageState) -> tuple[bool, bool, bool, bool, bool, bool, bool, bool]:
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


__all__ = ["render_request_editor"]
