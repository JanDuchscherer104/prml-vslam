"""ADVIO Streamlit page for dataset discovery, downloads, and loop preview."""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

import numpy as np
import streamlit as st

from prml_vslam.datasets import AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import (
    AdvioDownloadPreset,
    AdvioModality,
    AdvioOfflineSample,
    AdvioPoseSource,
    AdvioSequence,
    AdvioSequenceConfig,
)
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.io.interfaces import PinholeCameraIntrinsics, VideoFramePacket

from .. import plotting as plots
from ..advio_controller import AdvioDownloadFormData, build_advio_page_data
from ..services import AdvioPreviewSnapshot, AdvioPreviewStreamState
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_ACTIVE_PREVIEW_STATES = {
    AdvioPreviewStreamState.CONNECTING,
    AdvioPreviewStreamState.STREAMING,
}


# fmt: off
def render(context: AppContext) -> None:
    """Render the dedicated ADVIO dataset-management page."""
    render_page_intro(
        eyebrow="Dataset Management",
        title="ADVIO Dataset",
        body=(
            "Inspect the committed ADVIO scene catalog, check what is already available locally, download "
            "only the needed bundles, and loop a replay-ready scene inside the workbench."
        ),
    )
    _sync_preview_running_state(context)
    service = context.advio_service
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{service.dataset_root}`")
        download_form = _render_download_form(context)
    with st.spinner("Downloading selected ADVIO scenes...") if download_form.submitted else nullcontext():
        page_data = build_advio_page_data(context, download_form)
    notice_renderer = {"error": st.error, "warning": st.warning, "success": st.success}.get(page_data.notice_level)
    if notice_renderer is not None:
        notice_renderer(page_data.notice_message)
    upstream = service.catalog.upstream
    for column, (label, url) in zip(st.columns(3, gap="small"), (("Official Repo", upstream.repo_url), ("Zenodo Record", upstream.zenodo_record_url), ("DOI", f"https://doi.org/{upstream.doi}")), strict=True):
        column.link_button(label, url, width="stretch")
    st.caption("Scene and archive metadata in this page is pinned from the official ADVIO repository and Zenodo release.")
    for column, (label, value) in zip(st.columns(5, gap="small"), (("Total Scenes", page_data.summary.total_scene_count), ("Local Scenes", page_data.summary.local_scene_count), ("Replay Ready", page_data.summary.replay_ready_scene_count), ("Offline Ready", page_data.summary.offline_ready_scene_count), ("Cached Archives", page_data.summary.cached_archive_count)), strict=True):
        column.metric(label, str(value))
    with st.container(border=True):
        st.subheader("Dataset Overview")
        st.caption("These plots combine the committed ADVIO catalog with current local availability so the page stays useful before and after any downloads.")
        for figures in ((plots.build_scene_mix_figure(page_data.statuses), plots.build_local_readiness_figure(page_data.statuses)), (plots.build_crowd_density_figure(page_data.statuses), plots.build_scene_attribute_figure(page_data.statuses))):
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")
    _render_sequence_explorer(context, page_data.statuses)
    _render_loop_preview(context, page_data.statuses)
    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(page_data.rows, hide_index=True, width="stretch")


def _render_download_form(context: AppContext) -> AdvioDownloadFormData:
    page_state = context.state.advio
    service = context.advio_service
    with st.form("advio_download_form", border=False):
        selected_scene_ids = st.multiselect("Scenes", options=[scene.sequence_id for scene in service.list_scenes()], default=page_state.selected_sequence_ids, format_func=lambda sequence_id: service.scene(sequence_id).display_name, placeholder="Choose one or more scenes to download")
        selected_preset = st.selectbox("Bundle", options=list(AdvioDownloadPreset), index=list(AdvioDownloadPreset).index(page_state.download_preset), format_func=lambda preset: preset.label)
        selected_modalities = st.multiselect("Modalities Override", options=list(AdvioModality), default=page_state.selected_modalities, format_func=lambda modality: modality.label, placeholder="Leave empty to use the selected bundle")
        overwrite_existing = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        effective_modalities = selected_modalities or list(selected_preset.modalities)
        st.caption("Resolved bundle: " + ", ".join(modality.label for modality in effective_modalities))
        submitted = st.form_submit_button("Download selected scenes", type="primary", width="stretch")
    page_state.selected_sequence_ids = selected_scene_ids
    page_state.download_preset = selected_preset
    page_state.selected_modalities = selected_modalities
    page_state.overwrite_existing = overwrite_existing
    context.store.save(context.state)
    return AdvioDownloadFormData(request=AdvioDownloadRequest(sequence_ids=selected_scene_ids, preset=selected_preset, modalities=selected_modalities, overwrite=overwrite_existing), submitted=submitted)


def _render_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    local_samples: dict[int, AdvioOfflineSample] = {}
    has_partial_scene = False
    service = context.advio_service
    for status in statuses:
        if status.sequence_dir is None:
            continue
        try:
            local_samples[status.scene.sequence_id] = service.load_local_sample(status.scene.sequence_id)
        except (FileNotFoundError, ValueError):
            has_partial_scene = True
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not local_samples:
            (st.warning if has_partial_scene else st.info)(
                "Local ADVIO scenes exist, but none are offline-ready yet. Finish downloading the offline bundle for at least one scene to unlock trajectory and timing views."
                if has_partial_scene
                else "Download at least one ADVIO scene to unlock trajectory and timing views."
            )
            return
        page_state = context.state.advio
        local_sequence_ids = list(local_samples)
        selected_sequence_id = page_state.explorer_sequence_id if page_state.explorer_sequence_id in local_sequence_ids else local_sequence_ids[0]
        selected_sequence_id = st.selectbox("Local Scene", options=local_sequence_ids, index=local_sequence_ids.index(selected_sequence_id), format_func=lambda sequence_id: service.scene(sequence_id).display_name)
        if page_state.explorer_sequence_id != selected_sequence_id:
            page_state.explorer_sequence_id = selected_sequence_id
            context.store.save(context.state)
        _render_sequence_details(local_samples[selected_sequence_id])


def _render_sequence_details(sample: AdvioOfflineSample) -> None:
    duration_s = sample.duration_s
    frame_count = int(len(sample.frame_timestamps_ns))
    mean_fps = 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)
    intrinsics = sample.calibration.intrinsics
    for column, (label, value) in zip(st.columns(5, gap="small"), (("Duration", f"{duration_s:.1f} s"), ("Frames", str(frame_count)), ("Mean FPS", f"{mean_fps:.2f}"), ("GT Path Length", f"{plots.trajectory_length_m(sample.ground_truth):.1f} m"), ("ARKit", "Available" if sample.arkit is not None else "Missing")), strict=True):
        column.metric(label, value)
    st.caption(f"Camera: {intrinsics.width_px}×{intrinsics.height_px}px, fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}, cx={intrinsics.cx:.1f}, cy={intrinsics.cy:.1f}")
    trajectory_series = [("Ground Truth", sample.ground_truth), ("ARCore", sample.arcore)]
    timing_series = [("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9), ("Ground Truth", sample.ground_truth.timestamps_s), ("ARCore", sample.arcore.timestamps_s)]
    if sample.arkit is not None:
        trajectory_series.append(("ARKit", sample.arkit))
        timing_series.append(("ARKit", sample.arkit.timestamps_s))
    tabs = st.tabs(["Trajectories", "Motion", "Timing", "Camera"])
    for tab, figures in zip(tabs[:3], ((plots.build_bev_trajectory_figure(trajectory_series), plots.build_3d_trajectory_figure(trajectory_series, pose_axes_name="Ground Truth", pose_axis_stride=30)), (plots.build_speed_profile_figure(trajectory_series), plots.build_height_profile_figure(trajectory_series)), (plots.build_sample_interval_figure(timing_series), plots.build_sample_interval_figure(timing_series[1:], title="Trajectory Cadence"))), strict=True):
        with tab:
            for column, figure in zip(st.columns(2, gap="large"), figures, strict=True):
                column.plotly_chart(figure, width="stretch")
    with tabs[3]:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            st.latex(_format_intrinsics(intrinsics))
        with right:
            st.markdown("**Modalities and Paths**")
            st.markdown("\n".join(f"- {label}: `{value}`" for label, value in (("Video", sample.paths.video_path), ("Timestamps", sample.paths.frame_timestamps_path), ("Calibration", sample.paths.calibration_path), ("Ground Truth", sample.paths.ground_truth_csv_path), ("ARCore", sample.paths.arcore_csv_path), ("ARKit", sample.paths.arkit_csv_path or "Missing"))))


def _render_loop_preview(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    service = context.advio_service
    page_state = context.state.advio
    previewable_statuses = [status for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption("Run a replay-ready ADVIO scene in a local loop with the existing CV2 producer and inspect frames, trajectory, and camera metadata live.")
        if not previewable_statuses:
            st.info("Download the streaming bundle for at least one scene to unlock loop preview.")
            return

        preview_sequence_ids = [status.scene.sequence_id for status in previewable_statuses]
        selected_sequence_id = page_state.preview_sequence_id if page_state.preview_sequence_id in preview_sequence_ids else preview_sequence_ids[0]
        selected_pose_source = page_state.preview_pose_source
        with st.form("advio_preview_form", border=False):
            selected_sequence_id = st.selectbox("Preview Scene", options=preview_sequence_ids, index=preview_sequence_ids.index(selected_sequence_id), format_func=lambda sequence_id: service.scene(sequence_id).display_name)
            selected_pose_source = st.selectbox("Pose Source", options=list(AdvioPoseSource), index=list(AdvioPoseSource).index(selected_pose_source), format_func=_pose_source_label)
            respect_video_rotation = st.toggle("Respect video rotation metadata", value=page_state.preview_respect_video_rotation)
            start_requested = st.form_submit_button("Start preview" if not page_state.preview_is_running else "Restart preview", type="primary", use_container_width=True)

        stop_requested = st.button("Stop preview", disabled=not page_state.preview_is_running, use_container_width=True)
        page_state.preview_sequence_id = selected_sequence_id
        page_state.preview_pose_source = selected_pose_source
        page_state.preview_respect_video_rotation = respect_video_rotation
        context.store.save(context.state)

        if start_requested:
            try:
                scene = service.scene(selected_sequence_id)
                stream = AdvioSequence(
                    config=AdvioSequenceConfig(dataset_root=service.dataset_root, sequence_id=selected_sequence_id),
                    catalog=service.catalog,
                ).open_stream(
                    pose_source=selected_pose_source,
                    loop=True,
                    replay_mode=Cv2ReplayMode.REALTIME,
                    respect_video_rotation=respect_video_rotation,
                )
                context.advio_runtime.start(
                    sequence_id=selected_sequence_id,
                    sequence_label=scene.display_name,
                    pose_source=selected_pose_source,
                    stream=stream,
                )
                page_state.preview_is_running = True
                context.store.save(context.state)
            except Exception as exc:
                page_state.preview_is_running = False
                context.store.save(context.state)
                st.error(str(exc))

        if stop_requested:
            context.advio_runtime.stop()
            page_state.preview_is_running = False
            context.store.save(context.state)

        _render_loop_snapshot(context)


def _sync_preview_running_state(
    context: AppContext,
    snapshot: AdvioPreviewSnapshot | None = None,
) -> AdvioPreviewSnapshot:
    current_snapshot = context.advio_runtime.snapshot() if snapshot is None else snapshot
    if context.state.advio.preview_is_running and current_snapshot.state not in _ACTIVE_PREVIEW_STATES:
        context.state.advio.preview_is_running = False
        context.store.save(context.state)
    return current_snapshot


def _render_loop_snapshot(context: AppContext) -> None:
    page_state = context.state.advio

    @st.fragment(run_every=0.2 if page_state.preview_is_running else None)
    def _render_fragment() -> None:
        snapshot = _sync_preview_running_state(context)
        _render_preview_snapshot(snapshot)

    _render_fragment()


def _render_preview_snapshot(snapshot: AdvioPreviewSnapshot) -> None:
    _render_preview_status_notice(snapshot)
    packet = snapshot.latest_packet
    loop_index = 0 if packet is None else int(packet.metadata.get("loop_index", 0))
    for column, (label, value) in zip(st.columns(4, gap="small"), (("Status", snapshot.state.value.upper()), ("Received Frames", str(snapshot.received_frames)), ("Frame Rate", f"{snapshot.measured_fps:.2f} fps"), ("Loop Index", str(loop_index))), strict=True):
        column.metric(label, value)
    if snapshot.sequence_label:
        pose_label = "No pose overlay" if snapshot.pose_source is AdvioPoseSource.NONE else _pose_source_label(snapshot.pose_source)
        st.caption(f"Sequence: {snapshot.sequence_label} · Pose Source: {pose_label}")
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
            st.plotly_chart(
                plots.build_live_trajectory_figure(
                    snapshot.trajectory_positions_xyz,
                    snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
                ),
                width="stretch",
            )
    with camera_tab:
        intrinsics_col, details_col = st.columns((0.9, 1.1), gap="large")
        with intrinsics_col:
            st.markdown("**Camera Intrinsics**")
            if packet.intrinsics is None:
                st.info("Camera intrinsics are not available for the current packet.")
            else:
                st.latex(_format_intrinsics(packet.intrinsics))
        with details_col:
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


def _format_intrinsics(intrinsics: PinholeCameraIntrinsics) -> str:
    return (
        "K = \\begin{bmatrix}"
        f"{intrinsics.fx:.3f} & 0.000 & {intrinsics.cx:.3f} \\\\ "
        f"0.000 & {intrinsics.fy:.3f} & {intrinsics.cy:.3f} \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}"
    )


def _pose_source_label(pose_source: AdvioPoseSource) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "Ground Truth",
        AdvioPoseSource.ARCORE: "ARCore",
        AdvioPoseSource.ARKIT: "ARKit",
        AdvioPoseSource.NONE: "No Pose Overlay",
    }[pose_source]


def _preview_frame_details(snapshot: AdvioPreviewSnapshot, packet: VideoFramePacket) -> dict[str, Any]:
    camera_pose = None
    if packet.camera_pose is not None:
        camera_pose = {
            "qx": packet.camera_pose.qx,
            "qy": packet.camera_pose.qy,
            "qz": packet.camera_pose.qz,
            "qw": packet.camera_pose.qw,
            "tx": packet.camera_pose.tx,
            "ty": packet.camera_pose.ty,
            "tz": packet.camera_pose.tz,
        }
    return {
        "sequence_id": snapshot.sequence_id,
        "sequence_label": snapshot.sequence_label,
        "pose_source": None if snapshot.pose_source is None else snapshot.pose_source.value,
        "frame_index": packet.frame_index,
        "timestamp_ns": packet.timestamp_ns,
        "source_frame_index": packet.metadata.get("source_frame_index"),
        "loop_index": packet.metadata.get("loop_index", 0),
        "video_rotation_degrees": packet.metadata.get("video_rotation_degrees", 0),
        "camera_pose": camera_pose,
        "metadata": packet.metadata,
    }
# fmt: on
