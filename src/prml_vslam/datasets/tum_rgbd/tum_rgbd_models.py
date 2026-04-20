"""TUM RGB-D-specific metadata and config models.

This module owns the committed scene catalog metadata, download DTOs, and
sequence config used by the TUM RGB-D adapter. The actual normalization and
replay logic lives in :mod:`prml_vslam.datasets.tum_rgbd.tum_rgbd_sequence` and
:mod:`prml_vslam.datasets.tum_rgbd.tum_rgbd_service`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.datasets.contracts import DatasetDownloadResult, DatasetSummary, LocalSceneStatus
from prml_vslam.utils import BaseConfig, BaseData


class TumRgbdPoseSource(StrEnum):
    """Name the pose providers supported by the TUM RGB-D adapter."""

    GROUND_TRUTH = "ground_truth"
    NONE = "none"

    @property
    def label(self) -> str:
        """Return the user-facing pose-source label."""
        return {
            self.GROUND_TRUTH: "Ground Truth",
            self.NONE: "No Pose Overlay",
        }[self]


class TumRgbdModality(StrEnum):
    """Name the downloadable TUM RGB-D modality bundles."""

    RGB = "rgb"
    DEPTH = "depth"
    GROUND_TRUTH = "ground_truth"

    @property
    def label(self) -> str:
        """Return the user-facing modality label shown in TUM RGB-D controls."""
        return {
            self.RGB: "RGB Frames",
            self.DEPTH: "Depth Frames",
            self.GROUND_TRUTH: "Ground Truth",
        }[self]


class TumRgbdDownloadPreset(StrEnum):
    """Describe curated modality bundles for common TUM RGB-D workflows."""

    STREAMING = "streaming"
    OFFLINE = "offline"
    FULL = "full"

    @property
    def label(self) -> str:
        """Return the user-facing preset label shown in TUM RGB-D download controls."""
        return self.value.capitalize()

    @property
    def modalities(self) -> tuple[TumRgbdModality, ...]:
        """Return the effective modality bundle for the selected preset."""
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
    """Describe one TUM RGB-D scene committed into the repository catalog."""

    sequence_id: str
    folder_name: str
    display_name: str
    category: str
    archive_url: str
    archive_size_bytes: int = 0


class TumRgbdCatalog(BaseData):
    """Bundle the committed TUM RGB-D catalog and upstream metadata pointers."""

    dataset_id: str
    dataset_label: str
    upstream: dict[str, str]
    scenes: list[TumRgbdSceneMetadata]


class TumRgbdDownloadRequest(BaseConfig):
    """Describe one explicit TUM RGB-D download selection."""

    sequence_ids: list[str] = Field(default_factory=list)
    preset: TumRgbdDownloadPreset = TumRgbdDownloadPreset.OFFLINE
    modalities: list[TumRgbdModality] = Field(default_factory=list)
    overwrite: bool = False

    def resolved_modalities(self) -> tuple[TumRgbdModality, ...]:
        """Return the effective modality bundle for the request."""
        return tuple(self.modalities) if self.modalities else self.preset.modalities


class TumRgbdDownloadResult(DatasetDownloadResult[str, TumRgbdModality]):
    """Summary of one explicit TUM RGB-D download action."""


class TumRgbdLocalSceneStatus(LocalSceneStatus[TumRgbdSceneMetadata, TumRgbdModality]):
    """Local availability summary for one TUM RGB-D scene."""


class TumRgbdDatasetSummary(DatasetSummary):
    """High-level summary of committed and local TUM RGB-D coverage."""


class TumRgbdSequenceConfig(BaseConfig):
    """Configure one local TUM RGB-D sequence owner."""

    dataset_root: Path = Path(".data/tum_rgbd")
    sequence_id: str
