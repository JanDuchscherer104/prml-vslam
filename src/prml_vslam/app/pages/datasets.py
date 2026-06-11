from __future__ import annotations

from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias, TypeVar, cast

import numpy as np
import streamlit as st
from evo.core.trajectory import PoseTrajectory3D  # type: ignore[import-untyped]

import prml_vslam.plotting as plots
from prml_vslam.interfaces import CameraIntrinsics, Observation
from prml_vslam.sources.dataset_query import NormalizedDatasetQuery
from prml_vslam.sources.datasets.advio import (
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioModality,
    AdvioOfflineSample,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.sources.datasets.contracts import DatasetId, DatasetSummary
from prml_vslam.sources.datasets.normalization import (
    dataset_service,
    normalized_profile_for_dataset,
    open_normalized_dataset_stream,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetEntry
from prml_vslam.sources.datasets.record3d import (
    Record3DDatasetService,
    Record3DDownloadRequest,
    Record3DLocalSceneStatus,
    Record3DOfflineSample,
)
from prml_vslam.sources.datasets.tum_rgbd import (
    TumRgbdDatasetService,
    TumRgbdDownloadPreset,
    TumRgbdDownloadRequest,
    TumRgbdLocalSceneStatus,
    TumRgbdModality,
    TumRgbdOfflineSample,
    TumRgbdPoseSource,
)
from prml_vslam.utils import BaseConfig, JsonObject, PathConfig

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
from ..models import (
    AdvioPageState,
    AdvioPreviewSnapshot,
    DatasetPageData,
    DatasetTableRow,
    NormalizedDatasetSnapshot,
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


SequenceId: TypeAlias = int | str
StatusList: TypeAlias = list[AdvioLocalSceneStatus] | list[TumRgbdLocalSceneStatus] | list[Record3DLocalSceneStatus]
ExplorerSample: TypeAlias = AdvioOfflineSample | TumRgbdOfflineSample | Record3DOfflineSample
DatasetPageState: TypeAlias = AdvioPageState | TumRgbdPageState | Record3DDatasetPageState
DatasetService: TypeAlias = AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService
DownloadRequest: TypeAlias = AdvioDownloadRequest | TumRgbdDownloadRequest


@dataclass(slots=True)
class _DownloadFormData:
    request: BaseConfig
    submitted: bool = False


DownloadFormData = AdvioDownloadFormData | Record3DDownloadFormData | _DownloadFormData
DownloadFormT = TypeVar("DownloadFormT", AdvioDownloadFormData, Record3DDownloadFormData, _DownloadFormData)
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
    _render_summary_metrics(page_data.summary)
    _render_normalized_characterization(normalized)
    page_data.rows = _rows_with_normalized_status(DatasetId.ADVIO, page_data.rows, normalized)
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
    normalized = _load_normalized_dataset_snapshot_for_context(context, DatasetId.TUM_RGBD)
    _render_summary_metrics(page_data.summary)
    _render_normalized_characterization(normalized)
    page_data.rows = _rows_with_normalized_status(DatasetId.TUM_RGBD, page_data.rows, normalized)
    tum_statuses = cast(list[TumRgbdLocalSceneStatus], page_data.statuses)
    _render_tum_rgbd_sequence_explorer(context, tum_statuses)
    _render_tum_rgbd_loop_preview(context, tum_statuses)
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
    _render_summary_metrics(page_data.summary)
    _render_normalized_characterization(normalized)
    page_data.rows = _record3d_rows_with_normalized_status(page_data.rows, normalized)
    record3d_statuses = cast(list[Record3DLocalSceneStatus], page_data.statuses)
    _render_record3d_sequence_explorer(context, record3d_statuses)
    _render_record3d_loop_preview(context, record3d_statuses, normalized)
    _render_catalog(page_data.rows)


def _render_download_card(
    *, dataset_root: Path, download_label: str, render_form: Callable[[], DownloadFormT]
) -> DownloadFormT:
    with st.container(border=True):
        st.subheader("Download Scenes")
        st.caption(f"Dataset root: `{dataset_root}`")
        return render_form()


def _render_notice(level: str | None, message: str) -> None:
    if level:
        {"error": st.error, "warning": st.warning, "success": st.success}[level](message)


def _build_tum_rgbd_page_data(context: AppContext, form: _DownloadFormData) -> DatasetPageData:
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
                "Local": status.sequence_dir is not None,
                "Replay Ready": status.replay_ready,
                "Offline Ready": status.offline_ready,
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


def _record3d_scene_rows(statuses: list[Record3DLocalSceneStatus]) -> list[DatasetTableRow]:
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
                "Local": status.sequence_dir is not None,
                "Replay Ready": status.replay_ready,
                "Offline Ready": status.offline_ready,
            }
        )
    return rows


def _rows_with_normalized_status(
    dataset_id: DatasetId,
    rows: list[DatasetTableRow],
    normalized: NormalizedDatasetSnapshot,
) -> list[DatasetTableRow]:
    return [{**row, "Normalized": _row_sequence_id(dataset_id, row) in normalized.sequence_ids} for row in rows]


def _record3d_rows_with_normalized_status(
    rows: list[DatasetTableRow],
    normalized: NormalizedDatasetSnapshot,
) -> list[DatasetTableRow]:
    return [
        {
            **row,
            "Normalized": str(row.get("Sequence", "")) in normalized.sequence_ids,
            "Normalized Profiles": normalized.profile_counts.get(str(row.get("Sequence", "")), 0),
        }
        for row in rows
    ]


def _row_sequence_id(dataset_id: DatasetId, row: DatasetTableRow) -> str:
    if dataset_id is DatasetId.ADVIO:
        return str(row.get("Sequence", row.get("Scene", "")))
    return str(row.get("Sequence", ""))


def _load_normalized_dataset_snapshot_for_context(
    context: AppContext, dataset_id: DatasetId
) -> NormalizedDatasetSnapshot:
    return _load_normalized_dataset_snapshot(
        context.path_config.root.as_posix(),
        context.path_config.data_dir.as_posix(),
        dataset_id.value,
        _normalized_store_fingerprint(context, dataset_id),
    )


def _render_normalized_characterization(normalized: NormalizedDatasetSnapshot) -> None:
    with st.container(border=True):
        st.subheader("Normalized Dataset Characterization")
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
        storage_bytes = _sum_stat(normalized.stats, "storage_bytes")
        frame_count = _sum_stat(normalized.stats, "frame_count", artifact_kind="timing")
        duration_s = _sum_stat(normalized.stats, "duration_s", artifact_kind="timing")
        for column, (label, value) in zip(
            st.columns(4, gap="small"),
            (
                ("Normalized Entries", str(len(normalized.records))),
                ("Frames", f"{int(frame_count):,}"),
                ("Duration", f"{duration_s:.1f} s"),
                ("Storage", _format_bytes(storage_bytes)),
            ),
            strict=True,
        ):
            column.metric(label, value)
        tabs = st.tabs(["Entries", "Stats", "Metadata"])
        with tabs[0]:
            st.dataframe(normalized.records, hide_index=True, width="stretch")
        with tabs[1]:
            st.dataframe(normalized.stats, hide_index=True, width="stretch")
        with tabs[2]:
            st.dataframe(normalized.metadata, hide_index=True, width="stretch")


@st.cache_data
def _load_normalized_dataset_snapshot(
    root: str, data_dir: str, dataset_id: str, freshness_token: tuple[tuple[str, int, int], ...]
) -> NormalizedDatasetSnapshot:
    del freshness_token
    path_config = PathConfig(root=Path(root), data_dir=Path(data_dir))
    query = NormalizedDatasetQuery.from_path_config(path_config)
    dataset = DatasetId(dataset_id)
    entries = query.records([dataset])
    records = query.record_rows(records=entries)
    profile_counts: dict[str, int] = {}
    for row in records:
        sequence_id = str(row.get("sequence_id", ""))
        profile_counts[sequence_id] = profile_counts.get(sequence_id, 0) + 1
    return NormalizedDatasetSnapshot(
        records=records,
        stats=query.stats_long_rows(records=entries),
        metadata=query.metadata_long_rows(records=entries),
        issues=query.issue_rows([dataset]),
        sequence_ids=set(profile_counts),
        default_profile_sequence_ids=_default_profile_sequence_ids(
            dataset=dataset, entries=entries, path_config=path_config
        ),
        profile_counts=profile_counts,
    )


def _default_profile_sequence_ids(
    *, dataset: DatasetId, entries: list[NormalizedDatasetEntry], path_config: PathConfig
) -> set[str]:
    if dataset is not DatasetId.RECORD3D:
        return {str(entry.sequence_id) for entry in entries}
    service = dataset_service(dataset, path_config)
    default_sequence_ids: set[str] = set()
    for entry in entries:
        source_config = source_config_for_normalization(dataset_id=dataset, sequence_id=str(entry.sequence_id))
        profile = normalized_profile_for_dataset(dataset_id=dataset, service=service, source_config=source_config)
        if entry.profile_key == profile.profile_key:
            default_sequence_ids.add(str(entry.sequence_id))
    return default_sequence_ids


def _sum_stat(stats: list[JsonObject], stat_name: str, *, artifact_kind: str | None = None) -> float:
    total = 0.0
    for row in stats:
        if row.get("stat_name") != stat_name:
            continue
        if artifact_kind is not None and row.get("artifact_kind") != artifact_kind:
            continue
        value = row.get("value")
        if value not in (None, ""):
            total += float(value)
    return total


def _format_bytes(value: float) -> str:
    if value < 1_000_000:
        return f"{value / 1_000:.1f} KB"
    if value < 1_000_000_000:
        return f"{value / 1_000_000:.1f} MB"
    return f"{value / 1_000_000_000:.1f} GB"


def _normalized_store_fingerprint(context: AppContext, dataset_id: DatasetId) -> tuple[tuple[str, int, int], ...]:
    store_root = _dataset_root(context, dataset_id) / ".normalized"
    if not store_root.exists():
        return ()
    paths = sorted(
        path
        for pattern in (
            "*/*/entry.json",
            "*/*/sequence_manifest.json",
            "*/*/benchmark_inputs.json",
            "*/*/stats_long.csv",
            "*/*/metadata_long.csv",
        )
        for path in store_root.glob(pattern)
    )
    return tuple(
        (path.relative_to(store_root).as_posix(), path.stat().st_mtime_ns, path.stat().st_size) for path in paths
    )


def _dataset_root(context: AppContext, dataset_id: DatasetId) -> Path:
    match dataset_id:
        case DatasetId.ADVIO:
            return context.advio_service.dataset_root
        case DatasetId.TUM_RGBD:
            return context.tum_rgbd_service.dataset_root
        case DatasetId.RECORD3D:
            return context.record3d_dataset_service.dataset_root
    raise AssertionError(f"Unsupported dataset_id: {dataset_id}")


def _load_tum_rgbd_explorer_sample(
    context: AppContext, *, sequence_id: str
) -> tuple[TumRgbdOfflineSample | None, str | None]:
    save_model_updates(context.store, context.state, context.state.tum_rgbd, explorer_sequence_id=sequence_id)
    try:
        return context.tum_rgbd_service.load_local_sample(sequence_id), None
    except (FileNotFoundError, ValueError) as exc:
        return None, str(exc)


def _load_record3d_explorer_sample(
    context: AppContext, *, sequence_id: str
) -> tuple[Record3DOfflineSample | None, str | None]:
    save_model_updates(
        context.store,
        context.state,
        context.state.record3d_dataset,
        explorer_sequence_id=sequence_id,
    )
    try:
        return context.record3d_dataset_service.load_local_sample(sequence_id), None
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


def _render_summary_metrics(summary: DatasetSummary) -> None:
    metrics = (
        ("Total Scenes", summary.total_scene_count),
        ("Local Scenes", summary.local_scene_count),
        ("Replay Ready", summary.replay_ready_scene_count),
        ("Offline Ready", summary.offline_ready_scene_count),
        ("Cached Archives", summary.cached_archive_count),
    )
    for column, (label, value) in zip(st.columns(5, gap="small"), metrics, strict=True):
        column.metric(label, str(value))


def _render_catalog(rows: list[DatasetTableRow]) -> None:
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
        request_type=AdvioDownloadRequest,
    )
    sync_advio_download_state(context, request)
    return AdvioDownloadFormData(request=request, submitted=submitted)


def _render_tum_rgbd_download_form(context: AppContext) -> _DownloadFormData:
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
        download_preset=request.preset,
        selected_modalities=request.modalities,
        overwrite_existing=request.overwrite,
    )
    return _DownloadFormData(request=request, submitted=submitted)


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
        preset_options, modality_options = _download_options_for_request(request_type)
        preset = st.selectbox(
            "Preset",
            options=list(preset_options),
            index=list(preset_options).index(page_state.download_preset),
            format_func=lambda option: option.label,
        )
        modalities = st.multiselect(
            "Modalities",
            options=list(modality_options),
            default=page_state.selected_modalities,
            format_func=lambda option: option.label,
            placeholder="Leave empty to use the selected preset",
        )
        overwrite = st.toggle("Overwrite existing archives and extracted files", value=page_state.overwrite_existing)
        submitted = st.form_submit_button("Download scenes", type="primary", width="stretch")
    return request_type(sequence_ids=sequence_ids, preset=preset, modalities=modalities, overwrite=overwrite), submitted


def _download_options_for_request(
    request_type: type[DownloadRequestT],
) -> tuple[
    tuple[AdvioDownloadPreset, ...] | tuple[TumRgbdDownloadPreset, ...],
    tuple[AdvioModality, ...] | tuple[TumRgbdModality, ...],
]:
    if request_type is AdvioDownloadRequest:
        return tuple(AdvioDownloadPreset), tuple(AdvioModality)
    return tuple(TumRgbdDownloadPreset), tuple(TumRgbdModality)


def _render_advio_sequence_explorer(context: AppContext, statuses: list[AdvioLocalSceneStatus]) -> None:
    _render_sequence_explorer_impl(
        context=context,
        statuses=statuses,
        page_state=context.state.advio,
        service=context.advio_service,
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


def _render_record3d_sequence_explorer(context: AppContext, statuses: list[Record3DLocalSceneStatus]) -> None:
    _render_sequence_explorer_impl(
        context=context,
        statuses=statuses,
        page_state=context.state.record3d_dataset,
        service=context.record3d_dataset_service,
        dataset_label="Record3D",
        load_sample=lambda selected_id: _load_record3d_explorer_sample(context, sequence_id=str(selected_id)),
        render_details=_render_record3d_sequence_details,
    )


def _render_sequence_explorer_impl(
    *,
    context: AppContext,
    statuses: StatusList,
    page_state: DatasetPageState,
    service: DatasetService,
    dataset_label: str,
    load_sample: Callable[[SequenceId], tuple[ExplorerSample | None, str | None]],
    render_details: Callable[[ExplorerSample], None],
) -> None:
    del context
    offline_ids = [status.scene.sequence_id for status in statuses if status.offline_ready]
    has_partial_scene = any(status.sequence_dir is not None and not status.offline_ready for status in statuses)
    with st.container(border=True):
        st.subheader("Sequence Explorer")
        if not offline_ids:
            (st.warning if has_partial_scene else st.info)(
                f"Local {dataset_label} scenes exist, but none are complete yet. Finish downloading a full scene to unlock trajectory and timing views."
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
    pose_frame_mode = st.segmented_control(
        "Trajectory Comparison",
        options=[AdvioPoseFrameMode.PROVIDER_WORLD, AdvioPoseFrameMode.LOCAL_FIRST_POSE],
        default=AdvioPoseFrameMode.PROVIDER_WORLD,
        format_func=lambda item: item.label,
        selection_mode="single",
        width="stretch",
        key=f"advio_compare_mode_{sample.sequence_id}",
    )
    resolved_mode = AdvioPoseFrameMode.PROVIDER_WORLD if pose_frame_mode is None else pose_frame_mode
    st.caption(
        "Provider World shows each trajectory in its own source frame. Local First Pose rebases each trajectory to its own first valid pose."
    )
    trajectories = plots.build_advio_comparison_trajectories(
        ground_truth=sample.ground_truth,
        arcore=sample.arcore,
        arkit=sample.arkit,
        pose_frame_mode=resolved_mode,
    )
    timing = [
        ("Video Frames", sample.frame_timestamps_ns.astype(np.float64) / 1e9),
        ("Ground Truth", np.asarray(sample.ground_truth.timestamps, dtype=np.float64)),
        ("ARCore", np.asarray(sample.arcore.timestamps, dtype=np.float64)),
    ]
    if sample.arkit is not None:
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
        bev_axes=(0, 2),
        height_axis=1,
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


def _render_record3d_sequence_details(sample: Record3DOfflineSample) -> None:
    trajectory = _record3d_metadata_trajectory(sample)
    timestamps_s = sample.frame_timestamps_ns.astype(np.float64) / 1e9
    _render_sequence_details(
        duration_s=sample.duration_s,
        frame_count=int(len(sample.frames)),
        intrinsics=sample.depth_intrinsics,
        metrics=(("Depth", "Available"),),
        trajectories=[("Record3D / ARKit", trajectory)],
        timing=[
            ("RGB-D Frames", timestamps_s),
            ("Record3D / ARKit", timestamps_s),
        ],
        paths=(
            ("Archive", sample.archive_path),
            ("RGB Intrinsics", f"{sample.rgb_intrinsics.width_px}x{sample.rgb_intrinsics.height_px}"),
            ("Depth Intrinsics", f"{sample.depth_intrinsics.width_px}x{sample.depth_intrinsics.height_px}"),
        ),
        bev_axes=(0, 2),
        height_axis=1,
    )


def _record3d_metadata_trajectory(sample: Record3DOfflineSample) -> PoseTrajectory3D:
    pose_fields = np.asarray([pose.to_tum_fields() for pose in sample.poses_world_camera], dtype=np.float64)
    if pose_fields.size == 0:
        return PoseTrajectory3D(
            positions_xyz=np.zeros((0, 3), dtype=np.float64),
            orientations_quat_wxyz=np.zeros((0, 4), dtype=np.float64),
            timestamps=np.asarray([], dtype=np.float64),
        )
    quaternions_xyzw = pose_fields[:, 3:]
    quaternion_norms = np.linalg.norm(quaternions_xyzw, axis=1, keepdims=True)
    if np.any(quaternion_norms == 0.0):
        raise ValueError("Record3D metadata trajectory contains a zero-norm quaternion.")
    return PoseTrajectory3D(
        positions_xyz=pose_fields[:, :3],
        orientations_quat_wxyz=np.roll(quaternions_xyzw / quaternion_norms, 1, axis=1),
        timestamps=sample.frame_timestamps_ns.astype(np.float64) / 1e9,
    )


def _render_sequence_details(
    *,
    duration_s: float,
    frame_count: int,
    intrinsics: CameraIntrinsics,
    metrics: tuple[tuple[str, str], ...],
    trajectories: list[tuple[str, PoseTrajectory3D]],
    timing: list[tuple[str, np.ndarray]],
    paths: tuple[tuple[str, Path | str], ...],
    bev_axes: tuple[int, int] = (0, 1),
    height_axis: int = 2,
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
            plots.build_bev_trajectory_figure(trajectories, plane_axes=bev_axes),
            plots.build_3d_trajectory_figure(trajectories, pose_axes_name="Ground Truth", pose_axis_stride=30),
        ),
        (
            plots.build_speed_profile_figure(trajectories),
            plots.build_height_profile_figure(trajectories, height_axis=height_axis),
        ),
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
        pose_source_options=lambda selected_id: _advio_preview_pose_sources(statuses, sequence_id=int(selected_id)),
        caption="Run a replay-ready ADVIO scene in a local loop with the PyAV replay source and inspect frames, trajectory, and camera metadata live.",
        option_label="Normalize video display orientation",
        option_key="preview_normalize_video_orientation",
        initial_option_value=context.state.advio.preview_normalize_video_orientation,
        action_key_prefix="advio-loop-preview",
        action=lambda selected_id, pose_source, option_value, start, stop: handle_advio_preview_action(
            context,
            AdvioPreviewFormData(
                sequence_id=int(selected_id),
                pose_source=pose_source,
                normalize_video_orientation=option_value,
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
        pose_source_options=None,
        caption="Run a replay-ready TUM RGB-D scene in a local loop and inspect RGB-D frames, trajectory, and camera metadata live.",
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
    statuses: list[Record3DLocalSceneStatus],
    normalized: NormalizedDatasetSnapshot,
) -> None:
    normalized_statuses = [
        status for status in statuses if status.scene.sequence_id in normalized.default_profile_sequence_ids
    ]
    _render_loop_preview_impl(
        statuses=normalized_statuses,
        page_state=context.state.record3d_dataset,
        service=context.record3d_dataset_service,
        pose_source_type=Record3DDatasetPoseSource,
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
    statuses: StatusList,
    page_state: DatasetPageState,
    service: DatasetService,
    pose_source_type: type[StrEnum],
    pose_source_options: Callable[[SequenceId], list[StrEnum]] | None,
    caption: str,
    option_label: str,
    option_key: str,
    initial_option_value: bool,
    action_key_prefix: str,
    action: Callable[[SequenceId, StrEnum, bool, bool, bool], str | None],
    sync_snapshot: Callable[[], AdvioPreviewSnapshot],
) -> None:
    previewable_ids = [status.scene.sequence_id for status in statuses if status.replay_ready]
    with st.container(border=True):
        st.subheader("Loop Preview")
        st.caption(caption)
        if not previewable_ids:
            st.info("Download at least one complete scene to unlock loop preview.")
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
            key=f"{action_key_prefix}:scene",
        )
        available_pose_sources = (
            list(pose_source_type) if pose_source_options is None else pose_source_options(selected_id)
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


def _advio_preview_pose_sources(
    statuses: list[AdvioLocalSceneStatus],
    *,
    sequence_id: int,
) -> list[AdvioPoseSource]:
    status = next((status for status in statuses if status.scene.sequence_id == sequence_id), None)
    if status is None:
        return [AdvioPoseSource.GROUND_TRUTH, AdvioPoseSource.NONE]
    options = [AdvioPoseSource.GROUND_TRUTH, AdvioPoseSource.NONE]
    if status.arcore_ready:
        options.insert(1, AdvioPoseSource.ARCORE)
    if status.arkit_ready:
        options.append(AdvioPoseSource.ARKIT)
    return options


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
