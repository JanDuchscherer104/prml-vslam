"""Rendering helpers for the Pipeline run-console request editor."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets.advio import AdvioLocalSceneStatus, AdvioModality, AdvioPoseFrameMode, AdvioPoseSource
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.methods.stage.config import MethodId, VistaSlamBackendConfig
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import BackendSpec, build_backend_spec

from ..models import PipelinePageState, PipelineSourceId
from ..pipeline_controls import PipelinePageAction, parse_optional_float, parse_optional_int
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
    """Render grouped request controls and return the resolved action payload."""
    source_tab, run_tab, slam_tab, stages_tab, visualization_tab = st.tabs(
        ["Source", "Run", "SLAM", "Stages", "Visualization"]
    )
    with source_tab:
        source_kind = _render_source_selector(page_state)
        (
            advio_sequence_id,
            dataset_frame_stride,
            dataset_target_fps,
            record3d_transport,
            record3d_usb_device_index,
            record3d_wifi_device_address,
            record3d_frame_timeout_seconds,
            pose_source,
            pose_frame_mode,
            respect_video_rotation,
            source_input_error,
        ) = _render_source_settings(
            context=context,
            page_state=page_state,
            source_kind=source_kind,
            previewable_statuses=previewable_statuses,
        )
    with run_tab:
        experiment_name, mode = _render_request_identity_controls(page_state=page_state, source_kind=source_kind)
    with slam_tab:
        method, slam_max_frames, slam_backend_spec, slam_input_error = _render_slam_settings(page_state=page_state)
    with stages_tab:
        (
            emit_sparse_points,
            emit_dense_points,
            ground_alignment_enabled,
            reconstruction_enabled,
            trajectory_eval_enabled,
            evaluate_cloud,
        ) = _render_stage_settings(page_state)
    with visualization_tab:
        (
            connect_live_viewer,
            export_viewer_rrd,
            grpc_url,
            viewer_blueprint_path,
            preserve_native_rerun,
            frusta_history_window_streaming,
            frusta_history_window_offline,
            show_tracking_trajectory,
            log_source_rgb,
            log_diagnostic_preview,
            log_camera_image_rgb,
            visualization_input_error,
        ) = _render_visualization_settings(page_state)

    return (
        PipelinePageAction.model_validate(
            page_state.model_dump(mode="python")
            | {
                "config_path": selected_config_path,
                "experiment_name": experiment_name,
                "source_kind": source_kind,
                "advio_sequence_id": advio_sequence_id,
                "dataset_frame_stride": dataset_frame_stride,
                "dataset_target_fps": dataset_target_fps,
                "mode": mode,
                "method": method,
                "slam_max_frames": slam_max_frames,
                "slam_backend_spec": slam_backend_spec,
                "emit_dense_points": emit_dense_points,
                "emit_sparse_points": emit_sparse_points,
                "ground_alignment_enabled": ground_alignment_enabled,
                "reconstruction_enabled": reconstruction_enabled,
                "trajectory_eval_enabled": trajectory_eval_enabled,
                "evaluate_cloud": evaluate_cloud,
                "connect_live_viewer": connect_live_viewer,
                "export_viewer_rrd": export_viewer_rrd,
                "grpc_url": grpc_url,
                "viewer_blueprint_path": viewer_blueprint_path,
                "preserve_native_rerun": preserve_native_rerun,
                "frusta_history_window_streaming": frusta_history_window_streaming,
                "frusta_history_window_offline": frusta_history_window_offline,
                "show_tracking_trajectory": show_tracking_trajectory,
                "log_source_rgb": log_source_rgb,
                "log_diagnostic_preview": log_diagnostic_preview,
                "log_camera_image_rgb": log_camera_image_rgb,
                "record3d_transport": record3d_transport,
                "record3d_usb_device_index": record3d_usb_device_index,
                "record3d_wifi_device_address": record3d_wifi_device_address,
                "record3d_frame_timeout_seconds": record3d_frame_timeout_seconds,
                "pose_source": pose_source,
                "pose_frame_mode": pose_frame_mode,
                "respect_video_rotation": respect_video_rotation,
            }
        ),
        slam_input_error or visualization_input_error,
        source_input_error,
    )


def _render_source_selector(page_state: PipelinePageState) -> PipelineSourceId:
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
    return page_state.source_kind if source_kind is None else source_kind


def _pipeline_method_help(method: MethodId) -> str:
    """Explain the current execution semantics for the selected method."""
    if method is MethodId.MAST3R:
        return "MASt3R-SLAM is retained as a method id, but this repository has no executable backend yet."
    return "Real ViSTA-SLAM backend for offline and streaming runs."


def _render_request_identity_controls(
    *,
    page_state: PipelinePageState,
    source_kind: PipelineSourceId,
) -> tuple[str, PipelineMode]:
    experiment_name = st.text_input("Experiment Name", value=page_state.experiment_name).strip()
    mode_options = [PipelineMode.STREAMING] if source_kind is PipelineSourceId.RECORD3D else list(PipelineMode)
    default_mode = page_state.mode if page_state.mode in mode_options else mode_options[0]
    mode = st.selectbox(
        "Mode",
        options=mode_options,
        index=mode_options.index(default_mode),
        format_func=lambda item: item.title(),
    )
    return experiment_name, mode


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
    float,
    AdvioPoseSource,
    AdvioPoseFrameMode,
    bool,
    str | None,
]:
    advio_sequence_id = page_state.advio_sequence_id
    record3d_transport = page_state.record3d_transport
    record3d_usb_device_index = page_state.record3d_usb_device_index
    record3d_wifi_device_address = page_state.record3d_wifi_device_address
    record3d_frame_timeout_seconds = page_state.record3d_frame_timeout_seconds
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
            record3d_frame_timeout_seconds,
            source_input_error,
        ) = _render_record3d_source_settings(page_state=page_state)
    return (
        advio_sequence_id,
        dataset_frame_stride,
        dataset_target_fps,
        record3d_transport,
        record3d_usb_device_index,
        record3d_wifi_device_address,
        record3d_frame_timeout_seconds,
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
) -> tuple[Record3DTransportId, int, str, float, str | None]:
    selection = render_record3d_transport_controls(
        transport=page_state.record3d_transport,
        usb_device_index=page_state.record3d_usb_device_index,
        wifi_device_address=page_state.record3d_wifi_device_address,
        widget_key_prefix="pipeline_record3d",
    )
    frame_timeout_raw = st.text_input(
        "Frame Timeout",
        value=str(page_state.record3d_frame_timeout_seconds),
    ).strip()
    frame_timeout_seconds, timeout_error = parse_optional_float(
        raw_value=frame_timeout_raw,
        field_label="Frame Timeout",
    )
    render_record3d_transport_details(selection)
    return (
        selection.transport,
        selection.usb_device_index,
        selection.wifi_device_address,
        page_state.record3d_frame_timeout_seconds if frame_timeout_seconds is None else frame_timeout_seconds,
        selection.input_error or timeout_error,
    )


def _render_slam_settings(page_state: PipelinePageState) -> tuple[MethodId, int | None, BackendSpec | None, str | None]:
    method_options = list(MethodId)
    method = st.selectbox(
        "VSLAM Method",
        options=method_options,
        index=method_options.index(page_state.method),
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
    if slam_max_frames_error is not None:
        slam_max_frames = page_state.slam_max_frames

    backend_spec = _backend_spec_for_method(
        page_state=page_state,
        method=method,
        max_frames=slam_max_frames,
    )
    match method:
        case MethodId.VISTA:
            backend_spec = _render_vista_backend_settings(backend_spec, max_frames=slam_max_frames)
        case MethodId.MAST3R:
            st.warning("MASt3R-SLAM is not executable in the current pipeline runtime.")
    return method, slam_max_frames, backend_spec, slam_max_frames_error


def _backend_spec_for_method(
    *,
    page_state: PipelinePageState,
    method: MethodId,
    max_frames: int | None,
) -> BackendSpec:
    if page_state.slam_backend_spec is not None and page_state.slam_backend_spec.method_id is method:
        return page_state.slam_backend_spec.model_copy(update={"max_frames": max_frames})
    return build_backend_spec(method=method, max_frames=max_frames)


def _render_vista_backend_settings(backend_spec: BackendSpec, *, max_frames: int | None) -> VistaSlamBackendConfig:
    backend = (
        backend_spec
        if isinstance(backend_spec, VistaSlamBackendConfig)
        else build_backend_spec(method=MethodId.VISTA, max_frames=max_frames)
    )
    if not isinstance(backend, VistaSlamBackendConfig):
        raise TypeError("Expected a ViSTA backend config.")

    device_options = ["auto", "cuda", "cpu"]
    device = st.selectbox(
        "Device",
        options=device_options,
        index=device_options.index(backend.device),
    )
    col_a, col_b, col_c = st.columns(3, gap="small")
    with col_a:
        max_view_num = int(st.number_input("Max Views", min_value=1, value=backend.max_view_num))
        flow_thres = float(st.number_input("Flow Threshold", value=float(backend.flow_thres)))
        point_conf_thres = float(
            st.number_input("Point Confidence", min_value=0.0, value=float(backend.point_conf_thres))
        )
    with col_b:
        neighbor_edge_num = int(st.number_input("Neighbor Edges", min_value=0, value=backend.neighbor_edge_num))
        loop_edge_num = int(st.number_input("Loop Edges", min_value=0, value=backend.loop_edge_num))
        rel_pose_thres = float(
            st.number_input("Relative Pose Threshold", min_value=0.0, value=float(backend.rel_pose_thres))
        )
    with col_c:
        loop_dist_min = int(st.number_input("Loop Min Distance", min_value=0, value=backend.loop_dist_min))
        loop_nms = int(st.number_input("Loop NMS", min_value=0, value=backend.loop_nms))
        pgo_every = int(st.number_input("PGO Interval", min_value=1, value=backend.pgo_every))
    loop_cand_thresh_neighbor = int(
        st.number_input("Loop Candidate Neighbor Threshold", min_value=0, value=backend.loop_cand_thresh_neighbor)
    )
    random_seed = int(st.number_input("Random Seed", value=backend.random_seed))
    with st.expander("ViSTA Paths", expanded=False):
        vista_slam_dir = _path_input("ViSTA Directory", backend.vista_slam_dir)
        checkpoint_path = _path_input("Checkpoint Path", backend.checkpoint_path)
        vocab_path = _path_input("Vocabulary Path", backend.vocab_path)
    return VistaSlamBackendConfig(
        method_id=MethodId.VISTA,
        max_frames=max_frames,
        vista_slam_dir=vista_slam_dir,
        checkpoint_path=checkpoint_path,
        vocab_path=vocab_path,
        max_view_num=max_view_num,
        flow_thres=flow_thres,
        neighbor_edge_num=neighbor_edge_num,
        loop_edge_num=loop_edge_num,
        loop_dist_min=loop_dist_min,
        loop_nms=loop_nms,
        loop_cand_thresh_neighbor=loop_cand_thresh_neighbor,
        point_conf_thres=point_conf_thres,
        rel_pose_thres=rel_pose_thres,
        pgo_every=pgo_every,
        random_seed=random_seed,
        device=device,
    )


def _render_stage_settings(page_state: PipelinePageState) -> tuple[bool, bool, bool, bool, bool, bool]:
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("**SLAM Outputs**")
        emit_sparse_points = st.toggle("Sparse Geometry", value=page_state.emit_sparse_points)
        emit_dense_points = st.toggle("Dense Geometry", value=page_state.emit_dense_points)
        st.markdown("**Derived Stages**")
        ground_alignment_enabled = st.toggle("Ground Alignment", value=page_state.ground_alignment_enabled)
        reconstruction_enabled = st.toggle("Reference Reconstruction", value=page_state.reconstruction_enabled)
    with right:
        st.markdown("**Evaluation**")
        trajectory_eval_enabled = st.toggle("Trajectory Evaluation", value=page_state.trajectory_eval_enabled)
        evaluate_cloud = st.toggle("Dense-Cloud Evaluation", value=page_state.evaluate_cloud)
        st.caption("Dense-cloud evaluation remains a planned diagnostic stage without a registered runtime.")
        st.markdown("**Summary**")
        st.toggle("Run Summary", value=True, disabled=True)
    return (
        emit_sparse_points,
        emit_dense_points,
        ground_alignment_enabled,
        reconstruction_enabled,
        trajectory_eval_enabled,
        evaluate_cloud,
    )


def _render_visualization_settings(
    page_state: PipelinePageState,
) -> tuple[bool, bool, str, Path | None, bool, int, int | None, bool, bool, bool, bool, str | None]:
    left, right = st.columns(2, gap="large")
    with left:
        connect_live_viewer = st.toggle("Connect Live Viewer", value=page_state.connect_live_viewer)
        export_viewer_rrd = st.toggle("Export Viewer RRD", value=page_state.export_viewer_rrd)
        preserve_native_rerun = st.toggle("Preserve Native Rerun", value=page_state.preserve_native_rerun)
        show_tracking_trajectory = st.toggle("Show Tracking Trajectory", value=page_state.show_tracking_trajectory)
        grpc_url = st.text_input("Rerun gRPC URL", value=page_state.grpc_url).strip()
        viewer_blueprint_path = _optional_path_input("Viewer Blueprint", page_state.viewer_blueprint_path)
    with right:
        log_source_rgb = st.toggle("Log Source RGB", value=page_state.log_source_rgb)
        log_diagnostic_preview = st.toggle("Log Diagnostic Preview", value=page_state.log_diagnostic_preview)
        log_camera_image_rgb = st.toggle("Log Camera RGB Plane", value=page_state.log_camera_image_rgb)
        frusta_history_window_streaming = int(
            st.number_input(
                "Streaming Frusta Window",
                min_value=1,
                value=page_state.frusta_history_window_streaming,
            )
        )
        offline_window_raw = st.text_input(
            "Offline Frusta Window",
            value=(
                ""
                if page_state.frusta_history_window_offline is None
                else str(page_state.frusta_history_window_offline)
            ),
            placeholder="blank for full history",
        ).strip()
        frusta_history_window_offline, offline_window_error = parse_optional_int(
            raw_value=offline_window_raw,
            field_label="Offline Frusta Window",
        )
    return (
        connect_live_viewer,
        export_viewer_rrd,
        grpc_url,
        viewer_blueprint_path,
        preserve_native_rerun,
        frusta_history_window_streaming,
        frusta_history_window_offline,
        show_tracking_trajectory,
        log_source_rgb,
        log_diagnostic_preview,
        log_camera_image_rgb,
        offline_window_error,
    )


def _path_input(label: str, value: Path) -> Path:
    raw_value = st.text_input(label, value=value.as_posix()).strip()
    return value if raw_value == "" else Path(raw_value)


def _optional_path_input(label: str, value: Path | None) -> Path | None:
    raw_value = st.text_input(label, value="" if value is None else value.as_posix()).strip()
    return None if raw_value == "" else Path(raw_value)


__all__ = ["render_request_editor"]
