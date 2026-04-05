from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator

from prml_vslam.utils import BaseConfig, BaseData

ADVIO_SEQUENCE_COUNT = 23


class AdvioPoseSource(StrEnum):
    """Trajectory source used for replay-time pose annotation."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            self.GROUND_TRUTH: "Ground Truth",
            self.ARCORE: "ARCore",
            self.ARKIT: "ARKit",
            self.NONE: "No Pose Overlay",
        }[self]


class AdvioEnvironment(StrEnum):
    """Environment labels committed from the official ADVIO scene table."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"

    @property
    def label(self) -> str:
        return self.value.capitalize()


class AdvioPeopleLevel(StrEnum):
    """Crowd-density labels committed from the official ADVIO scene table."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def label(self) -> str:
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
        return {
            self.STREAMING: "Streaming",
            self.OFFLINE: "Offline",
            self.FULL: "Full",
        }[self]

    @property
    def modalities(self) -> tuple[AdvioModality, ...]:
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
    repo_url: str
    zenodo_record_url: str
    doi: str
    license: str
    calibration_base_url: str


class AdvioSceneMetadata(BaseData):
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


class AdvioDownloadResult(BaseData):
    """Summary of one explicit ADVIO download action."""

    sequence_ids: list[int]
    modalities: list[AdvioModality]
    downloaded_archive_count: int = 0
    reused_archive_count: int = 0
    written_path_count: int = 0


class AdvioLocalSceneStatus(BaseData):
    """Local availability summary for one ADVIO scene."""

    scene: AdvioSceneMetadata
    sequence_dir: Path | None = None
    local_modalities: list[AdvioModality] = Field(default_factory=list)
    archive_path: Path | None = None
    replay_ready: bool = False
    offline_ready: bool = False
    full_ready: bool = False


class AdvioDatasetSummary(BaseData):
    """High-level summary of committed and local ADVIO coverage."""

    total_scene_count: int
    local_scene_count: int
    replay_ready_scene_count: int
    offline_ready_scene_count: int
    full_scene_count: int
    cached_archive_count: int
    total_remote_archive_bytes: int


class AdvioSequenceConfig(BaseConfig):
    """Config describing one local ADVIO sequence."""

    dataset_root: Path = Path("data/advio")
    """Directory that stores extracted ADVIO sequences and calibration files."""

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    """1-based ADVIO sequence identifier."""

    @property
    def sequence_name(self) -> str:
        """Return the canonical ADVIO folder name."""
        return f"advio-{self.sequence_id:02d}"

    @field_validator("dataset_root")
    @classmethod
    def validate_dataset_root(cls, value: Path) -> Path:
        """Reject empty dataset roots."""
        if not str(value).strip():
            msg = "dataset_root must not be blank"
            raise ValueError(msg)
        return value
