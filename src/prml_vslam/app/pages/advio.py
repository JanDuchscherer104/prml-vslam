"""ADVIO Streamlit page for dataset discovery, downloads, and loop preview."""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from prml_vslam.datasets import AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import (
    AdvioDownloadPreset,
    AdvioModality,
    AdvioOfflineSample,
    AdvioPoseSource,
)
from prml_vslam.io.interfaces import VideoFramePacket

from .. import plotting as plots
from ..advio_controller import (
    AdvioDownloadFormData,
    AdvioPreviewFormData,
    build_advio_page_data,
    handle_advio_preview_action,
    sync_advio_preview_state,
)
from ..camera_display import format_camera_intrinsics_latex
from ..services import AdvioPreviewSnapshot, AdvioPreviewStreamState
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


# fmt: off
def render(context: AppContext) -> None:
    render_page_intro(
        eyebrow="Dataset Management",
        title="ADVIO Dataset",
        body="Inspect the committed ADVIO scene catalog, check what is already available locally, download only the needed bundles, and loop a replay-ready scene inside the workbench.",
    )
    sync_advio_preview_state(context)
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{context.advio_service.dataset_root}`")
        form = _render_download_form(context)
    with st.spinner("Downloading selected ADVIO scenes...") if form.submitted else nullcontext():
        page_data = build_advio_page_data(context, form)
    if page_data.notice_level:
        {"error": st.error, "warning": st.warning, "success": st.success}[page_data.notice_level](page_data.notice_message)
    upstream = context.advio_service.catalog.upstream
    links = (("Official Repo", upstream.repo_url), ("Zenodo Record", upstream.zenodo_record_url), ("DOI", f"https://doi.org/{upstream.doi}"))
    for column, (label, url) in zip(st.columns(3, gap="small"), links, strict=True):
        column.link_button(label, url, width="stretch")
    st.caption("Scene and archive metadata in this page is pinned from the official ADVIO repository and Zenodo release.")
    metrics = (("Total Scenes", page_data.summary.total_scene_count), ("Local Scenes", page_data.summary.local_scene_count), ("Replay Ready", page_data.summary.replay_ready_scene_count), ("Offline Ready", page_data.summary.offline_ready_scene_count), ("Cached Archives", page_data.summary.cached_archive_count))
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, str(value))
    with st.container(border=True):
        st.subheader("Dataset Overview")
        st.caption("These plots combine the committed ADVIO catalog with current local availability so the page stays useful before and after any downloads.")
        figure_rows = ((plots.build_scene_mix_figure(page_data.statuses), plots.build_local_readiness_figure(page_data.statuses)), (plots.build_crowd_density_figure(page_data.statuses), plots.build_scene_attribute_figure(page_data.statuses)))
        for figures in figure_rows:
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")
    _render_sequence_explorer(context, page_data.statuses)
    _render_loop_preview(context, page_data.statuses)
    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(page_data.rows, hide_index=True, width="stretch")


def _render_download_form(context: AppContext) -> AdvioDownloadFormData:
    page_state, service = context.state.advio, context.advio_service
    with st.form("advio_download_form", border=False):
        sequence_ids = st.multiselect("Scenes", options=[scene.sequence_id for scene in service.list_scenes()], default=page_state.selected_sequence_ids, format_func=lambda sequence_id: service.scene(sequence_id).display_name, placeholder="Choose one or more scenes to download")
        preset = st.selectbox("Bundle", options=list(AdvioDownloadPreset), index=list(AdvioDownloadPreset).index(page_state.download_preset), format_func=lambda item: item.label)
        modalities = st.multiselect("Modalities Override", options=list(AdvioModality), default=page_state.selected_modalities, format_func=lambda item: item.label, placeholder="Leave empty to use the selected bundle")
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        st.caption("Resolved bundle: " + ", ".join(item.label for item in (modalities or list(preset.modalities))))
        submitted = st.form_submit_button("Download selected scenes", type="primary", width="stretch")
    _set_page_state(context, selected_sequence_ids=sequence_ids, download_preset=preset, selected_modalities=modalities, overwrite_existing=overwrite)
    return AdvioDownloadFormData(request=AdvioDownloadRequest(sequence_ids=sequence_ids, preset=preset, modalities=modalities, overwrite=overwrite), submitted=submitted)


def _render_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    offline_ids = [status.scene.sequence_id for status in statuses if status.offline_ready]
    has_partial_scene = any(status.sequence_dir is not None and not status.offline_ready for status in statuses)
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not offline_ids:
            (st.warning if has_partial_scene else st.info)("Local ADVIO scenes exist, but none are offline-ready yet. Finish downloading the offline bundle for at least one scene to unlock trajectory and timing views." if has_partial_scene else "Download at least one ADVIO scene to unlock trajectory and timing views.")
            return
        service = context.advio_service
        selected_id = st.selectbox("Local Scene", options=offline_ids, index=offline_ids.index(_selected(page_state_id=context.state.advio.explorer_sequence_id, options=offline_ids)), format_func=lambda sequence_id: service.scene(sequence_id).display_name)
        _set_page_state(context, explorer_sequence_id=selected_id)
        try:
            _render_sequence_details(service.load_local_sample(selected_id))
        except (FileNotFoundError, ValueError) as exc:
            st.warning(str(exc))


def _render_sequence_details(sample: AdvioOfflineSample) -> None:
    duration_s, frame_count, intrinsics = sample.duration_s, int(len(sample.frame_timestamps_ns)), sample.calibration.intrinsics
    mean_fps = 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)
    metrics = (("Duration", f"{duration_s:.1f} s"), ("Frames", str(frame_count)), ("Mean FPS", f"{mean_fps:.2f}"), ("GT Path Length", f"{plots.trajectory_length_m(sample.ground_truth):.1f} m"), ("ARKit", "Available" if sample.arkit is not None else "Missing"))
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, value)
    st.caption(f"Camera: {intrinsics.width_px}×{intrinsics.height_px}px, fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}, cx={intrinsics.cx:.1f}, cy={intrinsics.cy:.1f}")
    trajectories = [("Ground Truth", sample.ground_truth), ("ARCore", sample.arcore)]
    timing = [("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9), ("Ground Truth", sample.ground_truth.timestamps_s), ("ARCore", sample.arcore.timestamps_s)]
    if sample.arkit is not None:
        trajectories.append(("ARKit", sample.arkit))
        timing.append(("ARKit", sample.arkit.timestamps_s))
    tabs = st.tabs(["Trajectories", "Motion", "Timing", "Camera"])
    figure_rows = ((plots.build_bev_trajectory_figure(trajectories), plots.build_3d_trajectory_figure(trajectories, pose_axes_name="Ground Truth", pose_axis_stride=30)), (plots.build_speed_profile_figure(trajectories), plots.build_height_profile_figure(trajectories)), (plots.build_sample_interval_figure(timing), plots.build_sample_interval_figure(timing[1:], title="Trajectory Cadence")))
    for tab, figures in zip(tabs[:3], figure_rows, strict=True):
        with tab:
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")
    with tabs[3]:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            st.latex(format_camera_intrinsics_latex(fx=intrinsics.fx, fy=intrinsics.fy, cx=intrinsics.cx, cy=intrinsics.cy))
        with right:
            st.markdown("**Modalities and Paths**")
            st.markdown("\n".join(f"- {label}: `{value}`" for label, value in (("Video", sample.paths.video_path), ("Timestamps", sample.paths.frame_timestamps_path), ("Calibration", sample.paths.calibration_path), ("Ground Truth", sample.paths.ground_truth_csv_path), ("ARCore", sample.paths.arcore_csv_path), ("ARKit", sample.paths.arkit_csv_path or "Missing"))))


def _render_loop_preview(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption("Run a replay-ready ADVIO scene in a local loop with the existing CV2 producer and inspect frames, trajectory, and camera metadata live.")
        if not previewable_ids:
            st.info("Download the streaming bundle for at least one scene to unlock loop preview.")
            return
        page_state, service = context.state.advio, context.advio_service
        selected_id = _selected(page_state_id=page_state.preview_sequence_id, options=previewable_ids)
        pose_source = page_state.preview_pose_source
        with st.form("advio_preview_form", border=False):
            selected_id = st.selectbox("Preview Scene", options=previewable_ids, index=previewable_ids.index(selected_id), format_func=lambda sequence_id: service.scene(sequence_id).display_name)
            pose_source = st.selectbox("Pose Source", options=list(AdvioPoseSource), index=list(AdvioPoseSource).index(pose_source), format_func=_pose_source_label)
            respect_video_rotation = st.toggle("Respect video rotation metadata", value=page_state.preview_respect_video_rotation)
            start_requested = st.form_submit_button("Start preview" if not page_state.preview_is_running else "Restart preview", type="primary", use_container_width=True)
        stop_requested = st.button("Stop preview", disabled=not page_state.preview_is_running, use_container_width=True)
        _set_page_state(context, preview_sequence_id=selected_id, preview_pose_source=pose_source, preview_respect_video_rotation=respect_video_rotation)
        error_message = handle_advio_preview_action(context, AdvioPreviewFormData(sequence_id=selected_id, pose_source=pose_source, respect_video_rotation=respect_video_rotation, start_requested=start_requested, stop_requested=stop_requested))
        if error_message:
            st.error(error_message)
        _render_loop_snapshot(context)


def _render_loop_snapshot(context: AppContext) -> None:
    @st.fragment(run_every=0.2 if context.state.advio.preview_is_running else None)
    def _render_fragment() -> None:
        _render_preview_snapshot(sync_advio_preview_state(context))
    _render_fragment()


def _render_preview_snapshot(snapshot: AdvioPreviewSnapshot) -> None:
    _render_preview_status_notice(snapshot)
    packet = snapshot.latest_packet
    loop_index = 0 if packet is None else int(packet.metadata.get("loop_index", 0))
    metrics = (("Status", snapshot.state.value.upper()), ("Received Frames", str(snapshot.received_frames)), ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"), ("Loop Index", str(loop_index)))
    for column, (label, value) in zip(st.columns(4, gap="small"), metrics, strict=True):
        column.metric(label, value)
    if snapshot.sequence_label:
        st.caption(f"Sequence: {snapshot.sequence_label} · Pose Source: {'No pose overlay' if snapshot.pose_source is AdvioPoseSource.NONE else _pose_source_label(snapshot.pose_source)}")
    if packet is None:
        return
    preview_tab, trajectory_tab, camera_tab = st.tabs(["Frames", "Trajectory", "Camera"])
    with preview_tab:
        st.markdown("**RGB Frame**")
        st.image(packet.rgb, channels="RGB", clamp=True)
    with trajectory_tab:
        if len(snapshot.trajectory_positions_xyz) == 0:
            st.info("No camera trajectory is available for the selected pose source yet.")
        else:
            st.plotly_chart(plots.build_live_trajectory_figure(snapshot.trajectory_positions_xyz, snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None), width="stretch")
    with camera_tab:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            if packet.intrinsics is None:
                st.info("Camera intrinsics are not available for the current packet.")
            else:
                st.latex(format_camera_intrinsics_latex(fx=packet.intrinsics.fx, fy=packet.intrinsics.fy, cx=packet.intrinsics.cx, cy=packet.intrinsics.cy))
        with right:
            st.markdown("**Frame Details**")
            st.json(_preview_frame_details(snapshot, packet), expanded=False)


def _render_preview_status_notice(snapshot: AdvioPreviewSnapshot) -> None:
    match snapshot.state:
        case AdvioPreviewStreamState.IDLE:
            st.info("Start a replay-ready scene to inspect looped ADVIO frames in-place.")
        case AdvioPreviewStreamState.CONNECTING:
            st.info("Starting ADVIO loop preview...")
        case AdvioPreviewStreamState.FAILED:
            st.error(snapshot.error_message or "The ADVIO preview failed.")
        case AdvioPreviewStreamState.DISCONNECTED:
            st.warning(snapshot.error_message or "The ADVIO preview ended.")
        case AdvioPreviewStreamState.STREAMING:
            if snapshot.error_message:
                st.warning(snapshot.error_message)


def _set_page_state(context: AppContext, **updates: object) -> None:
    page_state = context.state.advio
    if all(getattr(page_state, key) == value for key, value in updates.items()):
        return
    for key, value in updates.items():
        setattr(page_state, key, value)
    context.store.save(context.state)


def _selected(*, page_state_id: int | None, options: list[int]) -> int:
    return page_state_id if page_state_id in options else options[0]
def _pose_source_label(pose_source: AdvioPoseSource | None) -> str:
    return {AdvioPoseSource.GROUND_TRUTH: "Ground Truth", AdvioPoseSource.ARCORE: "ARCore", AdvioPoseSource.ARKIT: "ARKit", AdvioPoseSource.NONE: "No Pose Overlay", None: "No Pose Overlay"}[pose_source]


def _preview_frame_details(snapshot: AdvioPreviewSnapshot, packet: VideoFramePacket) -> dict[str, object]:
    camera_pose = None if packet.camera_pose is None else {"qx": packet.camera_pose.qx, "qy": packet.camera_pose.qy, "qz": packet.camera_pose.qz, "qw": packet.camera_pose.qw, "tx": packet.camera_pose.tx, "ty": packet.camera_pose.ty, "tz": packet.camera_pose.tz}
    return {"sequence_id": snapshot.sequence_id, "sequence_label": snapshot.sequence_label, "pose_source": None if snapshot.pose_source is None else snapshot.pose_source.value, "frame_index": packet.frame_index, "timestamp_ns": packet.timestamp_ns, "source_frame_index": packet.metadata.get("source_frame_index"), "loop_index": packet.metadata.get("loop_index", 0), "video_rotation_degrees": packet.metadata.get("video_rotation_degrees", 0), "camera_pose": camera_pose, "metadata": packet.metadata}
# fmt: on
