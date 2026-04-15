from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig, BaseData


class TumRgbdPoseSource(StrEnum):
    GROUND_TRUTH = "ground_truth"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            self.GROUND_TRUTH: "Ground Truth",
            self.NONE: "No Pose Overlay",
        }[self]


class TumRgbdModality(StrEnum):
    RGB = "rgb"
    DEPTH = "depth"
    GROUND_TRUTH = "ground_truth"

    @property
    def label(self) -> str:
        return {
            self.RGB: "RGB Frames",
            self.DEPTH: "Depth Frames",
            self.GROUND_TRUTH: "Ground Truth",
        }[self]


class TumRgbdDownloadPreset(StrEnum):
    STREAMING = "streaming"
    OFFLINE = "offline"
    FULL = "full"

    @property
    def label(self) -> str:
        return self.value.capitalize()

    @property
    def modalities(self) -> tuple[TumRgbdModality, ...]:
        return {
            self.STREAMING: (
                TumRgbdModality.RGB,
                TumRgbdModality.GROUND_TRUTH,
            ),
            self.OFFLINE: (
                TumRgbdModality.RGB,
                TumRgbdModality.DEPTH,
                TumRgbdModality.GROUND_TRUTH,
            ),
            self.FULL: tuple(TumRgbdModality),
        }[self]


class TumRgbdSceneMetadata(BaseData):
    sequence_id: str
    folder_name: str
    display_name: str
    category: str
    archive_url: str
    archive_size_bytes: int = 0


class TumRgbdCatalog(BaseData):
    dataset_id: str
    dataset_label: str
    upstream: dict[str, str]
    scenes: list[TumRgbdSceneMetadata]


class TumRgbdDownloadRequest(BaseConfig):
    sequence_ids: list[str] = Field(default_factory=list)
    preset: TumRgbdDownloadPreset = TumRgbdDownloadPreset.OFFLINE
    modalities: list[TumRgbdModality] = Field(default_factory=list)
    overwrite: bool = False

    def resolved_modalities(self) -> tuple[TumRgbdModality, ...]:
        return tuple(self.modalities) if self.modalities else self.preset.modalities


class TumRgbdDownloadResult(BaseData):
    sequence_ids: list[str]
    modalities: list[TumRgbdModality]
    downloaded_archive_count: int = 0
    reused_archive_count: int = 0
    written_path_count: int = 0


class TumRgbdLocalSceneStatus(BaseData):
    scene: TumRgbdSceneMetadata
    sequence_dir: Path | None = None
    local_modalities: list[TumRgbdModality] = Field(default_factory=list)
    archive_path: Path | None = None
    replay_ready: bool = False
    offline_ready: bool = False


class TumRgbdDatasetSummary(BaseData):
    total_scene_count: int
    local_scene_count: int
    replay_ready_scene_count: int
    offline_ready_scene_count: int
    cached_archive_count: int
    total_remote_archive_bytes: int


class TumRgbdSequenceConfig(BaseConfig):
    dataset_root: Path = Path(".data/tum_rgbd")
    sequence_id: str
