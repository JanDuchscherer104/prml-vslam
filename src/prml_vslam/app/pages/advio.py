"""ADVIO Streamlit page for dataset discovery and selective downloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from prml_vslam.datasets import AdvioDatasetSummary, AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality

from ..plotting import (
    build_3d_trajectory_figure,
    build_bev_trajectory_figure,
    build_crowd_density_figure,
    build_height_profile_figure,
    build_local_readiness_figure,
    build_sample_interval_figure,
    build_scene_attribute_figure,
    build_scene_mix_figure,
    build_speed_profile_figure,
    trajectory_length_m,
)
from ..ui import render_page_intro

if TYPE_CHECKING:
    from prml_vslam.datasets.advio import AdvioOfflineSample

    from ..bootstrap import AppContext


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

    statuses = context.advio_service.local_scene_statuses()
    summary = context.advio_service.summarize()
    rows = context.advio_service.scene_rows()
    upstream_container = st.container()
    summary_container = st.container()
    overview_container = st.container()

    download_error = ""
    download_warning = ""
    download_result_message = ""
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{context.advio_service.dataset_root}`")
        sequence_ids, preset, selected_modalities, overwrite_existing, submitted = _render_download_form(context)
        if submitted:
            if not sequence_ids:
                download_warning = "Select at least one scene before starting a download."
            else:
                try:
                    with st.spinner("Downloading selected ADVIO scenes..."):
                        result = context.advio_service.download(
                            AdvioDownloadRequest(
                                sequence_ids=sequence_ids,
                                preset=preset,
                                modalities=selected_modalities,
                                overwrite=overwrite_existing,
                            )
                        )
                except Exception as exc:
                    download_error = str(exc)
                else:
                    summary = context.advio_service.summarize()
                    statuses = context.advio_service.local_scene_statuses()
                    rows = context.advio_service.scene_rows()
                    download_result_message = (
                        f"Prepared {len(result.sequence_ids)} scene(s), fetched {len(result.downloaded_archives)} "
                        f"archive(s), and wrote {len(result.written_paths)} path(s)."
                    )

    if download_error:
        st.error(download_error)
    elif download_warning:
        st.warning(download_warning)
    elif download_result_message:
        st.success(download_result_message)

    with upstream_container:
        _render_upstream_links(context)
    with summary_container:
        _render_summary_metrics(summary)
    with overview_container:
        _render_overview_plots(statuses)

    _render_sequence_explorer(context, statuses)

    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_upstream_links(context: AppContext) -> None:
    upstream = context.advio_service.catalog.upstream
    link_columns = st.columns(3, gap="small")
    link_columns[0].link_button("Official Repo", upstream.repo_url, width="stretch")
    link_columns[1].link_button("Zenodo Record", upstream.zenodo_record_url, width="stretch")
    link_columns[2].link_button("DOI", f"https://doi.org/{upstream.doi}", width="stretch")
    st.caption(
        "Scene and archive metadata in this page is pinned from the official ADVIO repository and Zenodo release."
    )


def _render_summary_metrics(summary: AdvioDatasetSummary) -> None:
    metric_columns = st.columns(5, gap="small")
    metric_columns[0].metric("Total Scenes", str(summary.total_scene_count))
    metric_columns[1].metric("Local Scenes", str(summary.local_scene_count))
    metric_columns[2].metric("Replay Ready", str(summary.replay_ready_scene_count))
    metric_columns[3].metric("Offline Ready", str(summary.offline_ready_scene_count))
    metric_columns[4].metric("Cached Archives", str(summary.cached_archive_count))


def _render_overview_plots(statuses: list[AdvioLocalSceneStatus]) -> None:
    with st.container(border=True):
        st.subheader("Dataset Overview")
        st.caption(
            "These plots combine the committed ADVIO catalog with current local availability so the page stays useful "
            "before and after any downloads."
        )
        first_row = st.columns(2, gap="large")
        with first_row[0]:
            st.plotly_chart(build_scene_mix_figure(statuses), width="stretch")
        with first_row[1]:
            st.plotly_chart(build_local_readiness_figure(statuses), width="stretch")

        second_row = st.columns(2, gap="large")
        with second_row[0]:
            st.plotly_chart(build_crowd_density_figure(statuses), width="stretch")
        with second_row[1]:
            st.plotly_chart(build_scene_attribute_figure(statuses), width="stretch")


def _render_download_form(
    context: AppContext,
) -> tuple[list[int], AdvioDownloadPreset, list[AdvioModality], bool, bool]:
    page_state = context.state.advio
    scenes = context.advio_service.list_scenes()
    selected_scene_ids = page_state.selected_sequence_ids
    selected_preset = page_state.download_preset
    selected_modalities = page_state.selected_modalities
    overwrite_existing = page_state.overwrite_existing

    with st.form("advio_download_form", border=False):
        selected_scene_ids = st.multiselect(
            "Scenes",
            options=[scene.sequence_id for scene in scenes],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
            placeholder="Choose one or more scenes to download",
        )
        selected_preset = st.selectbox(
            "Bundle",
            options=list(AdvioDownloadPreset),
            index=list(AdvioDownloadPreset).index(page_state.download_preset),
            format_func=lambda preset: preset.label,
        )
        selected_modalities = st.multiselect(
            "Modalities Override",
            options=list(AdvioModality),
            default=page_state.selected_modalities,
            format_func=lambda modality: modality.label,
            placeholder="Leave empty to use the selected bundle",
        )
        overwrite_existing = st.toggle(
            "Overwrite existing archives and extracted files",
            value=page_state.overwrite_existing,
        )
        effective_modalities = selected_modalities or list(selected_preset.modalities)
        st.caption("Resolved bundle: " + ", ".join(modality.label for modality in effective_modalities))
        submitted = st.form_submit_button(
            "Download selected scenes",
            type="primary",
            width="stretch",
        )

    context.state.advio.selected_sequence_ids = selected_scene_ids
    context.state.advio.download_preset = selected_preset
    context.state.advio.selected_modalities = selected_modalities
    context.state.advio.overwrite_existing = overwrite_existing
    context.store.save(context.state)
    return selected_scene_ids, selected_preset, selected_modalities, overwrite_existing, submitted


def _render_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    local_statuses = [status for status in statuses if _supports_sequence_explorer(context, status)]
    partial_statuses = [
        status for status in statuses if status.sequence_dir is not None and status not in local_statuses
    ]
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not local_statuses:
            if partial_statuses:
                st.warning(
                    "Local ADVIO scenes exist, but none are offline-ready yet. Finish downloading the offline bundle "
                    "for at least one scene to unlock trajectory and timing views."
                )
            else:
                st.info("Download at least one ADVIO scene to unlock trajectory and timing views.")
            return

        page_state = context.state.advio
        local_sequence_ids = [status.scene.sequence_id for status in local_statuses]
        selected_sequence_id = page_state.explorer_sequence_id
        if selected_sequence_id not in local_sequence_ids:
            selected_sequence_id = local_sequence_ids[0]

        selected_sequence_id = st.selectbox(
            "Local Scene",
            options=local_sequence_ids,
            index=local_sequence_ids.index(selected_sequence_id),
            format_func=lambda sequence_id: context.advio_service.scene(sequence_id).display_name,
        )
        if page_state.explorer_sequence_id != selected_sequence_id:
            page_state.explorer_sequence_id = selected_sequence_id
            context.store.save(context.state)

        try:
            sample = context.advio_service.load_local_sample(selected_sequence_id)
        except (FileNotFoundError, ValueError) as exc:
            st.warning(f"The selected scene is not fully ready for offline exploration yet. Details: {exc}")
            return
        _render_sequence_summary(sample)
        _render_sequence_plots(sample)


def _supports_sequence_explorer(context: AppContext, status: AdvioLocalSceneStatus) -> bool:
    if status.sequence_dir is None:
        return False
    try:
        context.advio_service.load_local_sample(status.scene.sequence_id)
    except (FileNotFoundError, ValueError):
        return False
    return True


def _render_sequence_summary(sample: AdvioOfflineSample) -> None:
    duration_s = sample.duration_s
    frame_count = int(len(sample.frame_timestamps_ns))
    mean_fps = 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)
    gt_length_m = trajectory_length_m(sample.ground_truth)

    metrics = st.columns(5, gap="small")
    metrics[0].metric("Duration", f"{duration_s:.1f} s")
    metrics[1].metric("Frames", str(frame_count))
    metrics[2].metric("Mean FPS", f"{mean_fps:.2f}")
    metrics[3].metric("GT Path Length", f"{gt_length_m:.1f} m")
    metrics[4].metric("ARKit", "Available" if sample.arkit is not None else "Missing")

    intrinsics = sample.calibration.intrinsics
    st.caption(
        "Camera: "
        f"{intrinsics.width_px}×{intrinsics.height_px}px, "
        f"fx={intrinsics.fx:.1f}, fy={intrinsics.fy:.1f}, "
        f"cx={intrinsics.cx:.1f}, cy={intrinsics.cy:.1f}"
    )


def _render_sequence_plots(sample: AdvioOfflineSample) -> None:
    trajectory_series = [("Ground Truth", sample.ground_truth), ("ARCore", sample.arcore)]
    if sample.arkit is not None:
        trajectory_series.append(("ARKit", sample.arkit))

    timing_series = [("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9)]
    timing_series.append(("Ground Truth", sample.ground_truth.timestamps_s))
    timing_series.append(("ARCore", sample.arcore.timestamps_s))
    if sample.arkit is not None:
        timing_series.append(("ARKit", sample.arkit.timestamps_s))

    trajectory_tab, motion_tab, timing_tab, camera_tab = st.tabs(["Trajectories", "Motion", "Timing", "Camera"])
    with trajectory_tab:
        columns = st.columns(2, gap="large")
        with columns[0]:
            st.plotly_chart(build_bev_trajectory_figure(trajectory_series), width="stretch")
        with columns[1]:
            st.plotly_chart(
                build_3d_trajectory_figure(trajectory_series, pose_axes_name="Ground Truth", pose_axis_stride=30),
                width="stretch",
            )

    with motion_tab:
        columns = st.columns(2, gap="large")
        with columns[0]:
            st.plotly_chart(build_speed_profile_figure(trajectory_series), width="stretch")
        with columns[1]:
            st.plotly_chart(build_height_profile_figure(trajectory_series), width="stretch")

    with timing_tab:
        columns = st.columns(2, gap="large")
        with columns[0]:
            st.plotly_chart(build_sample_interval_figure(timing_series), width="stretch")
        with columns[1]:
            st.plotly_chart(
                build_sample_interval_figure(timing_series[1:], title="Trajectory Cadence"),
                width="stretch",
            )

    with camera_tab:
        columns = st.columns((0.9, 1.1), gap="large")
        with columns[0]:
            st.markdown("**Camera Intrinsics**")
            st.latex(_format_intrinsic_matrix(sample))
        with columns[1]:
            st.markdown("**Modalities and Paths**")
            st.markdown(
                "\n".join(
                    [
                        f"- Video: `{sample.paths.video_path}`",
                        f"- Timestamps: `{sample.paths.frame_timestamps_path}`",
                        f"- Calibration: `{sample.paths.calibration_path}`",
                        f"- Ground Truth: `{sample.paths.ground_truth_csv_path}`",
                        f"- ARCore: `{sample.paths.arcore_csv_path}`",
                        f"- ARKit: `{sample.paths.arkit_csv_path if sample.paths.arkit_csv_path is not None else 'Missing'}`",
                    ]
                )
            )


def _format_intrinsic_matrix(sample: AdvioOfflineSample) -> str:
    intrinsics = sample.calibration.intrinsics
    return (
        "K = \\begin{bmatrix}"
        f"{intrinsics.fx:.3f} & 0.000 & {intrinsics.cx:.3f} \\\\ "
        f"0.000 & {intrinsics.fy:.3f} & {intrinsics.cy:.3f} \\\\ "
        "0.000 & 0.000 & 1.000"
        "\\end{bmatrix}"
    )
