"""Controller helpers for the ADVIO Streamlit page."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from prml_vslam.datasets import (
    AdvioDatasetSummary,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioOfflineSample,
    AdvioPoseSource,
)
from prml_vslam.utils import BaseData

from .services import AdvioPreviewSnapshot, AdvioPreviewStreamState

if TYPE_CHECKING:
    from .bootstrap import AppContext


_ACTIVE_PREVIEW_STATES = {AdvioPreviewStreamState.CONNECTING, AdvioPreviewStreamState.STREAMING}


class AdvioDownloadFormData(BaseData):
    request: AdvioDownloadRequest
    submitted: bool = False


class AdvioPreviewFormData(BaseData):
    sequence_id: int
    pose_source: AdvioPoseSource
    respect_video_rotation: bool = False
    start_requested: bool = False
    stop_requested: bool = False


class AdvioPageData(BaseData):
    summary: AdvioDatasetSummary
    statuses: list[AdvioLocalSceneStatus]
    rows: list[dict[str, object]]
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message: str = ""


def build_advio_page_data(context: AppContext, form: AdvioDownloadFormData) -> AdvioPageData:
    notice_level, notice_message = _handle_download(context, form.request) if form.submitted else (None, "")
    statuses = context.advio_service.local_scene_statuses()
    return AdvioPageData(
        summary=context.advio_service.summarize(statuses),
        statuses=statuses,
        rows=_scene_rows(statuses),
        notice_level=notice_level,
        notice_message=notice_message,
    )


def sync_advio_download_state(context: AppContext, request: AdvioDownloadRequest) -> None:
    _save_page_state(
        context,
        selected_sequence_ids=request.sequence_ids,
        download_preset=request.preset,
        selected_modalities=request.modalities,
        overwrite_existing=request.overwrite,
    )


def load_advio_explorer_sample(
    context: AppContext, *, sequence_id: int
) -> tuple[AdvioOfflineSample | None, str | None]:
    _save_page_state(context, explorer_sequence_id=sequence_id)
    try:
        return context.advio_service.load_local_sample(sequence_id), None
    except (FileNotFoundError, ValueError) as exc:
        return None, str(exc)


def sync_advio_preview_state(context: AppContext, snapshot: AdvioPreviewSnapshot | None = None) -> AdvioPreviewSnapshot:
    snapshot = context.advio_runtime.snapshot() if snapshot is None else snapshot
    if context.state.advio.preview_is_running and snapshot.state not in _ACTIVE_PREVIEW_STATES:
        context.state.advio.preview_is_running = False
        context.store.save(context.state)
    return snapshot


def handle_advio_preview_action(context: AppContext, form: AdvioPreviewFormData) -> str | None:
    _save_page_state(
        context,
        preview_sequence_id=form.sequence_id,
        preview_pose_source=form.pose_source,
        preview_respect_video_rotation=form.respect_video_rotation,
    )
    if form.stop_requested:
        context.advio_runtime.stop()
        context.state.advio.preview_is_running = False
        context.store.save(context.state)
        return None
    if not form.start_requested:
        return None
    try:
        scene = context.advio_service.scene(form.sequence_id)
        context.advio_runtime.start(
            sequence_id=form.sequence_id,
            sequence_label=scene.display_name,
            pose_source=form.pose_source,
            stream=context.advio_service.open_preview_stream(
                sequence_id=form.sequence_id,
                pose_source=form.pose_source,
                respect_video_rotation=form.respect_video_rotation,
            ),
        )
        context.state.advio.preview_is_running = True
        context.store.save(context.state)
        return None
    except Exception as exc:
        context.state.advio.preview_is_running = False
        context.store.save(context.state)
        return str(exc)


def _save_page_state(context: AppContext, **updates: object) -> None:
    page_state = context.state.advio
    if all(getattr(page_state, key) == value for key, value in updates.items()):
        return
    for key, value in updates.items():
        setattr(page_state, key, value)
    context.store.save(context.state)


def _handle_download(
    context: AppContext, request: AdvioDownloadRequest
) -> tuple[Literal["error", "warning", "success"], str]:
    if not request.sequence_ids:
        return "warning", "Select at least one scene before starting a download."
    try:
        result = context.advio_service.download(request)
    except Exception as exc:
        return "error", str(exc)
    return (
        "success",
        f"Prepared {len(result.sequence_ids)} scene(s), fetched {len(result.downloaded_archives)} archive(s), and wrote {len(result.written_paths)} path(s).",
    )


def _scene_rows(statuses: list[AdvioLocalSceneStatus]) -> list[dict[str, object]]:
    return [
        {
            "Scene": status.scene.sequence_slug,
            "Venue": status.scene.venue,
            "Dataset": status.scene.dataset_code,
            "Environment": status.scene.environment.label,
            "Packed Size (MB)": round(status.scene.archive_size_bytes / 1e6, 1),
            "Local": status.sequence_dir is not None,
            "Replay Ready": status.replay_ready,
            "Offline Ready": status.offline_ready,
            "Local Modalities": ", ".join(modality.label for modality in status.local_modalities),
        }
        for status in statuses
    ]
