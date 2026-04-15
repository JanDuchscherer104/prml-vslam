"""Controller helpers for the ADVIO Streamlit page."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from prml_vslam.datasets.advio import (
    AdvioDatasetSummary,
    AdvioDownloadRequest,
    AdvioLocalSceneStatus,
    AdvioOfflineSample,
    AdvioPoseSource,
)
from prml_vslam.utils import BaseData

from .models import ACTIVE_PREVIEW_STREAM_STATES, AdvioPreviewSnapshot
from .state import save_model_updates

if TYPE_CHECKING:
    from .bootstrap import AppContext


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
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message = ""
    if form.submitted:
        try:
            result = context.advio_service.download(form.request)
        except Exception as exc:
            notice_level, notice_message = "error", str(exc)
        else:
            notice_level, notice_message = (
                "success",
                f"Prepared {len(result.sequence_ids)} scene(s), fetched {result.downloaded_archive_count} archive(s), and wrote {result.written_path_count} path(s).",
            )
    statuses = context.advio_service.local_scene_statuses()
    return AdvioPageData(
        summary=context.advio_service.summarize(statuses),
        statuses=statuses,
        rows=_scene_rows(statuses),
        notice_level=notice_level,
        notice_message=notice_message,
    )


def sync_advio_download_state(context: AppContext, request: AdvioDownloadRequest) -> None:
    """Persist the current ADVIO download-form state."""
    save_model_updates(
        context.store,
        context.state,
        context.state.advio,
        selected_sequence_ids=request.sequence_ids,
        download_preset=request.preset,
        selected_modalities=request.modalities,
        overwrite_existing=request.overwrite,
    )


def load_advio_explorer_sample(
    context: AppContext, *, sequence_id: int
) -> tuple[AdvioOfflineSample | None, str | None]:
    """Persist the current explorer selection and load its offline sample."""
    save_model_updates(context.store, context.state, context.state.advio, explorer_sequence_id=sequence_id)
    try:
        return context.advio_service.load_local_sample(sequence_id), None
    except (FileNotFoundError, ValueError) as exc:
        return None, str(exc)


def sync_advio_preview_state(context: AppContext, snapshot: AdvioPreviewSnapshot | None = None) -> AdvioPreviewSnapshot:
    """Keep persisted preview state aligned with the runtime snapshot."""
    snapshot = context.advio_runtime.snapshot() if snapshot is None else snapshot
    if context.state.advio.preview_is_running and snapshot.state not in ACTIVE_PREVIEW_STREAM_STATES:
        save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
    return snapshot


def handle_advio_preview_action(context: AppContext, form: AdvioPreviewFormData) -> str | None:
    """Apply one preview-form action and return an error message when it fails."""
    save_model_updates(
        context.store,
        context.state,
        context.state.advio,
        preview_sequence_id=form.sequence_id,
        preview_pose_source=form.pose_source,
        preview_respect_video_rotation=form.respect_video_rotation,
    )
    if form.stop_requested:
        context.advio_runtime.stop()
        save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
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
        save_model_updates(context.store, context.state, context.state.advio, preview_is_running=True)
        save_model_updates(context.store, context.state, context.state.tum_rgbd, preview_is_running=False)
        return None
    except Exception as exc:
        save_model_updates(context.store, context.state, context.state.advio, preview_is_running=False)
        return str(exc)


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
