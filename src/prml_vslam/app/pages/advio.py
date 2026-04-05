"""ADVIO Streamlit page for dataset discovery, downloads, and loop preview."""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

import prml_vslam.plotting as plots
from prml_vslam.datasets import AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality, AdvioOfflineSample, AdvioPoseSource
from prml_vslam.interfaces import FramePacket

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
    render_camera_intrinsics,
    render_live_fragment,
    render_live_session_shell,
    render_live_trajectory,
)
from ..services import AdvioPreviewSnapshot, AdvioPreviewStreamState
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


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
        {"error": st.error, "warning": st.warning, "success": st.success}[page_data.notice_level](
            page_data.notice_message
        )
    upstream = context.advio_service.catalog.upstream
    links = (
        ("Official Repo", upstream.repo_url),
        ("Zenodo Record", upstream.zenodo_record_url),
        ("DOI", f"https://doi.org/{upstream.doi}"),
    )
    for column, (label, url) in zip(st.columns(3, gap="small"), links, strict=True):
        column.link_button(label, url, width="stretch")
    st.caption(
        "Scene and archive metadata in this page is pinned from the official ADVIO repository and Zenodo release."
    )
    metrics = (
        ("Total Scenes", page_data.summary.total_scene_count),
        ("Local Scenes", page_data.summary.local_scene_count),
        ("Replay Ready", page_data.summary.replay_ready_scene_count),
        ("Offline Ready", page_data.summary.offline_ready_scene_count),
        ("Cached Archives", page_data.summary.cached_archive_count),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, str(value))
    with st.container(border=True):
        st.subheader("Dataset Overview")
        st.caption(
            "These plots combine the committed ADVIO catalog with current local availability so the page stays useful before and after any downloads."
        )
        figure_rows = (
            (plots.build_scene_mix_figure(page_data.statuses), plots.build_local_readiness_figure(page_data.statuses)),
            (
                plots.build_crowd_density_figure(page_data.statuses),
                plots.build_scene_attribute_figure(page_data.statuses),
            ),
        )
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
        sequence_ids = st.multiselect(
            "Scenes",
            options=[scene.sequence_id for scene in service.list_scenes()],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
            placeholder="Choose one or more scenes to download",
        )
        preset = st.selectbox(
            "Bundle",
            options=list(AdvioDownloadPreset),
            index=list(AdvioDownloadPreset).index(page_state.download_preset),
            format_func=lambda item: item.label,
        )
        modalities = st.multiselect(
            "Modalities Override",
            options=list(AdvioModality),
            default=page_state.selected_modalities,
            format_func=lambda item: item.label,
            placeholder="Leave empty to use the selected bundle",
        )
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        st.caption("Resolved bundle: " + ", ".join(item.label for item in (modalities or list(preset.modalities))))
        submitted = st.form_submit_button("Download selected scenes", type="primary", width="stretch")
    request = AdvioDownloadRequest(sequence_ids=sequence_ids, preset=preset, modalities=modalities, overwrite=overwrite)
    sync_advio_download_state(context, request)
    return AdvioDownloadFormData(request=request, submitted=submitted)


def _render_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    offline_ids = [status.scene.sequence_id for status in statuses if status.offline_ready]
    has_partial_scene = any(status.sequence_dir is not None and not status.offline_ready for status in statuses)
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not offline_ids:
            (st.warning if has_partial_scene else st.info)(
                "Local ADVIO scenes exist, but none are offline-ready yet. Finish downloading the offline bundle for at least one scene to unlock trajectory and timing views."
                if has_partial_scene
                else "Download at least one ADVIO scene to unlock trajectory and timing views."
            )
            return
        service = context.advio_service
        selected_id = st.selectbox(
            "Local Scene",
            options=offline_ids,
            index=offline_ids.index(
                context.state.advio.explorer_sequence_id
                if context.state.advio.explorer_sequence_id in offline_ids
                else offline_ids[0]
            ),
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
        )
        sample, error_message = load_advio_explorer_sample(context, sequence_id=selected_id)
        if error_message:
            st.warning(error_message)
        elif sample is not None:
            _render_sequence_details(sample)


def _render_sequence_details(sample: AdvioOfflineSample) -> None:
    duration_s, frame_count, intrinsics = (
        sample.duration_s,
        int(len(sample.frame_timestamps_ns)),
        sample.calibration.intrinsics,
    )
    mean_fps = 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)
    metrics = (
        ("Duration", f"{duration_s:.1f} s"),
        ("Frames", str(frame_count)),
        ("Mean FPS", f"{mean_fps:.2f}"),
        ("GT Path Length", f"{plots.trajectory_length_m(sample.ground_truth):.1f} m"),
        ("ARKit", "Available" if sample.arkit is not None else "Missing"),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, value)
    st.caption(
        f"Camera: {intrinsics.width_px}×{intrinsics.height_px}px, fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}, cx={intrinsics.cx:.1f}, cy={intrinsics.cy:.1f}"
    )
    trajectories = [("Ground Truth", sample.ground_truth), ("ARCore", sample.arcore)]
    timing = [
        ("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9),
        ("Ground Truth", sample.ground_truth.timestamps_s),
        ("ARCore", sample.arcore.timestamps_s),
    ]
    if sample.arkit is not None:
        trajectories.append(("ARKit", sample.arkit))
        timing.append(("ARKit", sample.arkit.timestamps_s))
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
            st.markdown(
                "\n".join(
                    f"- {label}: `{value}`"
                    for label, value in (
                        ("Video", sample.paths.video_path),
                        ("Timestamps", sample.paths.frame_timestamps_path),
                        ("Calibration", sample.paths.calibration_path),
                        ("Ground Truth", sample.paths.ground_truth_csv_path),
                        ("ARCore", sample.paths.arcore_csv_path),
                        ("ARKit", sample.paths.arkit_csv_path or "Missing"),
                    )
                )
            )


def _render_loop_preview(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption(
            "Run a replay-ready ADVIO scene in a local loop with the existing CV2 producer and inspect frames, trajectory, and camera metadata live."
        )
        if not previewable_ids:
            st.info("Download the streaming bundle for at least one scene to unlock loop preview.")
            return
        page_state, service = context.state.advio, context.advio_service
        selected_id = (
            page_state.preview_sequence_id if page_state.preview_sequence_id in previewable_ids else previewable_ids[0]
        )
        pose_source = page_state.preview_pose_source
        with st.form("advio_preview_form", border=False):
            selected_id = st.selectbox(
                "Preview Scene",
                options=previewable_ids,
                index=previewable_ids.index(selected_id),
                format_func=lambda sequence_id: service.scene(sequence_id).display_name,
            )
            pose_source = st.selectbox(
                "Pose Source",
                options=list(AdvioPoseSource),
                index=list(AdvioPoseSource).index(pose_source),
                format_func=_pose_source_label,
            )
            respect_video_rotation = st.toggle(
                "Respect video rotation metadata", value=page_state.preview_respect_video_rotation
            )
            start_requested = st.form_submit_button(
                "Start preview" if not page_state.preview_is_running else "Restart preview",
                type="primary",
                use_container_width=True,
            )
        stop_requested = st.button("Stop preview", disabled=not page_state.preview_is_running, use_container_width=True)
        error_message = handle_advio_preview_action(
            context,
            AdvioPreviewFormData(
                sequence_id=selected_id,
                pose_source=pose_source,
                respect_video_rotation=respect_video_rotation,
                start_requested=start_requested,
                stop_requested=stop_requested,
            ),
        )
        if error_message:
            st.error(error_message)
        render_live_fragment(
            run_every=0.2 if context.state.advio.preview_is_running else None,
            render_body=lambda: _render_preview_snapshot(sync_advio_preview_state(context)),
        )


def _render_preview_snapshot(snapshot: AdvioPreviewSnapshot) -> None:
    packet = snapshot.latest_packet
    render_live_session_shell(
        title=None,
        status_renderer=lambda: _render_preview_status_notice(snapshot),
        metrics=_preview_metrics(snapshot, packet),
        caption=_preview_caption(snapshot),
        body_renderer=None if packet is None else lambda: _render_preview_tabs(snapshot),
    )


def _preview_metrics(
    snapshot: AdvioPreviewSnapshot,
    packet: FramePacket | None,
) -> tuple[LiveMetric, ...]:
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
        "No pose overlay" if snapshot.pose_source is AdvioPoseSource.NONE else _pose_source_label(snapshot.pose_source)
    )
    return f"Sequence: {snapshot.sequence_label} · Pose Source: {pose_label}"


def _render_preview_tabs(snapshot: AdvioPreviewSnapshot) -> None:
    packet = snapshot.latest_packet
    if packet is None:
        return
    preview_tab, trajectory_tab, camera_tab = st.tabs(["Frames", "Trajectory", "Camera"])
    with preview_tab:
        st.markdown("**RGB Frame**")
        st.image(packet.rgb, channels="RGB", clamp=True)
    with trajectory_tab:
        render_live_trajectory(
            positions_xyz=snapshot.trajectory_positions_xyz,
            timestamps_s=snapshot.trajectory_timestamps_s if len(snapshot.trajectory_timestamps_s) else None,
            empty_message="No camera trajectory is available for the selected pose source yet.",
        )
    with camera_tab:
        left, right = st.columns((0.9, 1.1), gap="large")
        with left:
            st.markdown("**Camera Intrinsics**")
            render_camera_intrinsics(
                intrinsics=packet.intrinsics,
                missing_message="Camera intrinsics are not available for the current packet.",
            )
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


def _pose_source_label(pose_source: AdvioPoseSource | None) -> str:
    return {
        AdvioPoseSource.GROUND_TRUTH: "Ground Truth",
        AdvioPoseSource.ARCORE: "ARCore",
        AdvioPoseSource.ARKIT: "ARKit",
        AdvioPoseSource.NONE: "No Pose Overlay",
        None: "No Pose Overlay",
    }[pose_source]


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
        "pose": pose,
        "metadata": packet.metadata,
    }
