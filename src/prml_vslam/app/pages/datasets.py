from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Literal

import numpy as np
import streamlit as st

import prml_vslam.plotting as plots
from prml_vslam.datasets.advio import (
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioModality,
    AdvioOfflineSample,
    AdvioPoseSource,
)
from prml_vslam.datasets.tum_rgbd import (
    TumRgbdDownloadPreset,
    TumRgbdDownloadRequest,
    TumRgbdLocalSceneStatus,
    TumRgbdModality,
    TumRgbdOfflineSample,
    TumRgbdPoseSource,
)
from prml_vslam.interfaces import CameraIntrinsics, FramePacket
from prml_vslam.utils import BaseConfig

from ..advio_controller import (
    AdvioDownloadFormData,
    AdvioPreviewFormData,
    build_advio_page_data,
    handle_advio_preview_action,
    load_advio_explorer_sample,
    sync_advio_download_state,
    sync_advio_preview_state,
)
from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_camera_intrinsics,
    render_live_action_slot,
    render_live_fragment,
    render_live_packet_tabs,
    render_live_session_shell,
    rerun_after_action,
)
from ..models import AdvioPreviewSnapshot, PreviewStreamState
from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


SequenceId = int | str
StatusList = list[AdvioLocalSceneStatus] | list[TumRgbdLocalSceneStatus]


@dataclass(slots=True)
class _DownloadFormData:
    request: BaseConfig
    submitted: bool = False


@dataclass(slots=True)
class _PageData:
    summary: object
    statuses: list[object]
    rows: list[dict[str, object]]
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message: str = ""


def render(context: AppContext) -> None:
    render_page_intro(
        eyebrow="Dataset Management",
        title="Datasets",
        body="Inspect committed scene catalogs, check local availability, download focused bundles, and loop replay-ready scenes inside the workbench.",
    )
    advio_tab, tum_tab = st.tabs(["ADVIO", "TUM RGB-D"])
    with advio_tab:
        _render_advio_tab(context)
    with tum_tab:
        _render_tum_rgbd_tab(context)


def _render_advio_tab(context: AppContext) -> None:
    sync_advio_preview_state(context)
    form = _render_download_card(
        dataset_root=context.advio_service.dataset_root,
        download_label="ADVIO",
        render_form=lambda: _render_advio_download_form(context),
    )
    with st.spinner("Downloading selected ADVIO scenes...") if form.submitted else nullcontext():
        page_data = build_advio_page_data(context, form)
    _render_notice(page_data.notice_level, page_data.notice_message)
    upstream = context.advio_service.catalog.upstream
    _render_links(
        (
            ("Official Repo", upstream.repo_url),
            ("Zenodo Record", upstream.zenodo_record_url),
            ("DOI", f"https://doi.org/{upstream.doi}"),
        )
    )
    st.caption(
        "Scene and archive metadata in this page is pinned from the official ADVIO repository and Zenodo release."
    )
    _render_summary_metrics(page_data.summary)
    _render_advio_overview(page_data.statuses)
    _render_advio_sequence_explorer(context, page_data.statuses)
    _render_advio_loop_preview(context, page_data.statuses)
    _render_catalog(page_data.rows)


def _render_tum_rgbd_tab(context: AppContext) -> None:
    _sync_tum_rgbd_preview_state(context)
    form = _render_download_card(
        dataset_root=context.tum_rgbd_service.dataset_root,
        download_label="TUM RGB-D",
        render_form=lambda: _render_tum_rgbd_download_form(context),
    )
    with st.spinner("Downloading selected TUM RGB-D scenes...") if form.submitted else nullcontext():
        page_data = _build_tum_rgbd_page_data(context, form)
    _render_notice(page_data.notice_level, page_data.notice_message)
    upstream = context.tum_rgbd_service.catalog.upstream
    _render_links(
        (
            ("Official Dataset", upstream["dataset_url"]),
            ("File Formats", upstream["file_formats_url"]),
            ("License", "https://creativecommons.org/licenses/by/4.0/"),
        )
    )
    st.caption("Scene metadata is pinned to the TUM RGB-D sequences used by ViSTA-SLAM evaluation scripts.")
    _render_summary_metrics(page_data.summary)
    _render_tum_rgbd_sequence_explorer(context, page_data.statuses)
    _render_tum_rgbd_loop_preview(context, page_data.statuses)
    _render_catalog(page_data.rows)


def _render_download_card(*, dataset_root: object, download_label: str, render_form: Callable[[], object]) -> object:
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{dataset_root}`")
        return render_form()


def _render_notice(level: str | None, message: str) -> None:
    if level:
        {"error": st.error, "warning": st.warning, "success": st.success}[level](message)


def _build_tum_rgbd_page_data(context: AppContext, form: _DownloadFormData) -> _PageData:
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message = ""
    if form.submitted:
        try:
            result = context.tum_rgbd_service.download(form.request)
        except Exception as exc:
            notice_level, notice_message = "error", str(exc)
        else:
            notice_level = "success"
            notice_message = (
                f"Prepared {len(result.sequence_ids)} scene(s), fetched {result.downloaded_archive_count} "
                f"archive(s), and wrote {result.written_path_count} path(s)."
            )
    statuses = context.tum_rgbd_service.local_scene_statuses()
    return _PageData(
        summary=context.tum_rgbd_service.summarize(statuses),
        statuses=statuses,
        rows=[
            {
                "Scene": status.scene.display_name,
                "Sequence": status.scene.sequence_id,
                "Category": status.scene.category,
                "Packed Size (MB)": round(status.scene.archive_size_bytes / 1e6, 1),
                "Local": status.sequence_dir is not None,
                "Replay Ready": status.replay_ready,
                "Offline Ready": status.offline_ready,
                "Local Modalities": ", ".join(modality.label for modality in status.local_modalities),
            }
            for status in statuses
        ],
        notice_level=notice_level,
        notice_message=notice_message,
    )


def _load_tum_rgbd_explorer_sample(context: AppContext, *, sequence_id: str) -> tuple[object | None, str | None]:
    save_model_updates(context.store, context.state, context.state.tum_rgbd, explorer_sequence_id=sequence_id)
    try:
        return context.tum_rgbd_service.load_local_sample(sequence_id), None
    except (FileNotFoundError, ValueError) as exc:
        return None, str(exc)


def _sync_tum_rgbd_preview_state(
    context: AppContext, snapshot: AdvioPreviewSnapshot | None = None
) -> AdvioPreviewSnapshot:
    snapshot = context.advio_runtime.snapshot() if snapshot is None else snapshot
    if context.state.tum_rgbd.preview_is_running and snapshot.state not in {
        PreviewStreamState.CONNECTING,
        PreviewStreamState.STREAMING,
    }:
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
    return snapshot


def _handle_tum_rgbd_preview_action(
    *,
    context: AppContext,
    sequence_id: str,
    pose_source: StrEnum,
    include_depth: bool,
    start_requested: bool,
    stop_requested: bool,
) -> str | None:
    save_model_updates(
        context.store,
        context.state,
        context.state.tum_rgbd,
        preview_sequence_id=sequence_id,
        preview_pose_source=pose_source,
        preview_include_depth=include_depth,
    )
    if stop_requested:
        context.advio_runtime.stop()
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
        return None
    if not start_requested:
        return None
    try:
        scene = context.tum_rgbd_service.scene(sequence_id)
        context.advio_runtime.start(
            sequence_id=sequence_id,
            sequence_label=scene.display_name,
            pose_source=pose_source,
            stream=context.tum_rgbd_service.open_preview_stream(
                sequence_id=sequence_id,
                pose_source=pose_source,
                include_depth=include_depth,
            ),
        )
    except Exception as exc:
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
        return str(exc)
    save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=True)
    save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
    return None


def _render_links(links: tuple[tuple[str, str], ...]) -> None:
    for column, (label, url) in zip(st.columns(len(links), gap="small"), links, strict=True):
        column.link_button(label, url, width="stretch")


def _render_summary_metrics(summary: object) -> None:
    metrics = (
        ("Total Scenes", summary.total_scene_count),
        ("Local Scenes", summary.local_scene_count),
        ("Replay Ready", summary.replay_ready_scene_count),
        ("Offline Ready", summary.offline_ready_scene_count),
        ("Cached Archives", summary.cached_archive_count),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, str(value))


def _render_catalog(rows: list[dict[str, object]]) -> None:
    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_advio_overview(statuses: list[AdvioLocalSceneStatus]) -> None:
    with st.container(border=True):
        st.subheader("Dataset Overview")
        st.caption(
            "These plots combine the committed ADVIO catalog with current local availability so the page stays useful before and after any downloads."
        )
        figure_rows = (
            (plots.build_scene_mix_figure(statuses), plots.build_local_readiness_figure(statuses)),
            (plots.build_crowd_density_figure(statuses), plots.build_scene_attribute_figure(statuses)),
        )
        for figures in figure_rows:
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")


def _render_advio_download_form(context: AppContext) -> AdvioDownloadFormData:
    request, submitted = _render_download_form_fields(
        form_key="advio_download_form",
        page_state=context.state.advio,
        service=context.advio_service,
        preset_type=AdvioDownloadPreset,
        modality_type=AdvioModality,
        request_type=AdvioDownloadRequest,
    )
    sync_advio_download_state(context, request)
    return AdvioDownloadFormData(request=request, submitted=submitted)


def _render_tum_rgbd_download_form(context: AppContext) -> _DownloadFormData:
    request, submitted = _render_download_form_fields(
        form_key="tum_rgbd_download_form",
        page_state=context.state.tum_rgbd,
        service=context.tum_rgbd_service,
        preset_type=TumRgbdDownloadPreset,
        modality_type=TumRgbdModality,
        request_type=TumRgbdDownloadRequest,
    )
    save_model_updates(
        context.store,
        context.state,
        context.state.tum_rgbd,
        selected_sequence_ids=request.sequence_ids,
        download_preset=request.preset,
        selected_modalities=request.modalities,
        overwrite_existing=request.overwrite,
    )
    return _DownloadFormData(request=request, submitted=submitted)


def _render_download_form_fields(
    *,
    form_key: str,
    page_state: object,
    service: object,
    preset_type: type[StrEnum],
    modality_type: type[StrEnum],
    request_type: type[BaseConfig],
) -> tuple[BaseConfig, bool]:
    presets = list(preset_type)
    with st.form(form_key, border=False):
        sequence_ids = st.multiselect(
            "Scenes",
            options=[scene.sequence_id for scene in service.catalog.scenes],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
            placeholder="Leave empty to download every scene, or choose a subset",
        )
        preset = st.selectbox(
            "Bundle",
            options=presets,
            index=presets.index(page_state.download_preset),
            format_func=lambda item: item.label,
        )
        modalities = st.multiselect(
            "Modalities Override",
            options=list(modality_type),
            default=page_state.selected_modalities,
            format_func=lambda item: item.label,
            placeholder="Leave empty to use the selected bundle",
        )
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        st.caption("Resolved bundle: " + ", ".join(item.label for item in (modalities or list(preset.modalities))))
        submitted = st.form_submit_button("Download scenes", type="primary", width="stretch")
    return request_type(sequence_ids=sequence_ids, preset=preset, modalities=modalities, overwrite=overwrite), submitted


def _render_advio_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    _render_sequence_explorer_impl(
        context=context,
        statuses=statuses,
        page_state=None if not hasattr(context, "state") else context.state.advio,
        service=None if not hasattr(context, "advio_service") else context.advio_service,
        dataset_label="ADVIO",
        load_sample=lambda selected_id: load_advio_explorer_sample(context, sequence_id=int(selected_id)),
        render_details=_render_advio_sequence_details,
    )


def _render_tum_rgbd_sequence_explorer(context: AppContext, statuses: list[TumRgbdLocalSceneStatus]) -> None:
    _render_sequence_explorer_impl(
        context=context,
        statuses=statuses,
        page_state=context.state.tum_rgbd,
        service=context.tum_rgbd_service,
        dataset_label="TUM RGB-D",
        load_sample=lambda selected_id: _load_tum_rgbd_explorer_sample(context, sequence_id=str(selected_id)),
        render_details=_render_tum_rgbd_sequence_details,
    )


def _render_sequence_explorer_impl(
    *,
    context: AppContext,
    statuses: StatusList,
    page_state: object,
    service: object,
    dataset_label: str,
    load_sample: Callable[[SequenceId], tuple[object | None, str | None]],
    render_details: Callable[[object], None],
) -> None:
    del context
    offline_ids = [status.scene.sequence_id for status in statuses if status.offline_ready]
    has_partial_scene = any(status.sequence_dir is not None and not status.offline_ready for status in statuses)
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not offline_ids:
            (st.warning if has_partial_scene else st.info)(
                f"Local {dataset_label} scenes exist, but none are offline-ready yet. Finish downloading the offline bundle for at least one scene to unlock trajectory and timing views."
                if has_partial_scene
                else f"Download at least one {dataset_label} scene to unlock trajectory and timing views."
            )
            return
        selected_id = st.selectbox(
            "Local Scene",
            options=offline_ids,
            index=offline_ids.index(
                page_state.explorer_sequence_id
                if page_state is not None and page_state.explorer_sequence_id in offline_ids
                else offline_ids[0]
            ),
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
        )
        sample, error_message = load_sample(selected_id)
        if error_message:
            st.warning(error_message)
        elif sample is not None:
            render_details(sample)


def _render_advio_sequence_details(sample: AdvioOfflineSample) -> None:
    intrinsics = sample.calibration.intrinsics
    trajectories = [("Ground Truth", sample.ground_truth), ("ARCore", sample.arcore)]
    timing = [
        ("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9),
        ("Ground Truth", np.asarray(sample.ground_truth.timestamps, dtype=np.float64)),
        ("ARCore", np.asarray(sample.arcore.timestamps, dtype=np.float64)),
    ]
    if sample.arkit is not None:
        trajectories.append(("ARKit", sample.arkit))
        timing.append(("ARKit", np.asarray(sample.arkit.timestamps, dtype=np.float64)))
    _render_sequence_details(
        duration_s=sample.duration_s,
        frame_count=int(len(sample.frame_timestamps_ns)),
        intrinsics=intrinsics,
        metrics=(("ARKit", "Available" if sample.arkit is not None else "Missing"),),
        trajectories=trajectories,
        timing=timing,
        paths=(
            ("Video", sample.paths.video_path),
            ("Timestamps", sample.paths.frame_timestamps_path),
            ("Calibration", sample.paths.calibration_path),
            ("Ground Truth", sample.paths.ground_truth_csv_path),
            ("ARCore", sample.paths.arcore_csv_path),
            ("ARKit", sample.paths.arkit_csv_path or "Missing"),
        ),
    )


def _render_tum_rgbd_sequence_details(sample: TumRgbdOfflineSample) -> None:
    _render_sequence_details(
        duration_s=sample.duration_s,
        frame_count=int(len(sample.frame_timestamps_ns)),
        intrinsics=sample.intrinsics,
        metrics=(
            ("Depth", "Available" if any(item.depth_path is not None for item in sample.associations) else "Missing"),
        ),
        trajectories=[("Ground Truth", sample.ground_truth)],
        timing=[
            ("RGB Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9),
            ("Ground Truth", np.asarray(sample.ground_truth.timestamps, dtype=np.float64)),
        ],
        paths=(
            ("RGB List", sample.paths.rgb_list_path),
            ("Depth List", sample.paths.depth_list_path or "Missing"),
            ("Ground Truth", sample.paths.ground_truth_path),
        ),
    )


def _render_sequence_details(
    *,
    duration_s: float,
    frame_count: int,
    intrinsics: CameraIntrinsics,
    metrics: tuple[tuple[str, str], ...],
    trajectories: list[tuple[str, object]],
    timing: list[tuple[str, np.ndarray]],
    paths: tuple[tuple[str, object], ...],
) -> None:
    mean_fps = 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)
    metric_values = (
        ("Duration", f"{duration_s:.1f} s"),
        ("Frames", str(frame_count)),
        ("Mean FPS", f"{mean_fps:.2f}"),
        ("GT Path Length", f"{plots.trajectory_length_m(trajectories[0][1]):.1f} m"),
        *metrics,
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metric_values, strict=True):
        column.metric(label, value)
    st.caption(
        f"Camera: {intrinsics.width_px}×{intrinsics.height_px}px, fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}, cx={intrinsics.cx:.1f}, cy={intrinsics.cy:.1f}"
    )
    tabs = st.tabs(["Trajectories", "Motion", "Timing", "Camera"])
    figure_rows = (
        (
            plots.build_bev_trajectory_figure(trajectories),
            plots.build_3d_trajectory_figure(trajectories, pose_axes_name="Ground Truth", pose_axis_stride=30),
        ),
        (plots.build_speed_profile_figure(trajectories), plots.build_height_profile_figure(trajectories)),
        (
            plots.build_sample_interval_figure(timing),
            plots.build_sample_interval_figure(timing[1:], title="Trajectory Cadence"),
        ),
    )
    for tab, figures in zip(tabs[:3], figure_rows, strict=True):
        with tab:
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")
    with tabs[3]:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            render_camera_intrinsics(
                intrinsics=intrinsics,
                missing_message="Camera intrinsics are not available for the current sample.",
            )
        with right:
            st.markdown("**Modalities and Paths**")
            st.markdown("\n".join(f"- {label}: `{value}`" for label, value in paths))


def _render_advio_loop_preview(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    _render_loop_preview_impl(
        statuses=statuses,
        page_state=context.state.advio,
        service=context.advio_service,
        pose_source_type=AdvioPoseSource,
        caption="Run a replay-ready ADVIO scene in a local loop with the existing CV2 producer and inspect frames, trajectory, and camera metadata live.",
        option_label="Respect video rotation metadata",
        option_attr="preview_respect_video_rotation",
        action=lambda selected_id, pose_source, option_value, start, stop: handle_advio_preview_action(
            context,
            AdvioPreviewFormData(
                sequence_id=int(selected_id),
                pose_source=pose_source,
                respect_video_rotation=option_value,
                start_requested=start,
                stop_requested=stop,
            ),
        ),
        sync_snapshot=lambda: sync_advio_preview_state(context),
    )


def _render_tum_rgbd_loop_preview(context: AppContext, statuses: list[TumRgbdLocalSceneStatus]) -> None:
    _render_loop_preview_impl(
        statuses=statuses,
        page_state=context.state.tum_rgbd,
        service=context.tum_rgbd_service,
        pose_source_type=TumRgbdPoseSource,
        caption="Run a replay-ready TUM RGB-D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
        option_label="Include depth frames",
        option_attr="preview_include_depth",
        action=lambda selected_id, pose_source, option_value, start, stop: _handle_tum_rgbd_preview_action(
            context=context,
            sequence_id=str(selected_id),
            pose_source=pose_source,
            include_depth=option_value,
            start_requested=start,
            stop_requested=stop,
        ),
        sync_snapshot=lambda: _sync_tum_rgbd_preview_state(context),
    )


def _render_loop_preview_impl(
    *,
    statuses: StatusList,
    page_state: object,
    service: object,
    pose_source_type: type[StrEnum],
    caption: str,
    option_label: str,
    option_attr: str,
    action: Callable[[SequenceId, StrEnum, bool, bool, bool], str | None],
    sync_snapshot: Callable[[], AdvioPreviewSnapshot],
) -> None:
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption(caption)
        if not previewable_ids:
            st.info("Download the streaming bundle for at least one scene to unlock loop preview.")
            return
        selected_id = (
            page_state.preview_sequence_id if page_state.preview_sequence_id in previewable_ids else previewable_ids[0]
        )
        pose_source = page_state.preview_pose_source
        selected_id = st.selectbox(
            "Preview Scene",
            options=previewable_ids,
            index=previewable_ids.index(selected_id),
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
        )
        pose_source = st.selectbox(
            "Pose Source",
            options=list(pose_source_type),
            index=list(pose_source_type).index(pose_source),
            format_func=lambda item: item.label,
        )
        option_value = st.toggle(option_label, value=getattr(page_state, option_attr))
        start_requested, stop_requested = render_live_action_slot(
            is_active=page_state.preview_is_running,
            start_label="Start preview",
            stop_label="Stop preview",
        )
        error_message = action(selected_id, pose_source, option_value, start_requested, stop_requested)
        if rerun_after_action(action_requested=start_requested or stop_requested, error_message=error_message):
            return
        if error_message:
            st.error(error_message)
        render_live_fragment(
            run_every=live_poll_interval(is_active=page_state.preview_is_running, interval_seconds=0.2),
            render_body=lambda: _render_preview_snapshot(sync_snapshot()),
        )


def _render_preview_snapshot(snapshot: AdvioPreviewSnapshot) -> None:
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_preview_status_notice(snapshot),
        metrics=_preview_metrics(snapshot),
        caption=_preview_caption(snapshot),
        body_renderer=lambda: render_live_packet_tabs(
            packet=snapshot.latest_packet,
            preview_renderer=_render_preview_frame,
            positions_xyz=snapshot.trajectory_positions_xyz,
            timestamps_s=snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
            trajectory_empty_message="No camera trajectory is available for the selected pose source yet.",
            details_payload={}
            if snapshot.latest_packet is None
            else _preview_frame_details(snapshot, snapshot.latest_packet),
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
        ),
    )


def _preview_metrics(snapshot: AdvioPreviewSnapshot) -> tuple[LiveMetric, ...]:
    packet = snapshot.latest_packet
    loop_index = 0 if packet is None else int(packet.metadata.get("loop_index", 0))
    return (
        ("Status", snapshot.state.value.upper()),
        ("Received Frames", str(snapshot.received_frames)),
        ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"),
        ("Loop Index", str(loop_index)),
    )


def _preview_caption(snapshot: AdvioPreviewSnapshot) -> str | None:
    if not snapshot.sequence_label:
        return None
    pose_label = (
        "No pose overlay"
        if snapshot.pose_source is None or snapshot.pose_source.value == "none"
        else snapshot.pose_source.label
    )
    return f"Sequence: {snapshot.sequence_label} · Pose Source: {pose_label}"


def _render_preview_frame(packet: FramePacket) -> None:
    st.markdown("**RGB Frame**")
    st.image(packet.rgb, channels="RGB", clamp=True)
    if packet.depth is not None:
        st.markdown("**Depth Frame**")
        st.image(packet.depth, clamp=True)


def _render_preview_status_notice(snapshot: AdvioPreviewSnapshot) -> None:
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


def _preview_frame_details(snapshot: AdvioPreviewSnapshot, packet: FramePacket) -> dict[str, object]:
    pose = (
        None
        if packet.pose is None
        else {
            "qx": packet.pose.qx,
            "qy": packet.pose.qy,
            "qz": packet.pose.qz,
            "qw": packet.pose.qw,
            "tx": packet.pose.tx,
            "ty": packet.pose.ty,
            "tz": packet.pose.tz,
        }
    )
    return {
        "sequence_id": snapshot.sequence_id,
        "sequence_label": snapshot.sequence_label,
        "pose_source": None if snapshot.pose_source is None else snapshot.pose_source.value,
        "frame_index": packet.seq,
        "timestamp_ns": packet.timestamp_ns,
        "source_frame_index": packet.metadata.get("source_frame_index"),
        "loop_index": packet.metadata.get("loop_index", 0),
        "video_rotation_degrees": packet.metadata.get("video_rotation_degrees", 0),
        "rgb_path": packet.metadata.get("rgb_path"),
        "depth_path": packet.metadata.get("depth_path"),
        "pose": pose,
        "metadata": packet.metadata,
    }
