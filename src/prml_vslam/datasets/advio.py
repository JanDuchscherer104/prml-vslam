"""ADVIO dataset adapter utilities.

The official ADVIO release ships as per-sequence ZIP archives on Zenodo and a
small calibration bundle in the upstream GitHub repository. This module keeps
the integration layer thin and repo-owned:

- download one sequence on demand
- resolve the relevant iPhone / ground-truth / ARCore paths
- load exact frame timestamps from ``frames.csv``
- convert ADVIO pose CSV files to TUM trajectories for ``evo``
- summarize dataset modalities for UI inspection and validation
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, field_validator

from prml_vslam.pipeline.contracts import (
    CaptureMetadataConfig,
    MethodId,
    PipelineMode,
    RunPlanRequest,
    TimestampSource,
)
from prml_vslam.utils import (
    BaseConfig,
    download_file,
    interpolate_numeric_rows,
    load_yaml_file,
    read_numeric_csv,
    resolve_first_existing,
    summarize_timestamped_csv,
)

ADVIO_SEQUENCE_COUNT = 23
ADVIO_ZENODO_RECORD = 1476931
ADVIO_DOWNLOAD_BASE = f"https://zenodo.org/record/{ADVIO_ZENODO_RECORD}/files"
ADVIO_CALIBRATION_BASE = "https://raw.githubusercontent.com/AaltoVision/ADVIO/master/calibration"

_POSE_FILE_NAMES = ("pose.csv", "poses.csv")
_CALIBRATION_BY_SEQUENCE = {
    range(1, 13): "iphone-02.yaml",
    range(13, 18): "iphone-03.yaml",
    range(18, 20): "iphone-01.yaml",
    range(20, 24): "iphone-04.yaml",
}
_TIMED_MODALITY_SPECS = (
    ("iphone_frames", "iPhone video timestamps", "video", Path("iphone/frames.csv"), "Input video clock"),
    (
        "iphone_accelerometer",
        "iPhone accelerometer",
        "imu",
        Path("iphone/accelerometer.csv"),
        "Linear acceleration",
    ),
    ("iphone_gyro", "iPhone gyroscope", "imu", Path("iphone/gyro.csv"), "Angular velocity"),
    (
        "iphone_magnetometer",
        "iPhone magnetometer",
        "imu",
        Path("iphone/magnetometer.csv"),
        "Magnetic field",
    ),
    (
        "iphone_barometer",
        "iPhone barometer",
        "environment",
        Path("iphone/barometer.csv"),
        "Pressure and altitude",
    ),
    (
        "iphone_platform_locations",
        "iPhone platform locations",
        "baseline",
        Path("iphone/platform-locations.csv"),
        "Apple platform location estimates",
    ),
    (
        "iphone_arkit",
        "iPhone ARKit poses",
        "baseline",
        Path("iphone/arkit.csv"),
        "On-device ARKit baseline",
    ),
    (
        "pixel_arcore",
        "Pixel ARCore poses",
        "baseline",
        Path("pixel/arcore.csv"),
        "On-device ARCore baseline",
    ),
    (
        "ground_truth",
        "Ground-truth poses",
        "reference",
        Path("ground-truth/pose.csv"),
        "Official reference trajectory",
    ),
    ("tango_frames", "Tango video timestamps", "video", Path("tango/frames.csv"), "Tango RGB frame clock"),
    (
        "tango_area_learning",
        "Tango area learning poses",
        "reference",
        Path("tango/area-learning.csv"),
        "Tango area-learning reference poses",
    ),
)
_ASSET_MODALITY_SPECS = (
    ("iphone_video", "iPhone video file", "video", Path("iphone/frames.mov"), "Input video for offline replay"),
    ("tango_video", "Tango video file", "video", Path("tango/frames.mov"), "Auxiliary Tango RGB stream"),
)

AdvioModalityFamily = Literal[
    "video",
    "imu",
    "environment",
    "baseline",
    "reference",
    "geometry",
    "calibration",
]
AdvioModalitySourceKind = Literal["timed_stream", "file_asset", "file_bundle"]


class AdvioSequenceConfig(BaseConfig):
    """Config describing one ADVIO sequence on disk."""

    dataset_root: Path = Path("data/advio")
    """Directory that stores ADVIO archives, extracted sequences, and calibration files."""

    sequence_id: int = Field(ge=1, le=ADVIO_SEQUENCE_COUNT)
    """1-based ADVIO sequence identifier."""

    @property
    def sequence_name(self) -> str:
        """Return the canonical ADVIO folder name."""
        return f"advio-{self.sequence_id:02d}"

    @property
    def archive_path(self) -> Path:
        """Return the expected ZIP archive path for this sequence."""
        return self.dataset_root / f"{self.sequence_name}.zip"

    @property
    def sequence_dir(self) -> Path:
        """Return the preferred extracted directory for this sequence."""
        for candidate in (self.dataset_root / self.sequence_name, self.dataset_root / "data" / self.sequence_name):
            if candidate.exists():
                return candidate
        return self.dataset_root / self.sequence_name

    @property
    def download_url(self) -> str:
        """Return the official Zenodo download URL for this sequence."""
        return f"{ADVIO_DOWNLOAD_BASE}/{self.sequence_name}.zip"

    @property
    def calibration_name(self) -> str:
        """Return the official calibration YAML name for this sequence."""
        for sequence_range, calibration_name in _CALIBRATION_BY_SEQUENCE.items():
            if self.sequence_id in sequence_range:
                return calibration_name
        msg = f"No calibration mapping defined for ADVIO sequence {self.sequence_id}"
        raise ValueError(msg)

    @property
    def calibration_path(self) -> Path:
        """Return the local calibration YAML path for this sequence."""
        return self.dataset_root / "calibration" / self.calibration_name

    @property
    def calibration_hint_path(self) -> Path:
        """Alias used by the repo-wide capture metadata contract."""
        return self.calibration_path

    @property
    def calibration_url(self) -> str:
        """Return the official calibration YAML URL for this sequence."""
        return f"{ADVIO_CALIBRATION_BASE}/{self.calibration_name}"

    @property
    def video_path(self) -> Path:
        """Return the expected iPhone video path for this sequence."""
        return self.sequence_dir / "iphone" / "frames.mov"

    @property
    def frame_timestamps_path(self) -> Path:
        """Return the expected iPhone frame-timestamp CSV path for this sequence."""
        return self.sequence_dir / "iphone" / "frames.csv"

    @property
    def ground_truth_path(self) -> Path:
        """Return the resolved ground-truth pose CSV path for this sequence."""
        return resolve_first_existing(self.sequence_dir / "ground-truth", _POSE_FILE_NAMES)

    @field_validator("dataset_root")
    @classmethod
    def validate_dataset_root(cls, value: Path) -> Path:
        """Reject empty dataset roots."""
        if not str(value).strip():
            msg = "dataset_root must not be blank"
            raise ValueError(msg)
        return value


class AdvioSequencePaths(BaseConfig):
    """Resolved filesystem paths for one extracted ADVIO sequence."""

    config: AdvioSequenceConfig
    """Sequence config that produced these paths."""

    sequence_dir: Path
    """Extracted sequence directory."""

    video_path: Path
    """Path to the iPhone input video."""

    frame_timestamps_path: Path
    """Path to the exact iPhone frame timestamps CSV."""

    ground_truth_path: Path
    """Path to the official ground-truth pose CSV."""

    arcore_path: Path
    """Path to the Pixel ARCore pose CSV."""

    arkit_path: Path
    """Path to the iPhone ARKit pose CSV when present."""

    calibration_path: Path
    """Path to the calibration YAML associated with this sequence."""

    @classmethod
    def resolve(cls, config: AdvioSequenceConfig) -> Self:
        """Resolve the extracted dataset paths for ``config``."""
        sequence_dir = _resolve_sequence_dir(config)
        ground_truth_dir = sequence_dir / "ground-truth"
        ground_truth_path = resolve_first_existing(ground_truth_dir, _POSE_FILE_NAMES)
        resolved = cls(
            config=config,
            sequence_dir=sequence_dir,
            video_path=sequence_dir / "iphone" / "frames.mov",
            frame_timestamps_path=sequence_dir / "iphone" / "frames.csv",
            ground_truth_path=ground_truth_path,
            arcore_path=sequence_dir / "pixel" / "arcore.csv",
            arkit_path=sequence_dir / "iphone" / "arkit.csv",
            calibration_path=config.calibration_path,
        )
        for path in (
            resolved.video_path,
            resolved.frame_timestamps_path,
            resolved.ground_truth_path,
            resolved.arcore_path,
            resolved.calibration_path,
        ):
            if not path.exists():
                msg = f"Required ADVIO path is missing: {path}"
                raise FileNotFoundError(msg)
        return resolved


class AdvioCalibration(BaseConfig):
    """Parsed camera calibration metadata for one ADVIO iPhone sequence."""

    calibration_path: Path
    """Source YAML path."""

    image_width_px: int = Field(gt=0)
    """Image width in pixels."""

    image_height_px: int = Field(gt=0)
    """Image height in pixels."""

    camera_model: str
    """Camera projection model name."""

    distortion_model: str
    """Distortion model name."""

    focal_length_px: tuple[float, float]
    """Focal lengths ``(fx, fy)`` in pixels."""

    principal_point_px: tuple[float, float]
    """Principal point ``(cx, cy)`` in pixels."""

    distortion_coefficients: tuple[float, ...]
    """Ordered distortion parameters from the calibration YAML."""

    t_cam_imu: tuple[tuple[float, float, float, float], ...]
    """Row-major ``T_cam_imu`` transform."""


class AdvioImuSample(BaseConfig):
    """Gyroscope-aligned iPhone IMU sample from ADVIO."""

    timestamp_s: float
    """Sample timestamp in seconds."""

    angular_velocity_rad_s: tuple[float, float, float]
    """Gyroscope sample in radians per second."""

    accelerometer_values: tuple[float, float, float]
    """Interpolated accelerometer sample as stored in the ADVIO CSV."""


class AdvioModalitySummary(BaseConfig):
    """Summary for one observable ADVIO modality."""

    slug: str
    """Stable identifier used by the dataset explorer."""

    label: str
    """Human-readable modality label."""

    family: AdvioModalityFamily
    """Visual family used for grouping and color coding."""

    source_kind: AdvioModalitySourceKind
    """Whether the modality is a timed CSV stream, one file asset, or a file bundle."""

    path: Path
    """Filesystem path for the modality or bundle root."""

    sample_count: int = Field(default=0, ge=0)
    """Number of samples, snapshots, or files represented by the modality."""

    start_s: float | None = None
    """First timestamp in seconds when the modality is time-indexed."""

    end_s: float | None = None
    """Last timestamp in seconds when the modality is time-indexed."""

    duration_s: float | None = None
    """Observed temporal span in seconds when available."""

    approx_rate_hz: float | None = None
    """Approximate sampling rate derived from sample count and temporal span."""

    size_bytes: int = Field(default=0, ge=0)
    """On-disk size used for inventory and footprint summaries."""

    detail: str | None = None
    """Short explanatory note used in hovers and tables."""


class AdvioSequenceSummary(BaseConfig):
    """Typed summary for one local ADVIO sequence."""

    config: AdvioSequenceConfig
    """Sequence config that produced the summary."""

    sequence_dir: Path
    """Resolved sequence directory on disk."""

    timed_modalities: list[AdvioModalitySummary] = Field(default_factory=list)
    """Timestamped CSV streams available for the sequence."""

    asset_modalities: list[AdvioModalitySummary] = Field(default_factory=list)
    """Untimed assets such as video files, calibration, and point-cloud bundles."""

    @property
    def duration_s(self) -> float | None:
        """Return the global temporal span across all timestamped modalities."""
        start_candidates = [modality.start_s for modality in self.timed_modalities if modality.start_s is not None]
        end_candidates = [modality.end_s for modality in self.timed_modalities if modality.end_s is not None]
        if not start_candidates or not end_candidates:
            return None
        return max(end_candidates) - min(start_candidates)

    @property
    def total_size_bytes(self) -> int:
        """Return the combined disk footprint across all tracked modalities."""
        return sum(modality.size_bytes for modality in (*self.timed_modalities, *self.asset_modalities))

    @property
    def timed_modality_count(self) -> int:
        """Return the number of timestamped modalities present."""
        return len(self.timed_modalities)

    @property
    def asset_modality_count(self) -> int:
        """Return the number of untimed assets present."""
        return len(self.asset_modalities)

    @property
    def point_cloud_snapshot_count(self) -> int:
        """Return the number of Tango point-cloud snapshots when present."""
        for modality in self.asset_modalities:
            if modality.slug == "tango_point_clouds":
                return modality.sample_count
        return 0


class AdvioSequence(BaseConfig):
    """High-level adapter around one local ADVIO sequence."""

    config: AdvioSequenceConfig
    """Config that identifies the sequence on disk."""

    def assert_ready(self) -> Self:
        """Raise if the required ADVIO files are not present."""
        AdvioSequencePaths.resolve(self.config)
        return self

    @property
    def paths(self) -> AdvioSequencePaths:
        """Return the resolved path bundle for this sequence."""
        return AdvioSequencePaths.resolve(self.config)

    def load_frame_timestamps_ns(self) -> list[int]:
        """Load exact iPhone frame timestamps as nanoseconds."""
        return load_advio_frame_timestamps_ns(self.paths.frame_timestamps_path)

    def load_ground_truth(self) -> list[list[float]]:
        """Load the official ground-truth pose rows as raw numeric records."""
        return _read_pose_rows(self.paths.ground_truth_path)

    def load_arcore_baseline(self) -> list[list[float]]:
        """Load the Pixel ARCore pose rows as raw numeric records."""
        return load_advio_pose_rows(self.paths.arcore_path)

    def load_arkit_baseline(self) -> list[list[float]]:
        """Load the iPhone ARKit pose rows as raw numeric records."""
        return load_advio_pose_rows(self.paths.arkit_path)

    def load_iphone_imu(self) -> list[AdvioImuSample]:
        """Load gyroscope-aligned ADVIO iPhone IMU samples."""
        sequence_dir = self.paths.sequence_dir
        return load_advio_imu_samples(
            accelerometer_path=sequence_dir / "iphone" / "accelerometer.csv",
            gyroscope_path=sequence_dir / "iphone" / "gyro.csv",
        )

    def load_calibration(self) -> AdvioCalibration:
        """Parse the official ADVIO iPhone calibration YAML."""
        return load_advio_calibration(self.paths.calibration_path)

    def build_run_request(
        self,
        *,
        experiment_name: str,
        output_dir: Path,
        method: MethodId,
        frame_stride: int,
    ) -> RunPlanRequest:
        """Build the repo-owned run request for this ADVIO sequence."""
        paths = self.paths
        return RunPlanRequest(
            experiment_name=experiment_name,
            video_path=paths.video_path,
            output_dir=output_dir,
            mode=PipelineMode.BATCH,
            method=method,
            frame_stride=frame_stride,
            enable_dense_mapping=False,
            compare_to_arcore=paths.arcore_path.exists(),
            build_ground_truth_cloud=False,
            capture=CaptureMetadataConfig(
                device_label="ADVIO iPhone",
                frame_rate_hz=60.0,
                timestamp_source=TimestampSource.CAPTURE,
                arcore_log_path=paths.arcore_path,
                calibration_hint_path=paths.calibration_path,
                notes=f"ADVIO sequence {self.config.sequence_id:02d}",
            ),
        )

    def write_ground_truth_tum(self, target_path: Path) -> Path:
        """Export the official ground truth to TUM format."""
        return convert_advio_pose_csv_to_tum(self.paths.ground_truth_path, target_path)

    def write_ground_truth_sidecar(self, target_path: Path) -> Path:
        """Persist lightweight metadata for the exported ground-truth trajectory."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset": "ADVIO",
            "sequence_id": self.config.sequence_id,
            "sequence_name": self.config.sequence_name,
            "source_csv": self.paths.ground_truth_path.as_posix(),
            "format": "tum",
            "frame_name": "world",
            "transform_convention": "T_world_camera",
            "timestamp_source": TimestampSource.CAPTURE.value,
        }
        target_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target_path


def ensure_advio_sequence_downloaded(
    config: AdvioSequenceConfig,
    *,
    overwrite_archive: bool = False,
) -> AdvioSequencePaths:
    """Download and extract an ADVIO sequence if it is not already present."""
    config.dataset_root.mkdir(parents=True, exist_ok=True)
    ensure_advio_calibration_file(config)

    try:
        return AdvioSequencePaths.resolve(config)
    except FileNotFoundError:
        pass

    if overwrite_archive or not config.archive_path.exists():
        download_file(config.download_url, config.archive_path)

    with zipfile.ZipFile(config.archive_path) as archive:
        archive.extractall(config.dataset_root)

    return AdvioSequencePaths.resolve(config)


def download_advio_sequence(
    config: AdvioSequenceConfig,
    *,
    keep_archive: bool = True,
    force: bool = False,
) -> AdvioSequence:
    """Download, extract, and return one ready-to-use ADVIO sequence."""
    if force:
        for candidate in (config.sequence_dir, config.dataset_root / "data" / config.sequence_name):
            if candidate.exists():
                shutil.rmtree(candidate)
        if config.archive_path.exists():
            config.archive_path.unlink()

    ensure_advio_sequence_downloaded(config, overwrite_archive=force)
    if not keep_archive and config.archive_path.exists():
        config.archive_path.unlink()
    return AdvioSequence(config=config).assert_ready()


def ensure_advio_calibration_file(config: AdvioSequenceConfig) -> Path:
    """Ensure the official calibration YAML is available locally."""
    target_path = config.calibration_path
    if target_path.exists():
        return target_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    download_file(config.calibration_url, target_path)
    return target_path


def list_advio_sequence_ids(dataset_root: Path) -> list[int]:
    """Return the extracted ADVIO sequence ids available under ``dataset_root``."""
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


def summarize_advio_sequence(config: AdvioSequenceConfig) -> AdvioSequenceSummary:
    """Build a modality-level summary for one local ADVIO sequence."""
    sequence_dir = _resolve_sequence_dir(config)

    timed_modalities: list[AdvioModalitySummary] = []
    for slug, label, family, relative_path, detail in _TIMED_MODALITY_SPECS:
        if relative_path == Path("ground-truth/pose.csv"):
            path = resolve_first_existing(sequence_dir / "ground-truth", _POSE_FILE_NAMES)
        else:
            path = sequence_dir / relative_path
        if not path.exists():
            continue
        timed_modalities.append(
            _summarize_timed_csv(
                slug=slug,
                label=label,
                family=family,
                path=path,
                detail=detail,
            )
        )

    asset_modalities: list[AdvioModalitySummary] = []
    for slug, label, family, relative_path, detail in _ASSET_MODALITY_SPECS:
        path = sequence_dir / relative_path
        if not path.exists():
            continue
        asset_modalities.append(
            AdvioModalitySummary(
                slug=slug,
                label=label,
                family=family,
                source_kind="file_asset",
                path=path,
                size_bytes=path.stat().st_size,
                detail=detail,
            )
        )

    point_cloud_files = sorted((sequence_dir / "tango").glob("point-cloud-*.csv"))
    if point_cloud_files:
        asset_modalities.append(
            AdvioModalitySummary(
                slug="tango_point_clouds",
                label="Tango point-cloud bundle",
                family="geometry",
                source_kind="file_bundle",
                path=sequence_dir / "tango",
                sample_count=len(point_cloud_files),
                size_bytes=sum(point_cloud_file.stat().st_size for point_cloud_file in point_cloud_files),
                detail=f"{len(point_cloud_files)} point-cloud snapshot files",
            )
        )

    calibration_path = config.calibration_path
    if calibration_path.exists():
        asset_modalities.append(
            AdvioModalitySummary(
                slug="calibration_hint",
                label="Calibration hint",
                family="calibration",
                source_kind="file_asset",
                path=calibration_path,
                size_bytes=calibration_path.stat().st_size,
                detail=f"Batch calibration YAML: {calibration_path.name}",
            )
        )

    return AdvioSequenceSummary(
        config=config,
        sequence_dir=sequence_dir,
        timed_modalities=timed_modalities,
        asset_modalities=asset_modalities,
    )


def load_advio_frame_timestamps_ns(path: Path) -> list[int]:
    """Load exact frame timestamps from ``frames.csv`` as nanoseconds."""
    return [int(round(row[0] * 1e9)) for row in read_numeric_csv(path, columns=1)]


def load_advio_pose_rows(source_path: Path) -> list[list[float]]:
    """Read one ADVIO pose CSV into raw numeric rows."""
    return read_numeric_csv(source_path, columns=8)


def load_advio_imu_samples(
    *,
    accelerometer_path: Path,
    gyroscope_path: Path,
) -> list[AdvioImuSample]:
    """Load gyroscope-aligned ADVIO IMU samples."""
    accelerometer_rows = read_numeric_csv(accelerometer_path, columns=4)
    gyroscope_rows = read_numeric_csv(gyroscope_path, columns=4)
    accelerometer_interp = interpolate_numeric_rows(
        target_timestamps_s=[row[0] for row in gyroscope_rows],
        source_timestamps_s=[row[0] for row in accelerometer_rows],
        source_values=[row[1:4] for row in accelerometer_rows],
    )
    return [
        AdvioImuSample(
            timestamp_s=gyro_row[0],
            angular_velocity_rad_s=tuple(gyro_row[1:4]),
            accelerometer_values=tuple(acc_row),
        )
        for gyro_row, acc_row in zip(gyroscope_rows, accelerometer_interp, strict=True)
    ]


def load_advio_calibration(path: Path) -> AdvioCalibration:
    """Parse an official ADVIO iPhone calibration YAML."""
    payload = load_yaml_file(path)
    camera = _extract_advio_camera_mapping(payload, calibration_path=path)
    intrinsics = _expect_advio_float_list(camera, "intrinsics", "data", expected_len=4)
    distortion = _expect_advio_mapping(camera, "distortion")
    distortion_params = _expect_advio_float_list(distortion, "parameters", "data")
    t_cam_imu = _expect_advio_matrix(camera, "T_cam_imu")
    return AdvioCalibration(
        calibration_path=path,
        image_width_px=int(camera["image_width"]),
        image_height_px=int(camera["image_height"]),
        camera_model=str(camera["type"]),
        distortion_model=str(distortion["type"]),
        focal_length_px=(intrinsics[0], intrinsics[1]),
        principal_point_px=(intrinsics[2], intrinsics[3]),
        distortion_coefficients=tuple(distortion_params),
        t_cam_imu=tuple(tuple(row) for row in t_cam_imu),
    )


def convert_advio_pose_csv_to_tum(source_path: Path, target_path: Path) -> Path:
    """Convert an ADVIO pose CSV into a TUM trajectory file."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# timestamp tx ty tz qx qy qz qw"]
    for timestamp_s, tx, ty, tz, qw, qx, qy, qz in load_advio_pose_rows(source_path):
        lines.append(f"{timestamp_s:.9f} {tx:.9f} {ty:.9f} {tz:.9f} {qx:.9f} {qy:.9f} {qz:.9f} {qw:.9f}")
    target_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target_path


def _read_pose_rows(source_path: Path) -> list[list[float]]:
    """Read an ADVIO pose CSV into raw numeric rows."""
    return load_advio_pose_rows(source_path)


def _summarize_timed_csv(
    *,
    slug: str,
    label: str,
    family: AdvioModalityFamily,
    path: Path,
    detail: str | None,
) -> AdvioModalitySummary:
    """Summarize a time-indexed ADVIO CSV stream."""
    summary = summarize_timestamped_csv(path)

    return AdvioModalitySummary(
        slug=slug,
        label=label,
        family=family,
        source_kind="timed_stream",
        path=path,
        sample_count=summary.sample_count,
        start_s=summary.start_s,
        end_s=summary.end_s,
        duration_s=summary.duration_s,
        approx_rate_hz=summary.approx_rate_hz,
        size_bytes=path.stat().st_size,
        detail=detail,
    )


def _resolve_sequence_dir(config: AdvioSequenceConfig) -> Path:
    """Resolve the extracted sequence directory, handling the common ZIP layouts."""
    candidates = [
        config.dataset_root / config.sequence_name,
        config.dataset_root / "data" / config.sequence_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    msg = f"ADVIO sequence {config.sequence_name} is not available under {config.dataset_root}"
    raise FileNotFoundError(msg)


def _extract_advio_camera_mapping(payload: dict[str, Any], *, calibration_path: Path) -> dict[str, Any]:
    """Extract the first camera mapping from an ADVIO calibration payload."""
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


def _expect_advio_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    """Return ``mapping[key]`` as a nested mapping or raise."""
    value = mapping.get(key)
    if not isinstance(value, dict):
        msg = f"Expected `{key}` to be a mapping"
        raise ValueError(msg)
    return value


def _expect_advio_float_list(
    mapping: dict[str, Any],
    key: str,
    nested_key: str,
    *,
    expected_len: int | None = None,
) -> list[float]:
    """Extract a flat float list from ``mapping[key][nested_key]``."""
    nested = _expect_advio_mapping(mapping, key)
    values = nested.get(nested_key)
    if not isinstance(values, list):
        msg = f"Expected `{key}.{nested_key}` to be a list"
        raise ValueError(msg)
    numeric_values = [float(value) for value in values]
    if expected_len is not None and len(numeric_values) != expected_len:
        msg = f"Expected `{key}.{nested_key}` to have length {expected_len}, got {len(numeric_values)}"
        raise ValueError(msg)
    return numeric_values


def _expect_advio_matrix(mapping: dict[str, Any], key: str) -> list[list[float]]:
    """Extract a 4x4 float matrix from ``mapping[key].data``."""
    rows = _expect_advio_mapping(mapping, key).get("data")
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
