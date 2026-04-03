"""ADVIO Streamlit page for dataset discovery and selective downloads."""

from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from prml_vslam.datasets import AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality

from .. import plotting as plots
from ..advio_controller import AdvioDownloadFormData, build_advio_page_data
from ..ui import render_page_intro

if TYPE_CHECKING:
    from prml_vslam.datasets.advio import AdvioOfflineSample

    from ..bootstrap import AppContext


# fmt: off
def render(context: AppContext) -> None:
    """Render the dedicated ADVIO dataset-management page."""
    render_page_intro(
        eyebrow="Dataset Management",
        title="ADVIO Dataset",
        body=(
            "Inspect the committed ADVIO scene catalog, check what is already available locally, and download "
            "only the scene subsets and modality bundles needed for replay or offline evaluation."
        ),
    )
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
            st.latex("K = \\begin{bmatrix}" f"{intrinsics.fx:.3f} & 0.000 & {intrinsics.cx:.3f} \\\\ " f"0.000 & {intrinsics.fy:.3f} & {intrinsics.cy:.3f} \\\\ " "0.000 & 0.000 & 1.000" "\\end{bmatrix}")
        with right:
            st.markdown("**Modalities and Paths**")
            st.markdown("\n".join(f"- {label}: `{value}`" for label, value in (("Video", sample.paths.video_path), ("Timestamps", sample.paths.frame_timestamps_path), ("Calibration", sample.paths.calibration_path), ("Ground Truth", sample.paths.ground_truth_csv_path), ("ARCore", sample.paths.arcore_csv_path), ("ARKit", sample.paths.arkit_csv_path or "Missing"))))
# fmt: on
