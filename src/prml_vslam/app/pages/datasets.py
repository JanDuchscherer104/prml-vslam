"""Streamlit datasets page router."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import streamlit as st

from prml_vslam.sources.datasets.advio import AdvioDownloadRequest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.record3d import Record3DDownloadRequest
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDownloadRequest

from ..advio_controller import AdvioDownloadFormData, build_advio_page_data, sync_advio_preview_state
from ..dataset_page.dashboard import render_dataset_dashboard
from ..dataset_page.downloads import (
    TumRgbdDownloadFormData,
    build_record3d_page_data,
    build_tum_rgbd_page_data,
    render_advio_diagnostics,
    render_record3d_diagnostics,
    render_tum_rgbd_diagnostics,
    rows_with_normalized_status,
)
from ..dataset_page.preview import (
    render_advio_loop_preview,
    render_record3d_loop_preview,
    render_tum_rgbd_loop_preview,
    sync_record3d_dataset_preview_state,
    sync_tum_rgbd_preview_state,
)
from ..dataset_page.query import load_normalized_dataset_snapshot_for_context
from ..dataset_page.scene import render_scene_tab
from ..models import Record3DDownloadFormData
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


_DATASET_SECTION_TABS = ("Dashboard", "Scene", "Preview", "Diagnostics")


def render(context: AppContext) -> None:
    """Render the public datasets page."""
    render_page_intro(
        eyebrow="Dataset Management",
        title="Datasets",
        body="Inspect committed scene catalogs, check local availability, download full scenes, and loop replay-ready scenes inside the workbench.",
    )
    advio_tab, tum_tab, record3d_tab = st.tabs(["ADVIO", "TUM RGB-D", "Record3D"])
    with advio_tab:
        _render_advio_tab(context)
    with tum_tab:
        _render_tum_rgbd_tab(context)
    with record3d_tab:
        _render_record3d_tab(context)


def _render_advio_tab(context: AppContext) -> None:
    sync_advio_preview_state(context)
    page_data = build_advio_page_data(
        context,
        AdvioDownloadFormData(request=AdvioDownloadRequest(), submitted=False),
    )
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
    normalized = load_normalized_dataset_snapshot_for_context(context, DatasetId.ADVIO)
    page_data.rows = rows_with_normalized_status(page_data.rows, normalized)
    _render_dataset_sections(
        dashboard=lambda: render_dataset_dashboard(
            normalized=normalized,
            summary=page_data.summary,
            key_prefix="advio-dashboard",
            advio_statuses=page_data.statuses,
        ),
        scene=lambda: render_scene_tab(
            context=context,
            normalized=normalized,
            page_state=context.state.advio,
            dataset_label="ADVIO",
            key_prefix="advio-scene",
        ),
        preview=lambda: render_advio_loop_preview(context, normalized),
        diagnostics=lambda: render_advio_diagnostics(context=context, normalized=normalized, rows=page_data.rows),
    )


def _render_tum_rgbd_tab(context: AppContext) -> None:
    sync_tum_rgbd_preview_state(context)
    page_data = build_tum_rgbd_page_data(context, TumRgbdDownloadFormData(request=TumRgbdDownloadRequest()))
    upstream = context.tum_rgbd_service.catalog.upstream
    _render_links(
        (
            ("Official Dataset", upstream["dataset_url"]),
            ("File Formats", upstream["file_formats_url"]),
        )
    )
    st.caption("Scene metadata is pinned to the TUM RGB-D sequences used by ViSTA-SLAM evaluation scripts.")
    normalized = load_normalized_dataset_snapshot_for_context(context, DatasetId.TUM_RGBD)
    page_data.rows = rows_with_normalized_status(page_data.rows, normalized)
    _render_dataset_sections(
        dashboard=lambda: render_dataset_dashboard(
            normalized=normalized,
            summary=page_data.summary,
            key_prefix="tum-rgbd-dashboard",
            advio_statuses=None,
        ),
        scene=lambda: render_scene_tab(
            context=context,
            normalized=normalized,
            page_state=context.state.tum_rgbd,
            dataset_label="TUM RGB-D",
            key_prefix="tum-rgbd-scene",
        ),
        preview=lambda: render_tum_rgbd_loop_preview(context, normalized),
        diagnostics=lambda: render_tum_rgbd_diagnostics(context=context, normalized=normalized, rows=page_data.rows),
    )


def _render_record3d_tab(context: AppContext) -> None:
    sync_record3d_dataset_preview_state(context)
    page_data = build_record3d_page_data(context, Record3DDownloadFormData(request=Record3DDownloadRequest()))
    _render_links((("Zenodo Record", "https://zenodo.org/records/20591352"),))
    st.caption("Scene metadata is pinned to the Record3D `.r3d` archives used by offline RGB-D evaluation.")
    normalized = load_normalized_dataset_snapshot_for_context(context, DatasetId.RECORD3D)
    page_data.rows = rows_with_normalized_status(page_data.rows, normalized)
    _render_dataset_sections(
        dashboard=lambda: render_dataset_dashboard(
            normalized=normalized,
            summary=page_data.summary,
            key_prefix="record3d-dashboard",
            advio_statuses=None,
        ),
        scene=lambda: render_scene_tab(
            context=context,
            normalized=normalized,
            page_state=context.state.record3d_dataset,
            dataset_label="Record3D",
            key_prefix="record3d-scene",
        ),
        preview=lambda: render_record3d_loop_preview(context, normalized),
        diagnostics=lambda: render_record3d_diagnostics(context=context, normalized=normalized, rows=page_data.rows),
    )


def _render_dataset_sections(
    *,
    dashboard: Callable[[], None],
    scene: Callable[[], None],
    preview: Callable[[], None],
    diagnostics: Callable[[], None],
) -> None:
    dashboard_tab, scene_tab, preview_tab, diagnostics_tab = st.tabs(list(_DATASET_SECTION_TABS))
    with diagnostics_tab:
        diagnostics()
    with dashboard_tab:
        dashboard()
    with scene_tab:
        scene()
    with preview_tab:
        preview()


def _render_links(links: tuple[tuple[str, str], ...]) -> None:
    for column, (label, url) in zip(st.columns(len(links), gap="small"), links, strict=True):
        column.link_button(label, url, width="stretch")
