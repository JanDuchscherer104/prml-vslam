"""ADVIO Streamlit page for dataset discovery and selective downloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.datasets import AdvioDatasetSummary, AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.datasets.advio import AdvioDownloadPreset, AdvioModality

from ..plotting import (
    build_crowd_density_figure,
    build_local_readiness_figure,
    build_scene_attribute_figure,
    build_scene_mix_figure,
)
from ..ui import render_page_intro

if TYPE_CHECKING:
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
