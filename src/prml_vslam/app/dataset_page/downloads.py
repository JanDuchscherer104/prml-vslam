"""Download, catalog, and diagnostics panels for dataset management."""

from __future__ import annotations

from collections.abc import Callable, Hashable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeVar, cast

import streamlit as st

from prml_vslam.plotting.datasets import build_payload_footprint_figure
from prml_vslam.sources.datasets.advio import AdvioDatasetService, AdvioDownloadRequest
from prml_vslam.sources.datasets.contracts import DatasetSummary, LocalSceneStatus
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery
from prml_vslam.sources.datasets.record3d import Record3DDownloadRequest, Record3DSceneMetadata
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdDownloadRequest

from ..advio_controller import AdvioDownloadFormData, build_advio_page_data, sync_advio_download_state
from ..models import AdvioPageState, DatasetPageData, DatasetTableRow, Record3DDownloadFormData, TumRgbdPageState
from ..state import save_model_updates
from .query import clear_normalized_dataset_snapshot_cache

if TYPE_CHECKING:
    from ..bootstrap import AppContext


@dataclass(slots=True)
class TumRgbdDownloadFormData:
    """Download form data for the TUM RGB-D dataset page."""

    request: TumRgbdDownloadRequest
    submitted: bool = False


DownloadRequestT = TypeVar("DownloadRequestT", AdvioDownloadRequest, TumRgbdDownloadRequest)
DownloadFormT = TypeVar("DownloadFormT", AdvioDownloadFormData, Record3DDownloadFormData, TumRgbdDownloadFormData)


def render_advio_diagnostics(
    *, context: AppContext, normalized: NormalizedDatasetQuery, rows: list[DatasetTableRow]
) -> None:
    """Render ADVIO download controls and normalized diagnostics."""
    form = render_download_card(
        dataset_root=context.advio_service.dataset_root,
        render_form=lambda: render_advio_download_form(context),
    )
    with st.spinner("Downloading selected ADVIO scenes...") if form.submitted else nullcontext():
        page_data = build_advio_page_data(context, form)
    render_notice(page_data.notice_level, page_data.notice_message)
    rerun_after_successful_download(form_submitted=form.submitted, notice_level=page_data.notice_level)
    if form.submitted:
        rows = rows_with_normalized_status(page_data.rows, normalized)
    render_normalized_characterization(normalized)
    render_catalog(rows)


def render_tum_rgbd_diagnostics(
    *, context: AppContext, normalized: NormalizedDatasetQuery, rows: list[DatasetTableRow]
) -> None:
    """Render TUM RGB-D download controls and normalized diagnostics."""
    form = render_download_card(
        dataset_root=context.tum_rgbd_service.dataset_root,
        render_form=lambda: render_tum_rgbd_download_form(context),
    )
    with st.spinner("Downloading selected TUM RGB-D scenes...") if form.submitted else nullcontext():
        page_data = build_tum_rgbd_page_data(context, form)
    render_notice(page_data.notice_level, page_data.notice_message)
    rerun_after_successful_download(form_submitted=form.submitted, notice_level=page_data.notice_level)
    if form.submitted:
        rows = rows_with_normalized_status(page_data.rows, normalized)
    render_normalized_characterization(normalized)
    render_catalog(rows)


def render_record3d_diagnostics(
    *, context: AppContext, normalized: NormalizedDatasetQuery, rows: list[DatasetTableRow]
) -> None:
    """Render Record3D download controls and normalized diagnostics."""
    form = render_download_card(
        dataset_root=context.record3d_dataset_service.dataset_root,
        render_form=lambda: render_record3d_download_form(context),
    )
    with st.spinner("Downloading selected Record3D scenes...") if form.submitted else nullcontext():
        page_data = build_record3d_page_data(context, form)
    render_notice(page_data.notice_level, page_data.notice_message)
    rerun_after_successful_download(form_submitted=form.submitted, notice_level=page_data.notice_level)
    if form.submitted:
        rows = rows_with_normalized_status(page_data.rows, normalized)
    render_normalized_characterization(normalized)
    render_catalog(rows)


def rerun_after_successful_download(*, form_submitted: bool, notice_level: str | None) -> None:
    """Rerun immediately after successful downloads so other tabs cannot render stale snapshots."""
    if form_submitted and notice_level == "success":
        clear_normalized_dataset_snapshot_cache()
        st.rerun()


def render_download_card(
    *,
    dataset_root: Path,
    render_form: Callable[[], DownloadFormT],
) -> DownloadFormT:
    """Render the shared download form shell."""
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{dataset_root}`")
        return render_form()


def render_notice(level: str | None, message: str) -> None:
    """Render a service notice from a page-data result."""
    if level:
        {"error": st.error, "warning": st.warning, "success": st.success}[level](message)


def build_tum_rgbd_page_data(context: AppContext, form: TumRgbdDownloadFormData) -> DatasetPageData:
    """Build TUM RGB-D catalog rows and optional download result notice."""
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
    return DatasetPageData(
        summary=cast(DatasetSummary, context.tum_rgbd_service.summarize(statuses)),
        statuses=statuses,
        rows=[
            {
                "Scene": status.scene.display_name,
                "Sequence": status.scene.sequence_id,
                "Category": status.scene.category,
                "Packed Size (MB)": round(status.scene.archive_size_bytes / 1e6, 1),
                "Downloaded Cache": status.sequence_dir is not None,
                "Cached Archive": status.archive_path is not None,
            }
            for status in statuses
        ],
        notice_level=notice_level,
        notice_message=notice_message,
    )


def build_record3d_page_data(context: AppContext, form: Record3DDownloadFormData) -> DatasetPageData:
    """Build Record3D catalog rows and optional download result notice."""
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message = ""
    if form.submitted:
        try:
            result = context.record3d_dataset_service.download(form.request)
        except Exception as exc:
            notice_level, notice_message = "error", str(exc)
        else:
            notice_level = "success"
            notice_message = (
                f"Prepared {len(result.sequence_ids)} scene(s), fetched {result.downloaded_archive_count} "
                f"archive(s), and wrote {result.written_path_count} path(s)."
            )
    statuses = context.record3d_dataset_service.local_scene_statuses()
    return DatasetPageData(
        summary=cast(DatasetSummary, context.record3d_dataset_service.summarize(statuses)),
        statuses=statuses,
        rows=record3d_scene_rows(statuses),
        notice_level=notice_level,
        notice_message=notice_message,
    )


def record3d_scene_rows(statuses: list[LocalSceneStatus[Record3DSceneMetadata]]) -> list[DatasetTableRow]:
    """Return catalog table rows for Record3D scene statuses."""
    rows: list[DatasetTableRow] = []
    for status in statuses:
        rows.append(
            {
                "Scene": status.scene.display_name,
                "Sequence": status.scene.sequence_id,
                "Source": "Zenodo" if status.scene.archive_url is not None else "Local-only",
                "Index": status.scene.sequence_index if status.scene.sequence_index is not None else "Local",
                "Packed Size (MB)": None
                if status.scene.archive_size_bytes <= 0
                else round(status.scene.archive_size_bytes / 1e6, 1),
                "Downloaded Cache": status.sequence_dir is not None,
                "Cached Archive": status.archive_path is not None,
            }
        )
    return rows


def rows_with_normalized_status(
    rows: list[DatasetTableRow],
    normalized: NormalizedDatasetQuery,
) -> list[DatasetTableRow]:
    """Add normalized-entry status columns to catalog rows."""
    return [
        {
            **row,
            "Normalized": str(row.get("Sequence", "")) in normalized.sequence_ids,
            "Normalized Profiles": normalized.profile_counts.get(str(row.get("Sequence", "")), 0),
        }
        for row in rows
    ]


def render_normalized_characterization(normalized: NormalizedDatasetQuery) -> None:
    """Render read-only normalized-store entry details."""
    with st.container(border=True):
        st.subheader("Normalized Dataset Entries")
        st.caption(
            "Read-only summary of canonical full-frame normalized-store entries. Build or refresh entries from the CLI; this page never normalizes datasets."
        )
        if normalized.issues:
            st.warning(
                f"{len(normalized.issues)} normalized entr{'y' if len(normalized.issues) == 1 else 'ies'} need rebuild or attention."
            )
            st.dataframe(normalized.issues, hide_index=True, width="stretch")
        if not normalized.records:
            st.info("No usable normalized entries found for this dataset.")
            return
        st.metric("Normalized Entries", str(len(normalized.records)))
        st.dataframe(normalized.entry_frame(), hide_index=True, width="stretch")
        render_normalized_analysis_tables(normalized, key_prefix=f"normalized:{normalized.dataset_id.value}")


def render_normalized_analysis_tables(normalized: NormalizedDatasetQuery, *, key_prefix: str) -> None:
    """Render read-only normalized stats and metadata tables."""
    if normalized.stats_df.empty and normalized.metadata_df.empty:
        st.info("No persisted normalized analysis tables found. Rebuild entries to populate stats and metadata CSVs.")
        return
    if normalized.stats_df.empty:
        with st.expander("Metadata", expanded=False):
            st.dataframe(normalized.metadata_df, hide_index=True, width="stretch")
        return
    sequence_ids = multiselect_all(
        "Sequences",
        normalized.stats_df["sequence_id"].unique().tolist(),
        key=f"{key_prefix}:sequence-filter",
    )
    scopes = multiselect_all(
        "Scopes",
        normalized.stats_df["scope"].unique().tolist(),
        key=f"{key_prefix}:scope-filter",
    )
    stats = multiselect_all(
        "Stats",
        normalized.stats_df["stat"].unique().tolist(),
        key=f"{key_prefix}:stat-filter",
    )
    filtered_stats = normalized.filtered_stats_frame(sequence_ids=sequence_ids, scopes=scopes, stats=stats)
    columns = st.columns(3, gap="small")
    columns[0].metric("Stats Rows", str(len(filtered_stats.index)))
    columns[1].metric("Metadata Rows", str(len(normalized.metadata_df.index)))
    columns[2].metric("Sequences", str(filtered_stats["sequence_id"].nunique() if not filtered_stats.empty else 0))

    observation_summary = normalized.observation_summary_frame()
    if not observation_summary.empty:
        st.subheader("Observation Summary")
        st.dataframe(observation_summary, hide_index=True, width="stretch")
    footprint = normalized.payload_footprint_frame()
    if not footprint.empty:
        st.subheader("Payload Footprint")
        st.plotly_chart(
            build_payload_footprint_figure(footprint),
            width="stretch",
            key=f"{key_prefix}:payload-footprint",
        )
        st.dataframe(footprint, hide_index=True, width="stretch")
    trajectory_summary = normalized.trajectory_summary_frame()
    if not trajectory_summary.empty:
        st.subheader("Trajectory Summary")
        st.dataframe(trajectory_summary, hide_index=True, width="stretch")
    if not filtered_stats.empty:
        with st.expander("Filtered Stats", expanded=False):
            st.dataframe(filtered_stats, hide_index=True, width="stretch")
    if not normalized.metadata_df.empty:
        with st.expander("Metadata", expanded=False):
            st.dataframe(normalized.metadata_df, hide_index=True, width="stretch")


def multiselect_all(label: str, values: list[Hashable], *, key: str) -> list[str]:
    """Render a multiselect that defaults to every available stringified value."""
    options = sorted({str(value) for value in values})
    return st.multiselect(label, options=options, default=options, key=key)


def render_catalog(rows: list[DatasetTableRow]) -> None:
    """Render the dataset service scene catalog table."""
    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(rows, hide_index=True, width="stretch")


def render_advio_download_form(context: AppContext) -> AdvioDownloadFormData:
    """Render ADVIO scene download controls."""
    request, submitted = render_download_form_fields(
        form_key="advio_download_form",
        page_state=context.state.advio,
        service=context.advio_service,
        request_type=AdvioDownloadRequest,
    )
    sync_advio_download_state(context, request)
    return AdvioDownloadFormData(request=request, submitted=submitted)


def render_tum_rgbd_download_form(context: AppContext) -> TumRgbdDownloadFormData:
    """Render TUM RGB-D scene download controls."""
    request, submitted = render_download_form_fields(
        form_key="tum_rgbd_download_form",
        page_state=context.state.tum_rgbd,
        service=context.tum_rgbd_service,
        request_type=TumRgbdDownloadRequest,
    )
    save_model_updates(
        context.store,
        context.state,
        context.state.tum_rgbd,
        selected_sequence_ids=request.sequence_ids,
        overwrite_existing=request.overwrite,
    )
    return TumRgbdDownloadFormData(request=request, submitted=submitted)


def render_record3d_download_form(context: AppContext) -> Record3DDownloadFormData:
    """Render Record3D archive download controls."""
    page_state = context.state.record3d_dataset
    service = context.record3d_dataset_service
    scenes = [scene for scene in service.catalog.scenes if scene.sequence_index is not None]
    with st.form("record3d_download_form", border=False):
        sequence_ids = st.multiselect(
            "Scenes",
            options=[int(scene.sequence_index) for scene in scenes if scene.sequence_index is not None],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_index: service.scene(str(sequence_index)).display_name,
            placeholder="Leave empty to download every catalog scene, or choose a subset",
            key="record3d_download_form:scenes",
        )
        overwrite = st.toggle(
            "Overwrite existing archives and extracted files",
            value=page_state.overwrite_existing,
            key="record3d_download_form:overwrite",
        )
        submitted = st.form_submit_button("Download scenes", type="primary", width="stretch")
    request = Record3DDownloadRequest(sequence_ids=sequence_ids, overwrite=overwrite)
    save_model_updates(
        context.store,
        context.state,
        context.state.record3d_dataset,
        selected_sequence_ids=request.sequence_ids,
        overwrite_existing=request.overwrite,
    )
    return Record3DDownloadFormData(request=request, submitted=submitted)


def render_download_form_fields(
    *,
    form_key: str,
    page_state: AdvioPageState | TumRgbdPageState,
    service: AdvioDatasetService | TumRgbdDatasetService,
    request_type: type[DownloadRequestT],
) -> tuple[DownloadRequestT, bool]:
    """Render common scene-download form fields."""
    with st.form(form_key, border=False):
        sequence_ids = st.multiselect(
            "Scenes",
            options=[scene.sequence_id for scene in service.catalog.scenes],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
            placeholder="Leave empty to download every scene, or choose a subset",
            key=f"{form_key}:scenes",
        )
        overwrite = st.toggle(
            "Overwrite existing archives and extracted files",
            value=page_state.overwrite_existing,
            key=f"{form_key}:overwrite",
        )
        submitted = st.form_submit_button("Download scenes", type="primary", width="stretch")
    return request_type(sequence_ids=sequence_ids, overwrite=overwrite), submitted
