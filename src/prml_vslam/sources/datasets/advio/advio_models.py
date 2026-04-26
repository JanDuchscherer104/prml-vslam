"""ADVIO-specific metadata and config models.

This module owns the committed scene catalog metadata, download request DTOs,
and sequence config used by the ADVIO adapter. The actual normalization and
replay logic lives in :mod:`prml_vslam.sources.datasets.advio.advio_sequence` and
:mod:`prml_vslam.sources.datasets.advio.advio_service`.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import Field, field_validator

from prml_vslam.sources.datasets.contracts import DatasetDownloadResult, DatasetSummary, LocalSceneStatus
from prml_vslam.utils import BaseConfig, BaseData, FactoryConfig

if TYPE_CHECKING:
    from prml_vslam.sources.datasets.advio.advio_sequence import AdvioSequence

ADVIO_SEQUENCE_COUNT = 23


class AdvioEnvironment(StrEnum):
    """Environment labels committed from the official ADVIO scene table."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"

    @property
    def label(self) -> str:
        """Return the user-facing environment label."""
        return self.value.capitalize()


class AdvioPeopleLevel(StrEnum):
    """Crowd-density labels committed from the official ADVIO scene table."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def label(self) -> str:
        """Return the user-facing crowd-density label."""
        return self.value.capitalize()


class AdvioModality(StrEnum):
    """Downloadable ADVIO modality bundles exposed in the CLI and app."""

    CALIBRATION = "calibration"
    GROUND_TRUTH = "ground_truth"
    IPHONE_VIDEO = "iphone_video"
    IPHONE_SENSORS = "iphone_sensors"
    IPHONE_ARKIT = "iphone_arkit"
    PIXEL_ARCORE = "pixel_arcore"
    TANGO = "tango"

    @property
    def label(self) -> str:
        """Return the user-facing modality label shown in ADVIO controls."""
        return {
            self.CALIBRATION: "Calibration",
            self.GROUND_TRUTH: "Ground Truth",
            self.IPHONE_VIDEO: "iPhone Video",
            self.IPHONE_SENSORS: "iPhone Sensors",
            self.IPHONE_ARKIT: "ARKit Baseline",
            self.PIXEL_ARCORE: "ARCore Baseline",
            self.TANGO: "Tango Bundle",
        }[self]


class AdvioDownloadPreset(StrEnum):
    """Curated modality bundles for common ADVIO workflows."""

    STREAMING = "streaming"
    OFFLINE = "offline"
    FULL = "full"

    @property
    def label(self) -> str:
        """Return the user-facing preset label shown in ADVIO download controls."""
        return self.value.capitalize()

    @property
    def modalities(self) -> tuple[AdvioModality, ...]:
        """Return the effective modality bundle for the selected preset."""
        return {
            self.STREAMING: (
                AdvioModality.CALIBRATION,
                AdvioModality.GROUND_TRUTH,
                AdvioModality.IPHONE_VIDEO,
            ),
            self.OFFLINE: (
                AdvioModality.CALIBRATION,
                AdvioModality.GROUND_TRUTH,
                AdvioModality.IPHONE_VIDEO,
                AdvioModality.IPHONE_SENSORS,
                AdvioModality.IPHONE_ARKIT,
                AdvioModality.PIXEL_ARCORE,
            ),
            self.FULL: tuple(AdvioModality),
        }[self]


class AdvioUpstreamMetadata(BaseData):
    """Describe the committed upstream ADVIO metadata sources for the adapter."""

    repo_url: str
    zenodo_record_url: str
    doi: str
    license: str
    calibration_base_url: str


class AdvioSceneMetadata(BaseData):
    """Describe one ADVIO scene committed into the repository catalog."""

    sequence_id: int
    sequence_slug: str
    venue: str
    dataset_code: str
    environment: AdvioEnvironment
    has_stairs: bool
    has_escalator: bool
    has_elevator: bool
    people_level: AdvioPeopleLevel
    has_vehicles: bool
    calibration_name: str
    archive_url: str
    archive_size_bytes: int
    archive_md5: str

    @property
    def display_name(self) -> str:
        """Return the compact scene label shown in the app and CLI."""
        return f"{self.sequence_slug} · {self.venue} {self.dataset_code}"


class AdvioCatalog(BaseData):
    """Bundle the committed ADVIO catalog plus upstream metadata provenance."""

    dataset_id: str
    dataset_label: str
    upstream: AdvioUpstreamMetadata
    scenes: list[AdvioSceneMetadata]


class AdvioDownloadRequest(BaseConfig):
    """Explicit ADVIO download selection used by the CLI and Streamlit app."""

    sequence_ids: list[int] = Field(default_factory=list)
    """Selected sequence ids. An empty selection means all scenes."""

    preset: AdvioDownloadPreset = AdvioDownloadPreset.OFFLINE
    """Curated modality bundle used when no explicit modality override is provided."""

    modalities: list[AdvioModality] = Field(default_factory=list)
    """Optional explicit modality override."""

    overwrite: bool = False
    """Whether existing archives and extracted files should be replaced."""

    @field_validator("sequence_ids")
    @classmethod
    def validate_sequence_ids(cls, value: list[int]) -> list[int]:
        """Normalize and validate explicit scene selections."""
        normalized = sorted(set(value))
        for sequence_id in normalized:
            if sequence_id < 1 or sequence_id > ADVIO_SEQUENCE_COUNT:
                msg = f"ADVIO sequence id must be in [1, {ADVIO_SEQUENCE_COUNT}], got {sequence_id}"
                raise ValueError(msg)
        return normalized

    @field_validator("modalities")
    @classmethod
    def validate_modalities(cls, value: list[AdvioModality]) -> list[AdvioModality]:
        """Remove duplicate modality overrides while preserving order."""
        return list(dict.fromkeys(value))

    def resolved_modalities(self) -> tuple[AdvioModality, ...]:
        """Return the effective modality bundle for the request."""
        return tuple(self.modalities) if self.modalities else self.preset.modalities


class AdvioDownloadResult(DatasetDownloadResult[int, AdvioModality]):
    """Summary of one explicit ADVIO download action."""


class AdvioLocalSceneStatus(LocalSceneStatus[AdvioSceneMetadata, AdvioModality]):
    """Local availability summary for one ADVIO scene."""


class AdvioDatasetSummary(DatasetSummary):
    """High-level summary of committed and local ADVIO coverage."""


class AdvioSequenceConfig(BaseConfig, FactoryConfig["AdvioSequence"]):
    """Configure one local ADVIO sequence owner.

    This config is the main click-through bridge from app or pipeline selection
    into :class:`prml_vslam.sources.datasets.advio.advio_sequence.AdvioSequence`.
    """

    dataset_root: Path = Path(".data/advio")
    """Directory that stores extracted ADVIO sequences and calibration files."""

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    """1-based ADVIO sequence identifier."""

    @property
    def sequence_name(self) -> str:
        """Return the canonical ADVIO folder name used on disk."""
        return f"advio-{self.sequence_id:02d}"

    @field_validator("dataset_root")
    @classmethod
    def validate_dataset_root(cls, value: Path) -> Path:
        """Reject blank dataset roots before path resolution happens downstream."""
        if not str(value).strip():
            msg = "dataset_root must not be blank"
            raise ValueError(msg)
        return value

    @property
    def target_type(self) -> type[AdvioSequence]:
        """Return the expected sequence type for the config."""
        from prml_vslam.sources.datasets.advio.advio_sequence import AdvioSequence

        return AdvioSequence
