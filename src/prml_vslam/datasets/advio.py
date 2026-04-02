"""Small local ADVIO adapter for replay and offline dataset access.

This module intentionally avoids the broad helper surface from the original
dataset-adapter commit. It focuses on the two repo workflows that matter now:

- streaming-style replay of an existing local sample through the OpenCV producer
- offline access to exact timestamps, calibration, and trajectories for
  benchmarking or training jobs
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import urllib.request
import zipfile
from enum import StrEnum
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray
from pydantic import Field, field_validator

from prml_vslam.datasets.interfaces import TimedPoseTrajectory
from prml_vslam.io.cv2_producer import Cv2FrameProducer, Cv2ProducerConfig, Cv2ReplayMode
from prml_vslam.io.interfaces import CameraPose, PinholeCameraIntrinsics, VideoPacketStream
from prml_vslam.pipeline.contracts import SequenceManifest
from prml_vslam.utils import BaseConfig, Console, PathConfig
from prml_vslam.utils.geometry import SE3Pose, write_tum_trajectory

ADVIO_SEQUENCE_COUNT = 23
_ADVIO_CATALOG_PATH = Path(__file__).with_name("advio_catalog.json")
_POSE_FILE_NAMES = ("poses.csv", "pose.csv")
_CSV_FLOAT_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_NUMERIC_CSV_ROW_PATTERN = re.compile(
    rf"^\s*({_CSV_FLOAT_PATTERN}(?:\s*,\s*{_CSV_FLOAT_PATTERN})*)\s*$",
    flags=re.MULTILINE,
)
_DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
_CALIBRATION_BY_SEQUENCE = {
    range(1, 13): "iphone-02.yaml",
    range(13, 18): "iphone-03.yaml",
    range(18, 20): "iphone-01.yaml",
    range(20, 24): "iphone-04.yaml",
}
_IPHONE_VIDEO_FILES = ("frames.mov", "frames.csv")
_IPHONE_SENSOR_FILES = (
    "platform-location.csv",
    "accelerometer.csv",
    "gyroscope.csv",
    "magnetometer.csv",
    "barometer.csv",
)
_IPHONE_ARKIT_FILES = ("arkit.csv",)
_GROUND_TRUTH_FILES = ("poses.csv",)
_PIXEL_ARCORE_FILES = ("arcore.csv",)
_TANGO_REQUIRED_FILES = (
    "frames.mov",
    "frames.csv",
    "raw.csv",
    "area-learning.csv",
    "point-cloud.csv",
)


class AdvioPoseSource(StrEnum):
    """Trajectory source used for replay-time pose annotation."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"
    NONE = "none"


class AdvioEnvironment(StrEnum):
    """Environment labels committed from the official ADVIO scene table."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"

    @property
    def label(self) -> str:
        """Return the user-facing label."""
        return self.value.capitalize()


class AdvioPeopleLevel(StrEnum):
    """Crowd-density labels committed from the official ADVIO scene table."""

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @property
    def label(self) -> str:
        """Return the user-facing label."""
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
        """Return the user-facing modality label."""
        return {
            AdvioModality.CALIBRATION: "Calibration",
            AdvioModality.GROUND_TRUTH: "Ground Truth",
            AdvioModality.IPHONE_VIDEO: "iPhone Video",
            AdvioModality.IPHONE_SENSORS: "iPhone Sensors",
            AdvioModality.IPHONE_ARKIT: "ARKit Baseline",
            AdvioModality.PIXEL_ARCORE: "ARCore Baseline",
            AdvioModality.TANGO: "Tango Bundle",
        }[self]


class AdvioDownloadPreset(StrEnum):
    """Curated modality bundles for common ADVIO workflows."""

    STREAMING = "streaming"
    OFFLINE = "offline"
    FULL = "full"

    @property
    def label(self) -> str:
        """Return the user-facing preset label."""
        return {
            AdvioDownloadPreset.STREAMING: "Streaming",
            AdvioDownloadPreset.OFFLINE: "Offline",
            AdvioDownloadPreset.FULL: "Full",
        }[self]

    @property
    def modalities(self) -> tuple[AdvioModality, ...]:
        """Return the modality bundle implied by the preset."""
        return {
            AdvioDownloadPreset.STREAMING: (
                AdvioModality.CALIBRATION,
                AdvioModality.GROUND_TRUTH,
                AdvioModality.IPHONE_VIDEO,
            ),
            AdvioDownloadPreset.OFFLINE: (
                AdvioModality.CALIBRATION,
                AdvioModality.GROUND_TRUTH,
                AdvioModality.IPHONE_VIDEO,
                AdvioModality.IPHONE_SENSORS,
                AdvioModality.IPHONE_ARKIT,
                AdvioModality.PIXEL_ARCORE,
            ),
            AdvioDownloadPreset.FULL: tuple(AdvioModality),
        }[self]


class AdvioUpstreamMetadata(BaseConfig):
    """Pinned upstream metadata for repo-owned ADVIO downloads."""

    repo_url: str
    """Official upstream repository URL."""

    zenodo_record_url: str
    """Official Zenodo record URL hosting the per-scene archives."""

    doi: str
    """Dataset DOI published by the upstream authors."""

    license: str
    """Dataset license string published by the upstream authors."""

    calibration_base_url: str
    """Base URL for raw calibration YAML files in the upstream repository."""


class AdvioSceneMetadata(BaseConfig):
    """Committed metadata for one downloadable ADVIO scene archive."""

    sequence_id: int
    """1-based ADVIO sequence identifier."""

    sequence_slug: str
    """Canonical local folder name, for example `advio-15`."""

    venue: str
    """Short venue label from the official scene table."""

    dataset_code: str
    """Venue-local scene identifier from the official scene table."""

    environment: AdvioEnvironment
    """Indoor or outdoor environment category."""

    has_stairs: bool
    """Whether the official scene table marks stairs for this sequence."""

    has_escalator: bool
    """Whether the official scene table marks escalators for this sequence."""

    has_elevator: bool
    """Whether the official scene table marks elevators for this sequence."""

    people_level: AdvioPeopleLevel
    """Crowd-density label from the official scene table."""

    has_vehicles: bool
    """Whether the official scene table marks vehicles for this sequence."""

    calibration_name: str
    """Official calibration YAML name needed for this sequence."""

    archive_url: str
    """Direct scene archive download URL pinned from Zenodo."""

    archive_size_bytes: int
    """Packed scene archive size in bytes."""

    archive_md5: str
    """MD5 checksum published for the scene archive."""

    @property
    def display_name(self) -> str:
        """Return the compact scene label shown in the app and CLI."""
        return f"{self.sequence_slug} · {self.venue} {self.dataset_code}"


class AdvioCatalog(BaseConfig):
    """Repo-owned catalog metadata for the official ADVIO release."""

    dataset_id: str
    """Stable dataset slug."""

    dataset_label: str
    """Short user-facing dataset label."""

    upstream: AdvioUpstreamMetadata
    """Pinned upstream repository and archive source metadata."""

    scenes: list[AdvioSceneMetadata]
    """Committed metadata for all downloadable scenes."""


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
        if self.modalities:
            return tuple(self.modalities)
        return self.preset.modalities


class AdvioDownloadResult(BaseConfig):
    """Summary of one explicit ADVIO download action."""

    sequence_ids: list[int]
    """Sequence ids covered by the action."""

    modalities: list[AdvioModality]
    """Resolved modality bundle extracted for the selected scenes."""

    downloaded_archives: list[Path] = Field(default_factory=list)
    """Scene archives fetched from Zenodo during the action."""

    reused_archives: list[Path] = Field(default_factory=list)
    """Scene archives reused from the local cache."""

    written_paths: list[Path] = Field(default_factory=list)
    """Extracted or downloaded filesystem paths written during the action."""


class AdvioLocalSceneStatus(BaseConfig):
    """Local availability summary for one ADVIO scene."""

    scene: AdvioSceneMetadata
    """Committed scene metadata."""

    sequence_dir: Path | None = None
    """Resolved local scene directory when any scene content is present."""

    local_modalities: list[AdvioModality] = Field(default_factory=list)
    """Locally available modality bundles."""

    archive_path: Path | None = None
    """Cached local archive path when present."""

    replay_ready: bool = False
    """Whether the streaming bundle is fully available locally."""

    offline_ready: bool = False
    """Whether the offline bundle is fully available locally."""

    full_ready: bool = False
    """Whether the full modality bundle is available locally."""


class AdvioDatasetSummary(BaseConfig):
    """High-level summary of committed and local ADVIO coverage."""

    total_scene_count: int
    """Total scene count committed in the repo-owned catalog."""

    local_scene_count: int
    """Number of scenes with any extracted local content."""

    replay_ready_scene_count: int
    """Number of scenes that satisfy the streaming preset locally."""

    offline_ready_scene_count: int
    """Number of scenes that satisfy the offline preset locally."""

    full_scene_count: int
    """Number of scenes with the full modality bundle locally."""

    cached_archive_count: int
    """Number of cached scene ZIP archives stored locally."""

    total_remote_archive_bytes: int
    """Sum of packed archive sizes across all scenes in the catalog."""


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

    @property
    def calibration_name(self) -> str:
        """Return the official calibration YAML name for this sequence."""
        for sequence_range, calibration_name in _CALIBRATION_BY_SEQUENCE.items():
            if self.sequence_id in sequence_range:
                return calibration_name
        msg = f"No calibration mapping defined for ADVIO sequence {self.sequence_id}"
        raise ValueError(msg)

    @field_validator("dataset_root")
    @classmethod
    def validate_dataset_root(cls, value: Path) -> Path:
        """Reject empty dataset roots."""
        if not str(value).strip():
            msg = "dataset_root must not be blank"
            raise ValueError(msg)
        return value


class AdvioSequencePaths(BaseConfig):
    """Resolved filesystem paths for one local ADVIO sequence."""

    config: AdvioSequenceConfig
    """Sequence config that produced these paths."""

    sequence_dir: Path
    """Extracted sequence directory."""

    video_path: Path
    """Path to the iPhone RGB input video."""

    frame_timestamps_path: Path
    """Path to the exact iPhone frame timestamps CSV."""

    ground_truth_csv_path: Path
    """Path to the official ground-truth trajectory CSV."""

    arcore_csv_path: Path
    """Path to the Pixel ARCore baseline trajectory CSV."""

    arkit_csv_path: Path | None = None
    """Path to the iPhone ARKit baseline trajectory CSV when present."""

    calibration_path: Path
    """Path to the sequence calibration YAML."""

    accelerometer_csv_path: Path | None = None
    """Optional accelerometer CSV path for offline VIO jobs."""

    gyroscope_csv_path: Path | None = None
    """Optional gyroscope CSV path for offline VIO jobs."""

    @classmethod
    def resolve(cls, config: AdvioSequenceConfig) -> AdvioSequencePaths:
        """Resolve the required local file layout for one sequence."""
        sequence_dir = _resolve_sequence_dir(config)
        paths = cls(
            config=config,
            sequence_dir=sequence_dir,
            video_path=sequence_dir / "iphone" / "frames.mov",
            frame_timestamps_path=sequence_dir / "iphone" / "frames.csv",
            ground_truth_csv_path=_resolve_ground_truth_csv(sequence_dir),
            arcore_csv_path=sequence_dir / "pixel" / "arcore.csv",
            arkit_csv_path=_optional_existing_path(sequence_dir / "iphone" / "arkit.csv"),
            calibration_path=config.dataset_root / "calibration" / config.calibration_name,
            accelerometer_csv_path=_optional_existing_path(sequence_dir / "iphone" / "accelerometer.csv"),
            gyroscope_csv_path=_resolve_optional_named_path(sequence_dir / "iphone", ("gyroscope.csv", "gyro.csv")),
        )
        for path in (
            paths.video_path,
            paths.frame_timestamps_path,
            paths.ground_truth_csv_path,
            paths.arcore_csv_path,
            paths.calibration_path,
        ):
            if not path.exists():
                msg = f"Required ADVIO path is missing: {path}"
                raise FileNotFoundError(msg)
        return paths


class AdvioCalibration(BaseConfig):
    """Parsed ADVIO camera calibration."""

    calibration_path: Path
    """Source YAML path."""

    intrinsics: PinholeCameraIntrinsics
    """Pinhole intrinsics and distortion metadata."""

    t_cam_imu: NDArray[np.float64]
    """Rigid transform from camera to IMU coordinates as a 4x4 matrix."""


class AdvioOfflineSample(BaseConfig):
    """Minimal offline representation of one ADVIO sequence."""

    model_config = {"arbitrary_types_allowed": True}

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    """1-based sequence identifier."""

    sequence_name: str
    """Canonical sequence name."""

    paths: AdvioSequencePaths
    """Resolved file layout for the sequence."""

    frame_timestamps_ns: NDArray[np.int64]
    """Exact iPhone frame timestamps aligned to `video_path` frame indices."""

    calibration: AdvioCalibration
    """Parsed iPhone camera calibration."""

    ground_truth: TimedPoseTrajectory
    """Official reference trajectory."""

    arcore: TimedPoseTrajectory
    """Pixel ARCore baseline trajectory."""

    arkit: TimedPoseTrajectory | None = None
    """Optional iPhone ARKit baseline trajectory."""

    @property
    def duration_s(self) -> float:
        """Return the observed video duration from exact frame timestamps."""
        if self.frame_timestamps_ns.size < 2:
            return 0.0
        return float((self.frame_timestamps_ns[-1] - self.frame_timestamps_ns[0]) / 1e9)


class AdvioSequence(BaseConfig):
    """High-level adapter around one local ADVIO sequence."""

    config: AdvioSequenceConfig
    """Sequence config that identifies the sample on disk."""

    @property
    def paths(self) -> AdvioSequencePaths:
        """Resolve the local file layout for this sequence."""
        return AdvioSequencePaths.resolve(self.config)

    def load_offline_sample(self) -> AdvioOfflineSample:
        """Load the typed offline sample used by evaluation and training flows."""
        paths = self.paths
        return AdvioOfflineSample(
            sequence_id=self.config.sequence_id,
            sequence_name=self.config.sequence_name,
            paths=paths,
            frame_timestamps_ns=load_advio_frame_timestamps_ns(paths.frame_timestamps_path),
            calibration=load_advio_calibration(paths.calibration_path),
            ground_truth=load_advio_trajectory(paths.ground_truth_csv_path),
            arcore=load_advio_trajectory(paths.arcore_csv_path),
            arkit=(load_advio_trajectory(paths.arkit_csv_path) if paths.arkit_csv_path is not None else None),
        )

    def to_sequence_manifest(self, *, output_dir: Path | None = None) -> SequenceManifest:
        """Normalize the local ADVIO sequence into a shared sequence manifest."""
        sample = self.load_offline_sample()
        evaluation_dir = sample.paths.sequence_dir / "evaluation" if output_dir is None else output_dir
        evaluation_dir.mkdir(parents=True, exist_ok=True)

        reference_tum_path = evaluation_dir / "ground_truth.tum"
        if not reference_tum_path.exists():
            self.write_ground_truth_tum(reference_tum_path)

        arcore_tum_path = evaluation_dir / "arcore.tum"
        if not arcore_tum_path.exists():
            self.write_arcore_tum(arcore_tum_path)

        return SequenceManifest(
            sequence_id=sample.sequence_name,
            video_path=sample.paths.video_path,
            timestamps_path=sample.paths.frame_timestamps_path,
            intrinsics_path=sample.paths.calibration_path,
            reference_tum_path=reference_tum_path,
            arcore_tum_path=arcore_tum_path,
        )

    def open_stream(
        self,
        *,
        pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
        stride: int = 1,
        loop: bool = True,
        replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
    ) -> VideoPacketStream:
        """Open the sequence as a replayable RGB packet stream."""
        sample = self.load_offline_sample()
        poses_by_frame = _poses_for_frame_timestamps(
            sample.frame_timestamps_ns,
            _trajectory_for_pose_source(sample, pose_source),
        )
        return Cv2FrameProducer(
            Cv2ProducerConfig(
                video_path=sample.paths.video_path,
                frame_timestamps_ns=sample.frame_timestamps_ns.tolist(),
                stride=stride,
                loop=loop,
                replay_mode=replay_mode,
                intrinsics=sample.calibration.intrinsics,
                poses_by_frame=poses_by_frame,
                static_metadata={
                    "dataset": "ADVIO",
                    "sequence_id": sample.sequence_id,
                    "sequence_name": sample.sequence_name,
                    "pose_source": pose_source.value,
                },
            )
        )

    def write_ground_truth_tum(self, target_path: Path) -> Path:
        """Export the official ground-truth CSV in TUM trajectory format."""
        return write_advio_pose_tum(self.paths.ground_truth_csv_path, target_path)

    def write_arcore_tum(self, target_path: Path) -> Path:
        """Export the ARCore baseline CSV in TUM trajectory format."""
        return write_advio_pose_tum(self.paths.arcore_csv_path, target_path)

    def write_arkit_tum(self, target_path: Path) -> Path:
        """Export the ARKit baseline CSV in TUM trajectory format."""
        arkit_path = self.paths.arkit_csv_path
        if arkit_path is None:
            msg = f"Sequence {self.config.sequence_name} does not include an ARKit baseline CSV."
            raise FileNotFoundError(msg)
        return write_advio_pose_tum(arkit_path, target_path)


@lru_cache(maxsize=1)
def load_advio_catalog() -> AdvioCatalog:
    """Load the repo-owned ADVIO catalog metadata committed with the package."""
    payload = json.loads(_ADVIO_CATALOG_PATH.read_text(encoding="utf-8"))
    return AdvioCatalog.model_validate(payload)


class AdvioDatasetService:
    """Dataset-owned ADVIO summary and download surface for the CLI and app."""

    def __init__(self, path_config: PathConfig, *, catalog: AdvioCatalog | None = None) -> None:
        self.path_config = path_config
        self.catalog = load_advio_catalog() if catalog is None else catalog
        self.console = Console(__name__).child(self.__class__.__name__)

    @property
    def dataset_root(self) -> Path:
        """Return the repo-owned ADVIO root directory."""
        return self.path_config.resolve_dataset_dir(self.catalog.dataset_id)

    @property
    def archive_root(self) -> Path:
        """Return the cache directory used for downloaded scene archives."""
        return self.dataset_root / ".archives"

    def list_scenes(self) -> list[AdvioSceneMetadata]:
        """Return all catalog scenes in sequence-id order."""
        return list(self.catalog.scenes)

    def scene(self, sequence_id: int) -> AdvioSceneMetadata:
        """Return one catalog scene by id."""
        for scene in self.catalog.scenes:
            if scene.sequence_id == sequence_id:
                return scene
        msg = f"Unknown ADVIO scene id: {sequence_id}"
        raise KeyError(msg)

    def summarize(self) -> AdvioDatasetSummary:
        """Return high-level committed versus local ADVIO coverage."""
        statuses = self.local_scene_statuses()
        return AdvioDatasetSummary(
            total_scene_count=len(statuses),
            local_scene_count=sum(status.sequence_dir is not None for status in statuses),
            replay_ready_scene_count=sum(status.replay_ready for status in statuses),
            offline_ready_scene_count=sum(status.offline_ready for status in statuses),
            full_scene_count=sum(status.full_ready for status in statuses),
            cached_archive_count=sum(status.archive_path is not None for status in statuses),
            total_remote_archive_bytes=sum(scene.archive_size_bytes for scene in self.catalog.scenes),
        )

    def local_scene_statuses(self) -> list[AdvioLocalSceneStatus]:
        """Return local availability status for every catalog scene."""
        statuses: list[AdvioLocalSceneStatus] = []
        for scene in self.catalog.scenes:
            local_modalities = self._local_modalities(scene)
            statuses.append(
                AdvioLocalSceneStatus(
                    scene=scene,
                    sequence_dir=_resolve_existing_sequence_dir(self.dataset_root, scene.sequence_slug),
                    local_modalities=local_modalities,
                    archive_path=self._existing_archive_path(scene),
                    replay_ready=_modalities_present(local_modalities, AdvioDownloadPreset.STREAMING.modalities),
                    offline_ready=_modalities_present(local_modalities, AdvioDownloadPreset.OFFLINE.modalities),
                    full_ready=_modalities_present(local_modalities, AdvioDownloadPreset.FULL.modalities),
                )
            )
        return statuses

    def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
        """Download selected ADVIO scenes and extract the requested modalities."""
        dataset_root = self.path_config.resolve_dataset_dir(self.catalog.dataset_id, create=True)
        archive_root = self.archive_root
        archive_root.mkdir(parents=True, exist_ok=True)

        sequence_ids = request.sequence_ids or [scene.sequence_id for scene in self.catalog.scenes]
        modalities = request.resolved_modalities()
        downloaded_archives: list[Path] = []
        reused_archives: list[Path] = []
        written_paths: list[Path] = []

        for sequence_id in sequence_ids:
            scene = self.scene(sequence_id)
            if AdvioModality.CALIBRATION in modalities:
                calibration_path = self._ensure_calibration(scene, overwrite=request.overwrite)
                if calibration_path not in written_paths:
                    written_paths.append(calibration_path)

            archive_modalities = tuple(modality for modality in modalities if modality is not AdvioModality.CALIBRATION)
            if not archive_modalities:
                continue

            archive_path, downloaded = self._ensure_archive(scene, overwrite=request.overwrite)
            if downloaded:
                downloaded_archives.append(archive_path)
            else:
                reused_archives.append(archive_path)
            written_paths.extend(
                self._extract_modalities(
                    scene=scene,
                    archive_path=archive_path,
                    modalities=archive_modalities,
                    overwrite=request.overwrite,
                    dataset_root=dataset_root,
                )
            )

        return AdvioDownloadResult(
            sequence_ids=sequence_ids,
            modalities=list(modalities),
            downloaded_archives=downloaded_archives,
            reused_archives=reused_archives,
            written_paths=list(dict.fromkeys(written_paths)),
        )

    def scene_rows(self) -> list[dict[str, object]]:
        """Return a table-friendly summary row for each ADVIO scene."""
        rows: list[dict[str, object]] = []
        for status in self.local_scene_statuses():
            rows.append(
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
            )
        return rows

    def _local_modalities(self, scene: AdvioSceneMetadata) -> list[AdvioModality]:
        sequence_dir = _resolve_existing_sequence_dir(self.dataset_root, scene.sequence_slug)
        calibration_path = self.dataset_root / "calibration" / scene.calibration_name
        local_modalities: list[AdvioModality] = []

        if calibration_path.exists():
            local_modalities.append(AdvioModality.CALIBRATION)
        if sequence_dir is None:
            return local_modalities

        if _files_exist(sequence_dir / "ground-truth", _GROUND_TRUTH_FILES):
            local_modalities.append(AdvioModality.GROUND_TRUTH)
        if _files_exist(sequence_dir / "iphone", _IPHONE_VIDEO_FILES):
            local_modalities.append(AdvioModality.IPHONE_VIDEO)
        if _files_exist(sequence_dir / "iphone", _IPHONE_SENSOR_FILES):
            local_modalities.append(AdvioModality.IPHONE_SENSORS)
        if _files_exist(sequence_dir / "iphone", _IPHONE_ARKIT_FILES):
            local_modalities.append(AdvioModality.IPHONE_ARKIT)
        if _files_exist(sequence_dir / "pixel", _PIXEL_ARCORE_FILES):
            local_modalities.append(AdvioModality.PIXEL_ARCORE)
        if _files_exist(sequence_dir / "tango", _TANGO_REQUIRED_FILES):
            local_modalities.append(AdvioModality.TANGO)
        return local_modalities

    def _ensure_archive(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> tuple[Path, bool]:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        if archive_path.exists() and not overwrite:
            self._validate_archive_checksum(archive_path, scene.archive_md5)
            return archive_path, False

        self.console.info(f"Downloading {scene.sequence_slug} from {scene.archive_url}.")
        _download_binary_to_path(scene.archive_url, archive_path)
        self._validate_archive_checksum(archive_path, scene.archive_md5)
        return archive_path, True

    def _ensure_calibration(self, scene: AdvioSceneMetadata, *, overwrite: bool) -> Path:
        calibration_dir = self.dataset_root / "calibration"
        calibration_dir.mkdir(parents=True, exist_ok=True)
        calibration_path = calibration_dir / scene.calibration_name
        if calibration_path.exists() and not overwrite:
            return calibration_path

        calibration_url = f"{self.catalog.upstream.calibration_base_url}{scene.calibration_name}"
        self.console.info(f"Downloading calibration {scene.calibration_name} from {calibration_url}.")
        calibration_text = _download_text(calibration_url)
        calibration_path.write_text(calibration_text, encoding="utf-8")
        return calibration_path

    def _existing_archive_path(self, scene: AdvioSceneMetadata) -> Path | None:
        archive_path = self.archive_root / f"{scene.sequence_slug}.zip"
        return archive_path if archive_path.exists() else None

    def _validate_archive_checksum(self, archive_path: Path, expected_md5: str) -> None:
        actual_md5 = _md5_for_file(archive_path)
        if actual_md5 != expected_md5:
            msg = (
                f"Checksum mismatch for {archive_path}. Expected {expected_md5}, got {actual_md5}. "
                "Remove the corrupted archive and retry the download."
            )
            raise ValueError(msg)

    def _extract_modalities(
        self,
        *,
        scene: AdvioSceneMetadata,
        archive_path: Path,
        modalities: tuple[AdvioModality, ...],
        overwrite: bool,
        dataset_root: Path,
    ) -> list[Path]:
        written_paths: list[Path] = []
        matched_members = 0
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                normalized = _normalize_archive_member(member.filename)
                if normalized is None:
                    continue
                relative_sequence_path = _relative_sequence_path(normalized, scene.sequence_slug)
                if relative_sequence_path is None:
                    continue
                if not _member_matches_modalities(relative_sequence_path, modalities):
                    continue
                matched_members += 1
                target_path = dataset_root / Path(*normalized)
                if target_path.exists() and not overwrite:
                    written_paths.append(target_path)
                    continue
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, target_path.open("wb") as sink:
                    sink.write(source.read())
                written_paths.append(target_path)

        if matched_members == 0:
            requested = ", ".join(modality.value for modality in modalities)
            msg = f"Archive {archive_path} did not contain any members for requested modalities: {requested}"
            raise ValueError(msg)
        return written_paths


def load_advio_sequence(config: AdvioSequenceConfig) -> AdvioOfflineSample:
    """Load the offline representation for one local ADVIO sequence."""
    return AdvioSequence(config=config).load_offline_sample()


def list_advio_sequence_ids(dataset_root: Path) -> list[int]:
    """Return the extracted ADVIO sequence ids available under `dataset_root`."""
    sequence_ids: set[int] = set()
    for root in (dataset_root, dataset_root / "data"):
        if not root.exists():
            continue
        for candidate in root.iterdir():
            if not candidate.is_dir() or not candidate.name.startswith("advio-"):
                continue
            try:
                sequence_ids.add(int(candidate.name.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return sorted(sequence_ids)


def load_advio_frame_timestamps_ns(path: Path) -> NDArray[np.int64]:
    """Load exact iPhone frame timestamps from `frames.csv` as nanoseconds."""
    rows = _read_numeric_csv(path, min_columns=1)
    if rows.size == 0:
        return np.empty(0, dtype=np.int64)
    timestamps_ns = np.rint(rows[:, 0] * 1e9).astype(np.int64, copy=False)
    return timestamps_ns


def load_advio_trajectory(path: Path) -> TimedPoseTrajectory:
    """Load an ADVIO trajectory CSV into dense NumPy arrays."""
    rows = _read_numeric_csv(path, min_columns=8)
    if rows.ndim != 2 or rows.shape[1] < 8:
        msg = f"Expected at least 8 columns in ADVIO pose CSV: {path}"
        raise ValueError(msg)
    return TimedPoseTrajectory(
        timestamps_s=rows[:, 0].astype(np.float64, copy=True),
        positions_xyz=rows[:, 1:4].astype(np.float64, copy=True),
        quaternions_xyzw=rows[:, [5, 6, 7, 4]].astype(np.float64, copy=True),
    )


def load_advio_calibration(path: Path) -> AdvioCalibration:
    """Parse an official ADVIO calibration YAML into a typed camera model."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected a YAML mapping in {path}"
        raise ValueError(msg)
    camera = _extract_camera_mapping(payload, calibration_path=path)
    intrinsics = _expect_float_list(camera, "intrinsics", "data", expected_len=4)
    distortion = _expect_mapping(camera, "distortion")
    distortion_parameters = tuple(_expect_float_list(distortion, "parameters", "data"))
    return AdvioCalibration(
        calibration_path=path,
        intrinsics=PinholeCameraIntrinsics(
            width_px=int(camera["image_width"]),
            height_px=int(camera["image_height"]),
            fx=intrinsics[0],
            fy=intrinsics[1],
            cx=intrinsics[2],
            cy=intrinsics[3],
            distortion_model=str(distortion.get("type")) if distortion.get("type") is not None else None,
            distortion_coefficients=distortion_parameters,
        ),
        t_cam_imu=np.asarray(_expect_matrix(camera, "T_cam_imu"), dtype=np.float64),
    )


def write_advio_pose_tum(source_path: Path, target_path: Path) -> Path:
    """Convert an ADVIO pose CSV into a TUM trajectory file."""
    trajectory = load_advio_trajectory(source_path)
    poses = [
        SE3Pose(
            qx=float(quaternion[0]),
            qy=float(quaternion[1]),
            qz=float(quaternion[2]),
            qw=float(quaternion[3]),
            tx=float(position[0]),
            ty=float(position[1]),
            tz=float(position[2]),
        )
        for position, quaternion in zip(
            trajectory.positions_xyz,
            trajectory.quaternions_xyzw,
            strict=True,
        )
    ]
    return write_tum_trajectory(
        target_path,
        poses,
        trajectory.timestamps_s.tolist(),
        include_header=True,
        decimal_places=9,
    )


def _trajectory_for_pose_source(
    sample: AdvioOfflineSample,
    pose_source: AdvioPoseSource,
) -> TimedPoseTrajectory | None:
    match pose_source:
        case AdvioPoseSource.GROUND_TRUTH:
            return sample.ground_truth
        case AdvioPoseSource.ARCORE:
            return sample.arcore
        case AdvioPoseSource.ARKIT:
            return sample.arkit
        case AdvioPoseSource.NONE:
            return None


def _poses_for_frame_timestamps(
    frame_timestamps_ns: NDArray[np.int64],
    trajectory: TimedPoseTrajectory | None,
) -> list[CameraPose | None]:
    if trajectory is None or frame_timestamps_ns.size == 0:
        return [None] * int(frame_timestamps_ns.size)

    target_timestamps_s = frame_timestamps_ns.astype(np.float64) / 1e9
    source_timestamps_s = trajectory.timestamps_s
    interpolated_positions = np.column_stack(
        [np.interp(target_timestamps_s, source_timestamps_s, trajectory.positions_xyz[:, axis]) for axis in range(3)]
    )
    nearest_indices = np.searchsorted(source_timestamps_s, target_timestamps_s, side="left")
    nearest_indices = np.clip(nearest_indices, 0, max(len(source_timestamps_s) - 1, 0))
    previous_indices = np.clip(nearest_indices - 1, 0, max(len(source_timestamps_s) - 1, 0))
    pick_previous = np.abs(target_timestamps_s - source_timestamps_s[previous_indices]) <= np.abs(
        source_timestamps_s[nearest_indices] - target_timestamps_s
    )
    nearest_indices = np.where(pick_previous, previous_indices, nearest_indices)

    poses: list[CameraPose] = []
    for position, nearest_index in zip(interpolated_positions, nearest_indices, strict=True):
        quaternion = trajectory.quaternions_xyzw[int(nearest_index)]
        poses.append(
            CameraPose(
                qx=float(quaternion[0]),
                qy=float(quaternion[1]),
                qz=float(quaternion[2]),
                qw=float(quaternion[3]),
                tx=float(position[0]),
                ty=float(position[1]),
                tz=float(position[2]),
            )
        )
    return poses


def _resolve_sequence_dir(config: AdvioSequenceConfig) -> Path:
    for candidate in (config.dataset_root / config.sequence_name, config.dataset_root / "data" / config.sequence_name):
        if candidate.is_dir():
            return candidate
    msg = f"ADVIO sequence {config.sequence_name} is not available under {config.dataset_root}"
    raise FileNotFoundError(msg)


def _resolve_ground_truth_csv(sequence_dir: Path) -> Path:
    for name in _POSE_FILE_NAMES:
        candidate = sequence_dir / "ground-truth" / name
        if candidate.exists():
            return candidate
    msg = f"Could not find a ground-truth pose CSV under {sequence_dir / 'ground-truth'}"
    raise FileNotFoundError(msg)


def _optional_existing_path(path: Path) -> Path | None:
    return path if path.exists() else None


def _resolve_optional_named_path(root: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _resolve_existing_sequence_dir(dataset_root: Path, sequence_slug: str) -> Path | None:
    for candidate in (dataset_root / sequence_slug, dataset_root / "data" / sequence_slug):
        if candidate.is_dir():
            return candidate
    return None


def _files_exist(root: Path, names: tuple[str, ...]) -> bool:
    return all((root / name).exists() for name in names)


def _modalities_present(
    local_modalities: list[AdvioModality],
    required_modalities: tuple[AdvioModality, ...],
) -> bool:
    available = set(local_modalities)
    return all(modality in available for modality in required_modalities)


def _normalize_archive_member(member_name: str) -> tuple[str, ...] | None:
    normalized = PurePosixPath(member_name)
    parts = tuple(part for part in normalized.parts if part not in {"", "."})
    if not parts or any(part == ".." for part in parts):
        return None
    return parts


def _relative_sequence_path(normalized_parts: tuple[str, ...], sequence_slug: str) -> PurePosixPath | None:
    if len(normalized_parts) >= 2 and normalized_parts[0] == "data":
        root_parts = normalized_parts[1:]
    else:
        root_parts = normalized_parts
    if not root_parts or root_parts[0] != sequence_slug:
        return None
    return PurePosixPath(*root_parts[1:])


def _member_matches_modalities(relative_path: PurePosixPath, modalities: tuple[AdvioModality, ...]) -> bool:
    parts = relative_path.parts
    if not parts:
        return False
    for modality in modalities:
        match modality:
            case AdvioModality.GROUND_TRUTH:
                if parts[0] == "ground-truth":
                    return True
            case AdvioModality.IPHONE_VIDEO:
                if parts[:1] == ("iphone",) and parts[1:] in {(name,) for name in _IPHONE_VIDEO_FILES}:
                    return True
            case AdvioModality.IPHONE_SENSORS:
                if parts[:1] == ("iphone",) and parts[1:] in {(name,) for name in _IPHONE_SENSOR_FILES}:
                    return True
            case AdvioModality.IPHONE_ARKIT:
                if parts == ("iphone", "arkit.csv"):
                    return True
            case AdvioModality.PIXEL_ARCORE:
                if parts == ("pixel", "arcore.csv"):
                    return True
            case AdvioModality.TANGO:
                if parts[0] == "tango":
                    return True
            case AdvioModality.CALIBRATION:
                continue
    return False


def _download_binary_to_path(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "prml-vslam"})
    with tempfile.NamedTemporaryFile(dir=target_path.parent, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        with urllib.request.urlopen(request, timeout=60) as response:
            while True:
                chunk = response.read(_DOWNLOAD_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                temp_file.write(chunk)
    temp_path.replace(target_path)


def _download_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "prml-vslam"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def _md5_for_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_DOWNLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _read_numeric_csv(path: Path, *, min_columns: int) -> NDArray[np.float64]:
    row_strings = np.asarray(_NUMERIC_CSV_ROW_PATTERN.findall(path.read_text(encoding="utf-8")), dtype=str)
    if row_strings.size == 0:
        return np.empty((0, 0), dtype=np.float64)

    column_counts = np.char.count(row_strings, ",").astype(np.int64) + 1
    min_count = int(column_counts.min())
    if min_count < min_columns:
        msg = f"Expected at least {min_columns} columns in {path}, got {min_count}"
        raise ValueError(msg)

    first_count = int(column_counts[0])
    if np.any(column_counts != first_count):
        msg = f"Expected a rectangular numeric CSV in {path}"
        raise ValueError(msg)

    numeric_text = "\n".join(row_strings.tolist()).replace(",", " ")
    return np.fromstring(numeric_text, sep=" ", dtype=np.float64).reshape(-1, first_count)


def _extract_camera_mapping(payload: dict[str, Any], *, calibration_path: Path) -> dict[str, Any]:
    cameras = payload.get("cameras")
    if not isinstance(cameras, list) or not cameras:
        msg = f"Expected a non-empty `cameras` list in {calibration_path}"
        raise ValueError(msg)
    camera_entry = cameras[0]
    if not isinstance(camera_entry, dict):
        msg = f"Expected a mapping camera entry in {calibration_path}"
        raise ValueError(msg)
    camera = camera_entry.get("camera")
    if not isinstance(camera, dict):
        msg = f"Expected a `camera` mapping in {calibration_path}"
        raise ValueError(msg)
    return camera


def _expect_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        msg = f"Expected `{key}` to be a mapping"
        raise ValueError(msg)
    return value


def _expect_float_list(
    mapping: dict[str, Any],
    key: str,
    nested_key: str,
    *,
    expected_len: int | None = None,
) -> list[float]:
    nested = _expect_mapping(mapping, key)
    values = nested.get(nested_key)
    if not isinstance(values, list):
        msg = f"Expected `{key}.{nested_key}` to be a list"
        raise ValueError(msg)
    floats = [float(value) for value in values]
    if expected_len is not None and len(floats) != expected_len:
        msg = f"Expected `{key}.{nested_key}` to have length {expected_len}, got {len(floats)}"
        raise ValueError(msg)
    return floats


def _expect_matrix(mapping: dict[str, Any], key: str) -> list[list[float]]:
    rows = _expect_mapping(mapping, key).get("data")
    if not isinstance(rows, list) or len(rows) != 4:
        msg = f"Expected `{key}.data` to be a 4x4 matrix"
        raise ValueError(msg)
    matrix: list[list[float]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 4:
            msg = f"Expected `{key}.data` to be a 4x4 matrix"
            raise ValueError(msg)
        matrix.append([float(value) for value in row])
    return matrix


__all__ = [
    "ADVIO_SEQUENCE_COUNT",
    "AdvioCalibration",
    "AdvioCatalog",
    "AdvioDatasetService",
    "AdvioDatasetSummary",
    "AdvioDownloadPreset",
    "AdvioDownloadRequest",
    "AdvioDownloadResult",
    "AdvioEnvironment",
    "AdvioLocalSceneStatus",
    "AdvioModality",
    "AdvioOfflineSample",
    "AdvioPeopleLevel",
    "AdvioPoseSource",
    "AdvioSceneMetadata",
    "AdvioSequence",
    "AdvioSequenceConfig",
    "AdvioSequencePaths",
    "AdvioUpstreamMetadata",
    "list_advio_sequence_ids",
    "load_advio_calibration",
    "load_advio_catalog",
    "load_advio_frame_timestamps_ns",
    "load_advio_sequence",
    "load_advio_trajectory",
    "write_advio_pose_tum",
]
