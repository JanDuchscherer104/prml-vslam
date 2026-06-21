"""Loop-preview controls for normalized dataset entries."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

import streamlit as st

from prml_vslam.interfaces import Observation
from prml_vslam.sources.datasets.advio import AdvioPoseSource
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalization import open_normalized_dataset_stream, source_config_for_normalization
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedSequenceRecord,
    normalized_advio_pose_sources,
)
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdPoseSource
from prml_vslam.utils import JsonObject

from ..advio_controller import (
    AdvioPreviewFormData,
    handle_advio_preview_action,
    sync_advio_preview_state,
)
from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_live_action_slot,
    render_live_fragment,
    render_live_image,
    render_live_packet_tabs,
    render_live_session_shell,
    rerun_after_action,
)
from ..models import (
    AdvioPageState,
    DatasetPreviewSnapshot,
    PreviewStreamState,
    Record3DDatasetPageState,
    Record3DDatasetPoseSource,
    TumRgbdPageState,
)
from ..state import save_model_updates

if TYPE_CHECKING:
    from ..bootstrap import AppContext


DatasetPreviewState = AdvioPageState | TumRgbdPageState | Record3DDatasetPageState
DatasetPoseSource = AdvioPoseSource | TumRgbdPoseSource | Record3DDatasetPoseSource


def sync_tum_rgbd_preview_state(
    context: AppContext, snapshot: DatasetPreviewSnapshot | None = None
) -> DatasetPreviewSnapshot:
    """Keep TUM RGB-D preview state aligned with the shared preview runtime."""
    snapshot = context.dataset_preview_runtime.snapshot() if snapshot is None else snapshot
    if context.state.tum_rgbd.preview_is_running and snapshot.state not in {
        PreviewStreamState.CONNECTING,
        PreviewStreamState.STREAMING,
    }:
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
    return snapshot


def sync_record3d_dataset_preview_state(
    context: AppContext, snapshot: DatasetPreviewSnapshot | None = None
) -> DatasetPreviewSnapshot:
    """Keep Record3D preview state aligned with the shared preview runtime."""
    snapshot = context.dataset_preview_runtime.snapshot() if snapshot is None else snapshot
    if context.state.record3d_dataset.preview_is_running and snapshot.state not in {
        PreviewStreamState.CONNECTING,
        PreviewStreamState.STREAMING,
    }:
        save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=False)
    return snapshot


def handle_tum_rgbd_preview_action(
    *,
    context: AppContext,
    sequence_id: str,
    profile_key: str | None,
    pose_source: TumRgbdPoseSource,
    include_depth: bool,
    start_requested: bool,
    stop_requested: bool,
) -> str | None:
    """Apply one TUM RGB-D preview start or stop action."""
    save_model_updates(
        context.store,
        context.state,
        context.state.tum_rgbd,
        preview_sequence_id=sequence_id,
        preview_pose_source=pose_source,
        preview_include_depth=include_depth,
    )
    if stop_requested:
        context.dataset_preview_runtime.stop()
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
        return None
    if not start_requested:
        return None
    try:
        scene = context.tum_rgbd_service.scene(sequence_id)
        stream = open_normalized_dataset_stream(
            dataset_id=DatasetId.TUM_RGBD,
            service=context.tum_rgbd_service,
            source_config=source_config_for_normalization(dataset_id=DatasetId.TUM_RGBD, sequence_id=sequence_id),
            include_depth=include_depth,
            path_config=context.path_config,
            profile_key=profile_key,
            output_dir=context.path_config.resolve_output_dir(
                Path("dataset-preview") / "tum_rgbd" / str(sequence_id), create=True
            ),
        )
        context.dataset_preview_runtime.start(
            sequence_id=sequence_id,
            sequence_label=scene.display_name,
            pose_source=pose_source,
            stream=stream,
        )
    except Exception as exc:
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
        return str(exc)
    save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=True)
    save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
    save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=False)
    return None


def handle_record3d_dataset_preview_action(
    *,
    context: AppContext,
    sequence_id: str,
    profile_key: str | None,
    pose_source: Record3DDatasetPoseSource,
    include_depth: bool,
    start_requested: bool,
    stop_requested: bool,
) -> str | None:
    """Apply one Record3D preview start or stop action."""
    resolved_pose_source = Record3DDatasetPoseSource(pose_source.value)
    save_model_updates(
        context.store,
        context.state,
        context.state.record3d_dataset,
        preview_sequence_id=sequence_id,
        preview_pose_source=resolved_pose_source,
        preview_include_depth=include_depth,
    )
    if stop_requested:
        context.dataset_preview_runtime.stop()
        save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=False)
        return None
    if not start_requested:
        return None
    try:
        scene = context.record3d_dataset_service.scene(sequence_id)
        stream = open_normalized_dataset_stream(
            dataset_id=DatasetId.RECORD3D,
            service=context.record3d_dataset_service,
            source_config=source_config_for_normalization(dataset_id=DatasetId.RECORD3D, sequence_id=sequence_id),
            include_depth=include_depth,
            path_config=context.path_config,
            profile_key=profile_key,
            output_dir=context.path_config.resolve_output_dir(
                Path("dataset-preview") / "record3d" / str(sequence_id), create=True
            ),
        )
        context.dataset_preview_runtime.start(
            sequence_id=sequence_id,
            sequence_label=scene.display_name,
            pose_source=resolved_pose_source,
            stream=stream,
        )
    except Exception as exc:
        save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=False)
        return str(exc)
    save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=True)
    save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
    save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
    return None


def render_advio_loop_preview(context: AppContext, normalized: NormalizedDatasetQuery) -> None:
    """Render ADVIO normalized loop preview controls."""
    render_loop_preview(
        records=normalized.default_records,
        page_state=context.state.advio,
        pose_source_options=lambda sequence_id: normalized_advio_pose_sources(
            normalized.records,
            sequence_id=str(sequence_id),
        ),
        caption="Run a normalized ADVIO scene in a local loop and inspect frames, trajectory, and camera metadata live.",
        option_label="Normalize video display orientation",
        option_key="preview_normalize_video_orientation",
        initial_option_value=context.state.advio.preview_normalize_video_orientation,
        action_key_prefix="advio-loop-preview",
        action=lambda selected_id, profile_key, pose_source, option_value, start, stop: handle_advio_preview_action(
            context,
            AdvioPreviewFormData(
                sequence_id=int(str(selected_id).split("-", maxsplit=1)[1]),
                pose_source=cast(AdvioPoseSource, pose_source),
                profile_key=profile_key,
                normalize_video_orientation=option_value,
                start_requested=start,
                stop_requested=stop,
            ),
        ),
        sync_snapshot=lambda: sync_advio_preview_state(context),
    )


def render_tum_rgbd_loop_preview(context: AppContext, normalized: NormalizedDatasetQuery) -> None:
    """Render TUM RGB-D normalized loop preview controls."""
    render_loop_preview(
        records=normalized.default_records,
        page_state=context.state.tum_rgbd,
        pose_source_options=None,
        caption="Run a normalized TUM RGB-D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
        option_label="Include depth frames",
        option_key="preview_include_depth",
        initial_option_value=context.state.tum_rgbd.preview_include_depth,
        action_key_prefix="tum-rgbd-loop-preview",
        action=lambda selected_id, profile_key, pose_source, option_value, start, stop: handle_tum_rgbd_preview_action(
            context=context,
            sequence_id=str(selected_id),
            profile_key=profile_key,
            pose_source=cast(TumRgbdPoseSource, pose_source),
            include_depth=option_value,
            start_requested=start,
            stop_requested=stop,
        ),
        sync_snapshot=lambda: sync_tum_rgbd_preview_state(context),
    )


def render_record3d_loop_preview(
    context: AppContext,
    normalized: NormalizedDatasetQuery,
) -> None:
    """Render Record3D normalized loop preview controls."""
    render_loop_preview(
        records=normalized.default_records,
        page_state=context.state.record3d_dataset,
        pose_source_options=lambda _selected_id: [Record3DDatasetPoseSource.ARKIT],
        caption="Run a normalized Record3D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
        option_label="Include depth frames",
        option_key="preview_include_depth",
        initial_option_value=context.state.record3d_dataset.preview_include_depth,
        action_key_prefix="record3d-dataset-loop-preview",
        action=lambda selected_id,
        profile_key,
        pose_source,
        option_value,
        start,
        stop: handle_record3d_dataset_preview_action(
            context=context,
            sequence_id=str(selected_id),
            profile_key=profile_key,
            pose_source=cast(Record3DDatasetPoseSource, pose_source),
            include_depth=option_value,
            start_requested=start,
            stop_requested=stop,
        ),
        sync_snapshot=lambda: sync_record3d_dataset_preview_state(context),
    )


def render_loop_preview(
    *,
    records: list[NormalizedSequenceRecord],
    page_state: DatasetPreviewState,
    pose_source_options: Callable[[str], Sequence[DatasetPoseSource]] | None,
    caption: str,
    option_label: str,
    option_key: str,
    initial_option_value: bool,
    action_key_prefix: str,
    action: Callable[[str, str | None, DatasetPoseSource, bool, bool, bool], str | None],
    sync_snapshot: Callable[[], DatasetPreviewSnapshot],
) -> None:
    """Render the shared normalized dataset loop-preview control."""
    records_by_sequence = {record.sequence_id: record for record in records}
    previewable_ids: list[str] = list(records_by_sequence)
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption(caption)
        if not previewable_ids:
            st.info("Build at least one normalized entry to unlock loop preview.")
            return
        state_sequence_id = preview_state_sequence_id(page_state.preview_sequence_id)
        selected_id: str = state_sequence_id if state_sequence_id in previewable_ids else previewable_ids[0]
        selected_id = st.selectbox(
            "Preview Scene",
            options=previewable_ids,
            index=previewable_ids.index(selected_id),
            format_func=lambda sequence_id: next(
                record.sequence_label for record in records if record.sequence_id == sequence_id
            ),
            key=f"{action_key_prefix}:scene",
        )
        available_pose_sources: list[DatasetPoseSource] = (
            [page_state.preview_pose_source] if pose_source_options is None else list(pose_source_options(selected_id))
        )
        pose_source: DatasetPoseSource = (
            page_state.preview_pose_source
            if page_state.preview_pose_source in available_pose_sources
            else available_pose_sources[0]
        )
        pose_source = st.selectbox(
            "Pose Source",
            options=available_pose_sources,
            index=available_pose_sources.index(pose_source),
            format_func=lambda item: item.label,
            key=f"{action_key_prefix}:pose-source",
        )
        option_value = st.toggle(
            option_label,
            value=initial_option_value,
            key=f"{action_key_prefix}:{option_key}",
        )
        start_requested, stop_requested = render_live_action_slot(
            is_active=page_state.preview_is_running,
            start_label="Start preview",
            stop_label="Stop preview",
            key=action_key_prefix,
        )
        selected_record = records_by_sequence.get(selected_id)
        error_message = action(
            selected_id,
            None if selected_record is None else selected_record.profile_key,
            pose_source,
            option_value,
            start_requested,
            stop_requested,
        )
        if rerun_after_action(action_requested=start_requested or stop_requested, error_message=error_message):
            return
        if error_message:
            st.error(error_message)
        render_live_fragment(
            run_every=live_poll_interval(is_active=page_state.preview_is_running, interval_seconds=0.2),
            render_body=lambda: render_preview_snapshot(sync_snapshot()),
        )


def render_preview_snapshot(snapshot: DatasetPreviewSnapshot) -> None:
    """Render the current shared preview-runtime snapshot."""
    render_live_session_shell(
        title=None,
        status_renderer=lambda: render_preview_status_notice(snapshot),
        metrics=preview_metrics(snapshot),
        caption=preview_caption(snapshot),
        body_renderer=lambda: render_live_packet_tabs(
            packet=snapshot.preview_packet,
            preview_renderer=render_preview_frame,
            positions_xyz=snapshot.preview_trajectory_xyz,
            timestamps_s=snapshot.preview_trajectory_time_s if len(snapshot.preview_trajectory_time_s) else None,
            trajectory_empty_message="No camera trajectory is available for the selected pose source yet.",
            details_payload=cast(
                JsonObject,
                {} if snapshot.preview_packet is None else preview_frame_details(snapshot, snapshot.preview_packet),
            ),
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
        ),
    )


def preview_metrics(snapshot: DatasetPreviewSnapshot) -> tuple[LiveMetric, ...]:
    """Return compact live preview metrics."""
    packet = snapshot.preview_packet
    loop_index = 0 if packet is None else packet.loop_index
    return (
        ("Status", snapshot.state.value.upper()),
        ("Received Frames", str(snapshot.preview_frame_count)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Loop Index", str(loop_index)),
    )


def preview_caption(snapshot: DatasetPreviewSnapshot) -> str | None:
    """Return a compact preview caption for the active sequence and pose source."""
    if not snapshot.sequence_label:
        return None
    pose_label = (
        "No pose overlay"
        if snapshot.pose_source is None or snapshot.pose_source.value == "none"
        else snapshot.pose_source.label
    )
    return f"Sequence: {snapshot.sequence_label} · Pose Source: {pose_label}"


def render_preview_frame(packet: Observation) -> None:
    """Render RGB and optional depth frames for one preview observation."""
    st.markdown("**RGB Frame**")
    if packet.rgb is None:
        st.info("RGB frame is not available for the current packet.")
        return
    if packet.depth_m is None:
        render_live_image(packet.rgb, channels="RGB", clamp=True, width="stretch")
        return
    rgb_column, depth_column = st.columns(2, gap="large")
    with rgb_column:
        render_live_image(packet.rgb, channels="RGB", clamp=True, width="stretch")
    with depth_column:
        st.markdown("**Depth Frame**")
        render_live_image(packet.depth_m, clamp=True, width="stretch")


def render_preview_status_notice(snapshot: DatasetPreviewSnapshot) -> None:
    """Render preview runtime state as a Streamlit notice."""
    match snapshot.state:
        case PreviewStreamState.IDLE:
            st.info("Start a replay-ready scene to inspect looped dataset frames in-place.")
        case PreviewStreamState.CONNECTING:
            st.info("Starting dataset loop preview...")
        case PreviewStreamState.FAILED:
            st.error(snapshot.error_message or "The dataset preview failed.")
        case PreviewStreamState.DISCONNECTED:
            st.warning(snapshot.error_message or "The dataset preview ended.")
        case PreviewStreamState.STREAMING:
            if snapshot.error_message:
                st.warning(snapshot.error_message)


def preview_frame_details(snapshot: DatasetPreviewSnapshot, packet: Observation) -> JsonObject:
    """Return compact observation details for the live packet details tab."""
    pose: JsonObject | None = (
        None
        if packet.T_world_camera is None
        else {
            "qx": packet.T_world_camera.qx,
            "qy": packet.T_world_camera.qy,
            "qz": packet.T_world_camera.qz,
            "qw": packet.T_world_camera.qw,
            "tx": packet.T_world_camera.tx,
            "ty": packet.T_world_camera.ty,
            "tz": packet.T_world_camera.tz,
        }
    )
    return {
        "sequence_id": snapshot.sequence_id,
        "sequence_label": snapshot.sequence_label,
        "pose_source": None if snapshot.pose_source is None else snapshot.pose_source.value,
        "frame_index": packet.seq,
        "timestamp_ns": packet.timestamp_ns,
        "source_frame_index": packet.source_frame_index,
        "loop_index": packet.loop_index,
        "video_rotation_degrees": packet.provenance.video_rotation_degrees,
        "pose": pose,
        "provenance": cast(JsonObject, packet.provenance.compact_payload()),
    }


def preview_state_sequence_id(value: int | str | None) -> str | None:
    """Normalize legacy ADVIO integer preview IDs to normalized sequence IDs."""
    if isinstance(value, int):
        return f"advio-{value:02d}"
    return value
