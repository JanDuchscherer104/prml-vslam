"""TUM RGB-D-specific metadata and config models.

This module owns the committed scene catalog metadata, download DTOs, and
sequence config used by the TUM RGB-D adapter. The actual normalization and
replay logic lives in :mod:`prml_vslam.sources.datasets.tum_rgbd.tum_rgbd_sequence` and
:mod:`prml_vslam.sources.datasets.tum_rgbd.tum_rgbd_service`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field

from prml_vslam.sources.datasets.contracts import ReferenceCloudConfig
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
    overwrite: bool = False


class TumRgbdSequenceConfig(BaseConfig):
    """Configure one local TUM RGB-D sequence owner."""

    dataset_root: Path = Path(".data/tum_rgbd")
    sequence_id: str
    reference_cloud: ReferenceCloudConfig = Field(default_factory=ReferenceCloudConfig)
