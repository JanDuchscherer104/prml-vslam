from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeVar, cast

import streamlit as st

from prml_vslam.interfaces import Observation
from prml_vslam.plotting.datasets import build_payload_footprint_figure
from prml_vslam.sources.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadRequest,
)
from prml_vslam.sources.datasets.contracts import DatasetId, DatasetSummary, LocalSceneStatus
from prml_vslam.sources.datasets.normalization import (
    open_normalized_dataset_stream,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_query import (
    NormalizedDatasetQuery,
    NormalizedSequenceRecord,
    normalized_advio_pose_sources,
    normalized_query_fingerprint,
    query_normalized_dataset,
)
from prml_vslam.sources.datasets.record3d import (
    Record3DDownloadRequest,
    Record3DSceneMetadata,
)
from prml_vslam.sources.datasets.tum_rgbd import (
    TumRgbdDatasetService,
    TumRgbdDownloadRequest,
)
from prml_vslam.utils import JsonObject, PathConfig

from ..advio_controller import (
    AdvioDownloadFormData,
    AdvioPreviewFormData,
    build_advio_page_data,
    handle_advio_preview_action,
    sync_advio_download_state,
    sync_advio_preview_state,
)
from ..live_session import (
    LiveMetric,
    live_poll_interval,
    render_live_action_slot,
    render_live_fragment,
    render_live_packet_tabs,
    render_live_session_shell,
    rerun_after_action,
)
from ..models import (
    AdvioPageState,
    AdvioPreviewSnapshot,
    DatasetPageData,
    DatasetTableRow,
    PreviewStreamState,
    Record3DDatasetPageState,
    Record3DDatasetPoseSource,
    Record3DDownloadFormData,
    TumRgbdPageState,
)
from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


@dataclass(slots=True)
class _TumRgbdDownloadFormData:
    request: TumRgbdDownloadRequest
    submitted: bool = False


DownloadRequestT = TypeVar("DownloadRequestT", AdvioDownloadRequest, TumRgbdDownloadRequest)


def render(context: AppContext) -> None:
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
    normalized = _load_normalized_dataset_snapshot_for_context(context, DatasetId.ADVIO)
    _render_normalized_summary_metrics(normalized)
    _render_normalized_characterization(normalized)
    page_data.rows = _rows_with_normalized_status(page_data.rows, normalized)
    _render_download_cache_summary(page_data.summary)
    _render_sequence_explorer_impl(
        context=context,
        records=normalized.default_records,
        page_state=context.state.advio,
        dataset_label="ADVIO",
    )
    _render_advio_loop_preview(context, normalized)
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
    normalized = _load_normalized_dataset_snapshot_for_context(context, DatasetId.TUM_RGBD)
    _render_normalized_summary_metrics(normalized)
    _render_normalized_characterization(normalized)
    page_data.rows = _rows_with_normalized_status(page_data.rows, normalized)
    _render_download_cache_summary(page_data.summary)
    _render_sequence_explorer_impl(
        context=context,
        records=normalized.default_records,
        page_state=context.state.tum_rgbd,
        dataset_label="TUM RGB-D",
    )
    _render_tum_rgbd_loop_preview(context, normalized)
    _render_catalog(page_data.rows)


def _render_record3d_tab(context: AppContext) -> None:
    _sync_record3d_dataset_preview_state(context)
    form = _render_download_card(
        dataset_root=context.record3d_dataset_service.dataset_root,
        download_label="Record3D",
        render_form=lambda: _render_record3d_download_form(context),
    )
    with st.spinner("Downloading selected Record3D scenes...") if form.submitted else nullcontext():
        page_data = _build_record3d_page_data(context, form)
    _render_notice(page_data.notice_level, page_data.notice_message)
    _render_links((("Zenodo Record", "https://zenodo.org/records/20591352"),))
    st.caption("Scene metadata is pinned to the Record3D `.r3d` archives used by offline RGB-D evaluation.")
    normalized = _load_normalized_dataset_snapshot_for_context(context, DatasetId.RECORD3D)
    _render_normalized_summary_metrics(normalized)
    _render_normalized_characterization(normalized)
    page_data.rows = _rows_with_normalized_status(page_data.rows, normalized)
    _render_download_cache_summary(page_data.summary)
    _render_sequence_explorer_impl(
        context=context,
        records=normalized.default_records,
        page_state=context.state.record3d_dataset,
        dataset_label="Record3D",
    )
    _render_record3d_loop_preview(context, normalized)
    _render_catalog(page_data.rows)


def _render_download_card(
    *,
    dataset_root: Path,
    download_label: str,
    render_form: Callable[[], AdvioDownloadFormData | Record3DDownloadFormData | _TumRgbdDownloadFormData],
) -> AdvioDownloadFormData | Record3DDownloadFormData | _TumRgbdDownloadFormData:
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{dataset_root}`")
        return render_form()


def _render_notice(level: str | None, message: str) -> None:
    if level:
        {"error": st.error, "warning": st.warning, "success": st.success}[level](message)


def _build_tum_rgbd_page_data(context: AppContext, form: _TumRgbdDownloadFormData) -> DatasetPageData:
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


def _build_record3d_page_data(context: AppContext, form: Record3DDownloadFormData) -> DatasetPageData:
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
        rows=_record3d_scene_rows(statuses),
        notice_level=notice_level,
        notice_message=notice_message,
    )


def _record3d_scene_rows(statuses: list[LocalSceneStatus[Record3DSceneMetadata]]) -> list[DatasetTableRow]:
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


def _rows_with_normalized_status(
    rows: list[DatasetTableRow],
    normalized: NormalizedDatasetQuery,
) -> list[DatasetTableRow]:
    return [
        {
            **row,
            "Normalized": str(row.get("Sequence", "")) in normalized.sequence_ids,
            "Normalized Profiles": normalized.profile_counts.get(str(row.get("Sequence", "")), 0),
        }
        for row in rows
    ]


def _load_normalized_dataset_snapshot_for_context(context: AppContext, dataset_id: DatasetId) -> NormalizedDatasetQuery:
    return _load_normalized_dataset_snapshot(
        context.path_config.root.as_posix(),
        context.path_config.data_dir.as_posix(),
        dataset_id.value,
        normalized_query_fingerprint(context.path_config, dataset_id),
    )


def _render_normalized_characterization(normalized: NormalizedDatasetQuery) -> None:
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
        _render_normalized_analysis_tables(normalized)


def _render_normalized_analysis_tables(normalized: NormalizedDatasetQuery) -> None:
    if normalized.stats_df.empty and normalized.metadata_df.empty:
        st.info("No persisted normalized analysis tables found. Rebuild entries to populate stats and metadata CSVs.")
        return
    sequence_ids = _multiselect_all("Sequences", normalized.stats_df["sequence_id"].unique().tolist())
    scopes = _multiselect_all("Scopes", normalized.stats_df["scope"].unique().tolist())
    stats = _multiselect_all("Stats", normalized.stats_df["stat"].unique().tolist())
    filtered_stats = normalized.filtered_stats_frame(sequence_ids=sequence_ids, scopes=scopes, stats=stats)
    columns = st.columns(4, gap="small")
    columns[0].metric("Stats Rows", str(len(filtered_stats.index)))
    columns[1].metric("Metadata Rows", str(len(normalized.metadata_df.index)))
    columns[2].metric("Sequences", str(filtered_stats["sequence_id"].nunique() if not filtered_stats.empty else 0))
    motion_classes = (
        filtered_stats.loc[filtered_stats["stat"].eq("ego_motion_class"), "value"].nunique()
        if not filtered_stats.empty
        else 0
    )
    columns[3].metric("Motion Classes", str(motion_classes))

    observation_summary = normalized.observation_summary_frame()
    if not observation_summary.empty:
        st.subheader("Observation Summary")
        st.dataframe(observation_summary, hide_index=True, width="stretch")
    footprint = normalized.payload_footprint_frame()
    if not footprint.empty:
        st.subheader("Payload Footprint")
        st.plotly_chart(build_payload_footprint_figure(footprint), width="stretch")
        st.dataframe(footprint, hide_index=True, width="stretch")
    trajectory_summary = normalized.trajectory_summary_frame()
    if not trajectory_summary.empty:
        st.subheader("Trajectory Summary")
        st.dataframe(trajectory_summary, hide_index=True, width="stretch")
    if not filtered_stats.empty:
        st.subheader("Filtered Stats")
        st.dataframe(filtered_stats, hide_index=True, width="stretch")
    if not normalized.metadata_df.empty:
        st.subheader("Metadata")
        st.dataframe(normalized.metadata_df, hide_index=True, width="stretch")


def _multiselect_all(label: str, values: list[object]) -> list[str]:
    options = sorted({str(value) for value in values})
    return st.multiselect(label, options=options, default=options)


@st.cache_data
def _load_normalized_dataset_snapshot(
    root: str, data_dir: str, dataset_id: str, freshness_token: tuple[tuple[str, int, int], ...]
) -> NormalizedDatasetQuery:
    del freshness_token
    path_config = PathConfig(root=Path(root), data_dir=Path(data_dir))
    dataset = DatasetId(dataset_id)
    return query_normalized_dataset(dataset, path_config)


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


def _sync_record3d_dataset_preview_state(
    context: AppContext, snapshot: AdvioPreviewSnapshot | None = None
) -> AdvioPreviewSnapshot:
    snapshot = context.advio_runtime.snapshot() if snapshot is None else snapshot
    if context.state.record3d_dataset.preview_is_running and snapshot.state not in {
        PreviewStreamState.CONNECTING,
        PreviewStreamState.STREAMING,
    }:
        save_model_updates(context.store, context.state, context.state.record3d_dataset, preview_is_running=False)
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
        stream = open_normalized_dataset_stream(
            dataset_id=DatasetId.TUM_RGBD,
            service=context.tum_rgbd_service,
            source_config=source_config_for_normalization(dataset_id=DatasetId.TUM_RGBD, sequence_id=sequence_id),
            include_depth=include_depth,
            path_config=context.path_config,
            output_dir=context.path_config.resolve_output_dir(
                Path("dataset-preview") / "tum_rgbd" / str(sequence_id), create=True
            ),
        )
        context.advio_runtime.start(
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


def _handle_record3d_dataset_preview_action(
    *,
    context: AppContext,
    sequence_id: str,
    pose_source: StrEnum,
    include_depth: bool,
    start_requested: bool,
    stop_requested: bool,
) -> str | None:
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
        context.advio_runtime.stop()
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
            output_dir=context.path_config.resolve_output_dir(
                Path("dataset-preview") / "record3d" / str(sequence_id), create=True
            ),
        )
        context.advio_runtime.start(
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


def _render_links(links: tuple[tuple[str, str], ...]) -> None:
    for column, (label, url) in zip(st.columns(len(links), gap="small"), links, strict=True):
        column.link_button(label, url, width="stretch")


def _render_normalized_summary_metrics(normalized: NormalizedDatasetQuery) -> None:
    metrics = (
        ("Normalized Entries", len(normalized.records)),
        ("Sequences", len(normalized.sequence_ids)),
        ("Default Profiles", len(normalized.default_profile_sequence_ids)),
        ("Stats Rows", len(normalized.stats_df.index)),
        ("Metadata Rows", len(normalized.metadata_df.index)),
        ("Issues", len(normalized.issues)),
    )
    for column, (label, value) in zip(st.columns(6, gap="small"), metrics, strict=True):
        column.metric(label, str(value))


def _render_download_cache_summary(summary: DatasetSummary) -> None:
    metrics = (
        ("Catalog Scenes", summary.total_scene_count),
        ("Downloaded Cache", summary.local_scene_count),
        ("Cached Archives", summary.cached_archive_count),
    )
    for column, (label, value) in zip(st.columns(3, gap="small"), metrics, strict=True):
        column.metric(label, str(value))


def _render_catalog(rows: list[DatasetTableRow]) -> None:
    with st.container(border=True):
        st.subheader("Scene Catalog")
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_advio_download_form(context: AppContext) -> AdvioDownloadFormData:
    request, submitted = _render_download_form_fields(
        form_key="advio_download_form",
        page_state=context.state.advio,
        service=context.advio_service,
        request_type=AdvioDownloadRequest,
    )
    sync_advio_download_state(context, request)
    return AdvioDownloadFormData(request=request, submitted=submitted)


def _render_tum_rgbd_download_form(context: AppContext) -> _TumRgbdDownloadFormData:
    request, submitted = _render_download_form_fields(
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
    return _TumRgbdDownloadFormData(request=request, submitted=submitted)


def _render_record3d_download_form(context: AppContext) -> Record3DDownloadFormData:
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
        )
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
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


def _render_download_form_fields(
    *,
    form_key: str,
    page_state: AdvioPageState | TumRgbdPageState,
    service: AdvioDatasetService | TumRgbdDatasetService,
    request_type: type[DownloadRequestT],
) -> tuple[DownloadRequestT, bool]:
    with st.form(form_key, border=False):
        sequence_ids = st.multiselect(
            "Scenes",
            options=[scene.sequence_id for scene in service.catalog.scenes],
            default=page_state.selected_sequence_ids,
            format_func=lambda sequence_id: service.scene(sequence_id).display_name,
            placeholder="Leave empty to download every scene, or choose a subset",
        )
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        submitted = st.form_submit_button("Download scenes", type="primary", width="stretch")
    return request_type(sequence_ids=sequence_ids, overwrite=overwrite), submitted


def _render_sequence_explorer_impl(
    *,
    context: AppContext,
    records: list[NormalizedSequenceRecord],
    page_state: AdvioPageState | TumRgbdPageState | Record3DDatasetPageState,
    dataset_label: str,
) -> None:
    sequence_ids = [record.sequence_id for record in records]
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not sequence_ids:
            st.info(f"Build at least one normalized {dataset_label} entry to unlock sequence statistics.")
            return
        selected_id = (
            page_state.explorer_sequence_id if page_state.explorer_sequence_id in sequence_ids else sequence_ids[0]
        )
        selected_id = st.selectbox(
            "Normalized Scene",
            options=sequence_ids,
            index=sequence_ids.index(selected_id),
            format_func=lambda sequence_id: next(
                record.sequence_label for record in records if record.sequence_id == sequence_id
            ),
        )
        save_model_updates(context.store, context.state, page_state, explorer_sequence_id=selected_id)
        selected_records = [record for record in records if record.sequence_id == selected_id]
        st.dataframe(
            [
                {
                    "Profile": record.profile_key,
                    "Default Profile": record.is_default_profile,
                    "Stats Rows": record.stats_row_count,
                    "Metadata Rows": record.metadata_row_count,
                    "Root": record.root.as_posix(),
                }
                for record in selected_records
            ],
            hide_index=True,
            width="stretch",
        )


def _render_advio_loop_preview(context: AppContext, normalized: NormalizedDatasetQuery) -> None:
    _render_loop_preview_impl(
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
        action=lambda selected_id, pose_source, option_value, start, stop: handle_advio_preview_action(
            context,
            AdvioPreviewFormData(
                sequence_id=int(str(selected_id).split("-", maxsplit=1)[1]),
                pose_source=pose_source,
                normalize_video_orientation=option_value,
                start_requested=start,
                stop_requested=stop,
            ),
        ),
        sync_snapshot=lambda: sync_advio_preview_state(context),
    )


def _render_tum_rgbd_loop_preview(context: AppContext, normalized: NormalizedDatasetQuery) -> None:
    _render_loop_preview_impl(
        records=normalized.default_records,
        page_state=context.state.tum_rgbd,
        pose_source_options=None,
        caption="Run a normalized TUM RGB-D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
        option_label="Include depth frames",
        option_key="preview_include_depth",
        initial_option_value=context.state.tum_rgbd.preview_include_depth,
        action_key_prefix="tum-rgbd-loop-preview",
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


def _render_record3d_loop_preview(
    context: AppContext,
    normalized: NormalizedDatasetQuery,
) -> None:
    _render_loop_preview_impl(
        records=normalized.default_records,
        page_state=context.state.record3d_dataset,
        pose_source_options=lambda _selected_id: [Record3DDatasetPoseSource.ARKIT],
        caption="Run a normalized Record3D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
        option_label="Include depth frames",
        option_key="preview_include_depth",
        initial_option_value=context.state.record3d_dataset.preview_include_depth,
        action_key_prefix="record3d-dataset-loop-preview",
        action=lambda selected_id, pose_source, option_value, start, stop: _handle_record3d_dataset_preview_action(
            context=context,
            sequence_id=str(selected_id),
            pose_source=pose_source,
            include_depth=option_value,
            start_requested=start,
            stop_requested=stop,
        ),
        sync_snapshot=lambda: _sync_record3d_dataset_preview_state(context),
    )


def _render_loop_preview_impl(
    *,
    records: list[NormalizedSequenceRecord],
    page_state: AdvioPageState | TumRgbdPageState | Record3DDatasetPageState,
    pose_source_options: Callable[[int | str], list[StrEnum]] | None,
    caption: str,
    option_label: str,
    option_key: str,
    initial_option_value: bool,
    action_key_prefix: str,
    action: Callable[[int | str, StrEnum, bool, bool, bool], str | None],
    sync_snapshot: Callable[[], AdvioPreviewSnapshot],
) -> None:
    previewable_ids = [record.sequence_id for record in records]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption(caption)
        if not previewable_ids:
            st.info("Build at least one normalized entry to unlock loop preview.")
            return
        selected_id = (
            page_state.preview_sequence_id if page_state.preview_sequence_id in previewable_ids else previewable_ids[0]
        )
        pose_source = page_state.preview_pose_source
        selected_id = st.selectbox(
            "Preview Scene",
            options=previewable_ids,
            index=previewable_ids.index(selected_id),
            format_func=lambda sequence_id: next(
                record.sequence_label for record in records if record.sequence_id == sequence_id
            ),
            key=f"{action_key_prefix}:scene",
        )
        available_pose_sources = (
            [page_state.preview_pose_source] if pose_source_options is None else pose_source_options(selected_id)
        )
        pose_source = (
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
            packet=snapshot.preview_packet,
            preview_renderer=_render_preview_frame,
            positions_xyz=snapshot.preview_trajectory_xyz,
            timestamps_s=snapshot.preview_trajectory_time_s if len(snapshot.preview_trajectory_time_s) else None,
            trajectory_empty_message="No camera trajectory is available for the selected pose source yet.",
            details_payload={}
            if snapshot.preview_packet is None
            else _preview_frame_details(snapshot, snapshot.preview_packet),
            intrinsics_missing_message="Camera intrinsics are not available for the current packet.",
        ),
    )


def _preview_metrics(snapshot: AdvioPreviewSnapshot) -> tuple[LiveMetric, ...]:
    packet = snapshot.preview_packet
    loop_index = 0 if packet is None else packet.loop_index
    return (
        ("Status", snapshot.state.value.upper()),
        ("Received Frames", str(snapshot.preview_frame_count)),
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


def _render_preview_frame(packet: Observation) -> None:
    st.markdown("**RGB Frame**")
    st.image(packet.rgb, channels="RGB", clamp=True)
    if packet.depth_m is not None:
        st.markdown("**Depth Frame**")
        st.image(packet.depth_m, clamp=True)


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


def _preview_frame_details(snapshot: AdvioPreviewSnapshot, packet: Observation) -> JsonObject:
    pose = (
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
        "provenance": packet.provenance.compact_payload(),
    }
