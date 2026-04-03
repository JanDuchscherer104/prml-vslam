"""Tiny controller helpers for the ADVIO Streamlit page."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from prml_vslam.datasets import AdvioDatasetSummary, AdvioDownloadRequest, AdvioLocalSceneStatus
from prml_vslam.utils import BaseData

if TYPE_CHECKING:
    from .bootstrap import AppContext


class AdvioDownloadFormData(BaseData):
    """Typed ADVIO download form payload."""

    request: AdvioDownloadRequest
    """Current download request."""

    submitted: bool = False
    """Whether the form was submitted."""


class AdvioPageData(BaseData):
    """Resolved ADVIO page snapshot and latest action feedback."""

    summary: AdvioDatasetSummary
    """Current dataset summary."""

    statuses: list[AdvioLocalSceneStatus]
    """Current local scene statuses."""

    rows: list[dict[str, object]]
    """Scene catalog rows."""

    notice_level: Literal["error", "warning", "success"] | None = None
    """Optional Streamlit notice level."""

    notice_message: str = ""
    """User-visible notice message."""


def build_advio_page_data(context: AppContext, form: AdvioDownloadFormData) -> AdvioPageData:
    """Handle the current action and return one fresh ADVIO page snapshot."""
    notice_level: Literal["error", "warning", "success"] | None = None
    notice_message = ""
    if form.submitted:
        notice_level, notice_message = _handle_download(context, form.request)
    summary, statuses, rows = _load_snapshot(context)
    return AdvioPageData(
        summary=summary,
        statuses=statuses,
        rows=rows,
        notice_level=notice_level,
        notice_message=notice_message,
    )


def _load_snapshot(
    context: AppContext,
) -> tuple[AdvioDatasetSummary, list[AdvioLocalSceneStatus], list[dict[str, object]]]:
    statuses = context.advio_service.local_scene_statuses()
    return (
        context.advio_service.summarize(),
        statuses,
        _scene_rows(statuses),
    )


def _handle_download(
    context: AppContext,
    request: AdvioDownloadRequest,
) -> tuple[Literal["error", "warning", "success"], str]:
    if not request.sequence_ids:
        return "warning", "Select at least one scene before starting a download."
    try:
        result = context.advio_service.download(request)
    except Exception as exc:
        return "error", str(exc)
    return (
        "success",
        f"Prepared {len(result.sequence_ids)} scene(s), fetched {len(result.downloaded_archives)} archive(s), "
        f"and wrote {len(result.written_paths)} path(s).",
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
