"""Dataset-owned contracts."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import Field, model_validator

from prml_vslam.utils import BaseConfig, BaseData

SequenceKey = int | str
SceneT = TypeVar("SceneT", bound=BaseData)
ModalityT = TypeVar("ModalityT", bound=StrEnum)
SequenceT = TypeVar("SequenceT", int, str)


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"
    TUM_RGBD = "tum_rgbd"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {self.ADVIO: "ADVIO", self.TUM_RGBD: "TUM RGB-D"}[self]


class FrameSelectionConfig(BaseConfig):
    frame_stride: int = Field(default=1, ge=1)
    target_fps: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def validate_single_sampling_mode(self) -> FrameSelectionConfig:
        if self.target_fps is not None and self.frame_stride != 1:
            raise ValueError("Configure either `frame_stride` or `target_fps`, not both.")
        return self

    def stride_for_timestamps_ns(self, timestamps_ns: Sequence[int]) -> int:
        if self.target_fps is None or len(timestamps_ns) < 2:
            return self.frame_stride
        duration_s = max((int(timestamps_ns[-1]) - int(timestamps_ns[0])) / 1e9, 0.0)
        native_fps = 0.0 if duration_s <= 0.0 else (len(timestamps_ns) - 1) / duration_s
        return max(1, int(round(native_fps / self.target_fps))) if native_fps > 0.0 else 1

    def stride_for_timestamps_s(self, timestamps_s: Sequence[float]) -> int:
        return self.stride_for_timestamps_ns([int(round(value * 1e9)) for value in timestamps_s])


class DatasetDownloadResult(BaseData, Generic[SequenceT, ModalityT]):
    """Summary of one explicit dataset download action."""

    sequence_ids: list[SequenceT]
    modalities: list[ModalityT]
    downloaded_archive_count: int = 0
    reused_archive_count: int = 0
    written_path_count: int = 0


class LocalSceneStatus(BaseData, Generic[SceneT, ModalityT]):
    """Local availability summary for one dataset scene."""

    scene: SceneT
    sequence_dir: Path | None = None
    local_modalities: list[ModalityT] = Field(default_factory=list)
    archive_path: Path | None = None
    replay_ready: bool = False
    offline_ready: bool = False


class DatasetSummary(BaseData):
    """High-level summary of committed and local dataset coverage."""

    total_scene_count: int
    local_scene_count: int
    replay_ready_scene_count: int
    offline_ready_scene_count: int
    cached_archive_count: int
    total_remote_archive_bytes: int


__all__ = [
    "DatasetDownloadResult",
    "DatasetId",
    "DatasetSummary",
    "FrameSelectionConfig",
    "LocalSceneStatus",
    "SequenceKey",
]
