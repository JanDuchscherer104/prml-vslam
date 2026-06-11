"""Normalized dataset long-table schema, builders, and CSV codecs."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import TypeAlias

import cv2
import numpy as np

from prml_vslam.interfaces import ObservationSequenceIndex
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.utils import BaseData, JsonObject
from prml_vslam.utils.geometry import load_tum_trajectory

StatValue: TypeAlias = bool | int | float | str | None


class NormalizedDatasetLongRow(BaseData):
    """One tidy row emitted by normalized dataset query surfaces."""

    dataset_id: str
    sequence_id: str
    profile_key: str
    artifact_kind: str
    stat_name: str
    value: StatValue = None
    unit: str | None = None
    modality: str | None = None
    source_kind: str | None = None
    artifact_path: Path | None = None


NORMALIZED_LONG_ROW_COLUMNS = tuple(NormalizedDatasetLongRow.model_fields)


def statistics_rows(
    *,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    rows: list[NormalizedDatasetLongRow] = []
    timestamps_ns = load_timestamps_ns(sequence_manifest.timestamps_path) if sequence_manifest.timestamps_path else []
    frame_count = len(timestamps_ns)
    duration_s = _duration_s(timestamps_ns)
    rows.extend(
        [
            _row(sequence_manifest, profile_key, "timing", "frame_count", frame_count, unit="frames", modality="rgb"),
            _row(sequence_manifest, profile_key, "timing", "duration_s", duration_s, unit="s"),
            _row(sequence_manifest, profile_key, "timing", "effective_fps", _fps(frame_count, duration_s), unit="Hz"),
            _row(
                sequence_manifest, profile_key, "timing", "timestamp_monotonic", _is_strictly_monotonic(timestamps_ns)
            ),
            _row(
                sequence_manifest,
                profile_key,
                "rgb",
                "available",
                sequence_manifest.rgb_dir is not None,
                modality="rgb",
                artifact_path=sequence_manifest.rgb_dir,
            ),
            _row(
                sequence_manifest,
                profile_key,
                "intrinsics",
                "available",
                sequence_manifest.intrinsics_path is not None,
                artifact_path=sequence_manifest.intrinsics_path,
            ),
            _row(
                sequence_manifest,
                profile_key,
                "trajectory",
                "reference_count",
                len(benchmark_inputs.reference_trajectories),
            ),
            _row(sequence_manifest, profile_key, "cloud", "reference_count", len(benchmark_inputs.reference_clouds)),
            _row(
                sequence_manifest,
                profile_key,
                "observation_sequence",
                "reference_count",
                len(benchmark_inputs.observation_sequences),
            ),
        ]
    )
    rows.extend(_storage_rows(sequence_manifest, benchmark_inputs, profile_key))
    rows.extend(_observation_rows(sequence_manifest, benchmark_inputs, profile_key))
    rows.extend(_trajectory_rows(sequence_manifest, benchmark_inputs, profile_key))
    rows.extend(_reference_rows(sequence_manifest, benchmark_inputs, profile_key))
    return rows


def metadata_rows(
    *,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    rows = [
        _row(
            sequence_manifest,
            profile_key,
            "identity",
            "dataset_id",
            sequence_manifest.dataset_id.value if sequence_manifest.dataset_id else None,
        ),
        _row(sequence_manifest, profile_key, "identity", "sequence_id", sequence_manifest.sequence_id),
    ]
    if sequence_manifest.advio is not None:
        rows.extend(
            [
                _row(
                    sequence_manifest,
                    profile_key,
                    "calibration",
                    "intrinsics_model",
                    "pinhole",
                    artifact_path=sequence_manifest.advio.calibration_path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "calibration",
                    "T_cam_imu_target_frame",
                    sequence_manifest.advio.T_cam_imu.target_frame,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "calibration",
                    "T_cam_imu_source_frame",
                    sequence_manifest.advio.T_cam_imu.source_frame,
                ),
            ]
        )
    for trajectory_ref in benchmark_inputs.reference_trajectories:
        rows.extend(
            [
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "target_frame",
                    trajectory_ref.target_frame,
                    source_kind=trajectory_ref.source.value,
                    artifact_path=trajectory_ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "coordinate_status",
                    None if trajectory_ref.coordinate_status is None else trajectory_ref.coordinate_status.value,
                    source_kind=trajectory_ref.source.value,
                    artifact_path=trajectory_ref.path,
                ),
            ]
        )
    for cloud_ref in benchmark_inputs.reference_clouds:
        rows.extend(
            [
                _row(
                    sequence_manifest,
                    profile_key,
                    "cloud",
                    "target_frame",
                    cloud_ref.target_frame,
                    source_kind=cloud_ref.source.value,
                    artifact_path=cloud_ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "cloud",
                    "coordinate_status",
                    cloud_ref.coordinate_status.value,
                    source_kind=cloud_ref.source.value,
                    artifact_path=cloud_ref.path,
                ),
            ]
        )
    return rows


def _storage_rows(
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    paths = [
        ("rgb", sequence_manifest.rgb_dir),
        ("timestamps", sequence_manifest.timestamps_path),
        ("intrinsics", sequence_manifest.intrinsics_path),
        ("rotation_metadata", sequence_manifest.rotation_metadata_path),
    ]
    paths.extend(("trajectory", ref.path) for ref in benchmark_inputs.reference_trajectories)
    paths.extend(("cloud", ref.path) for ref in benchmark_inputs.reference_clouds)
    paths.extend(("observation_sequence", ref.index_path) for ref in benchmark_inputs.observation_sequences)
    return [
        _row(
            sequence_manifest,
            profile_key,
            artifact_kind,
            "storage_bytes",
            _path_size_bytes(path),
            unit="bytes",
            artifact_path=path,
        )
        for artifact_kind, path in paths
        if path is not None
    ]


def _observation_rows(
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    rows: list[NormalizedDatasetLongRow] = []
    for ref in benchmark_inputs.observation_sequences:
        index = load_observation_sequence_index(ref.index_path)
        rows.append(
            _row(
                sequence_manifest,
                profile_key,
                "observation_sequence",
                "observation_count",
                index.observation_count,
                unit="observations",
                source_kind=ref.source_id,
                artifact_path=ref.index_path,
            )
        )
        rows.append(
            _row(
                sequence_manifest,
                profile_key,
                "depth",
                "available",
                any(row.depth_path is not None for row in index.rows),
                modality="depth",
                source_kind=ref.source_id,
            )
        )
        first_intrinsics = next((row.intrinsics for row in index.rows if row.intrinsics is not None), None)
        if first_intrinsics is not None:
            rows.extend(
                [
                    _row(
                        sequence_manifest,
                        profile_key,
                        "camera",
                        "width_px",
                        first_intrinsics.width_px,
                        unit="px",
                        source_kind=ref.source_id,
                    ),
                    _row(
                        sequence_manifest,
                        profile_key,
                        "camera",
                        "height_px",
                        first_intrinsics.height_px,
                        unit="px",
                        source_kind=ref.source_id,
                    ),
                    _row(
                        sequence_manifest,
                        profile_key,
                        "camera",
                        "intrinsics_available",
                        True,
                        source_kind=ref.source_id,
                    ),
                ]
            )
        rows.extend(_depth_rows(sequence_manifest, profile_key, ref.payload_root, index, source_kind=ref.source_id))
    return rows


def _depth_rows(
    sequence_manifest: SequenceManifest,
    profile_key: str,
    payload_root: Path,
    index: ObservationSequenceIndex,
    *,
    source_kind: str,
) -> list[NormalizedDatasetLongRow]:
    valid_pixels = 0
    zero_pixels = 0
    total_pixels = 0
    min_depth = math.inf
    max_depth = -math.inf
    depth_frames = 0
    for row in index.rows:
        if row.depth_path is None:
            continue
        depth_path = row.depth_path if row.depth_path.is_absolute() else payload_root / row.depth_path
        depth = load_depth_array(depth_path) * float(row.depth_scale_to_m)
        finite = np.isfinite(depth)
        valid = finite & (depth > 0.0)
        zeros = finite & (depth == 0.0)
        depth_frames += 1
        valid_pixels += int(np.count_nonzero(valid))
        zero_pixels += int(np.count_nonzero(zeros))
        total_pixels += int(depth.size)
        if np.any(valid):
            min_depth = min(min_depth, float(np.min(depth[valid])))
            max_depth = max(max_depth, float(np.max(depth[valid])))
    if total_pixels == 0:
        return []
    return [
        _row(
            sequence_manifest,
            profile_key,
            "depth",
            "frame_count",
            depth_frames,
            unit="frames",
            modality="depth",
            source_kind=source_kind,
        ),
        _row(
            sequence_manifest,
            profile_key,
            "depth",
            "valid_ratio",
            valid_pixels / total_pixels,
            modality="depth",
            source_kind=source_kind,
        ),
        _row(
            sequence_manifest,
            profile_key,
            "depth",
            "zero_ratio",
            zero_pixels / total_pixels,
            modality="depth",
            source_kind=source_kind,
        ),
        _row(
            sequence_manifest,
            profile_key,
            "depth",
            "min_valid_depth_m",
            None if min_depth == math.inf else min_depth,
            unit="m",
            modality="depth",
            source_kind=source_kind,
        ),
        _row(
            sequence_manifest,
            profile_key,
            "depth",
            "max_valid_depth_m",
            None if max_depth == -math.inf else max_depth,
            unit="m",
            modality="depth",
            source_kind=source_kind,
        ),
    ]


def load_depth_array(path: Path) -> np.ndarray:
    if path.suffix == ".npy":
        return np.asarray(np.load(path), dtype=np.float32)
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Cannot read normalized depth image: {path}")
    return np.asarray(image, dtype=np.float32)


def _trajectory_rows(
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    rows: list[NormalizedDatasetLongRow] = []
    for ref in benchmark_inputs.reference_trajectories:
        trajectory = load_tum_trajectory(ref.path)
        positions = np.asarray(trajectory.positions_xyz, dtype=np.float64)
        timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
        distances = (
            np.linalg.norm(np.diff(positions, axis=0), axis=1)
            if len(positions) > 1
            else np.asarray([], dtype=np.float64)
        )
        duration_s = float(timestamps[-1] - timestamps[0]) if len(timestamps) > 1 else 0.0
        speeds = (
            distances / np.maximum(np.diff(timestamps), 1e-12) if len(distances) else np.asarray([], dtype=np.float64)
        )
        rows.extend(
            [
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "pose_count",
                    len(positions),
                    unit="poses",
                    source_kind=ref.source.value,
                    artifact_path=ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "path_length_m",
                    float(np.sum(distances)),
                    unit="m",
                    source_kind=ref.source.value,
                    artifact_path=ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "duration_s",
                    duration_s,
                    unit="s",
                    source_kind=ref.source.value,
                    artifact_path=ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "mean_speed_mps",
                    float(np.mean(speeds)) if speeds.size else 0.0,
                    unit="m/s",
                    source_kind=ref.source.value,
                    artifact_path=ref.path,
                ),
                _row(
                    sequence_manifest,
                    profile_key,
                    "trajectory",
                    "max_speed_mps",
                    float(np.max(speeds)) if speeds.size else 0.0,
                    unit="m/s",
                    source_kind=ref.source.value,
                    artifact_path=ref.path,
                ),
            ]
        )
    return rows


def _reference_rows(
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    profile_key: str,
) -> list[NormalizedDatasetLongRow]:
    rows: list[NormalizedDatasetLongRow] = []
    for trajectory_ref in benchmark_inputs.reference_trajectories:
        rows.append(
            _row(
                sequence_manifest,
                profile_key,
                "trajectory",
                "exists",
                trajectory_ref.path.exists(),
                source_kind=trajectory_ref.source.value,
                artifact_path=trajectory_ref.path,
            )
        )
    for cloud_ref in benchmark_inputs.reference_clouds:
        rows.append(
            _row(
                sequence_manifest,
                profile_key,
                "cloud",
                "exists",
                cloud_ref.path.exists() and cloud_ref.metadata_path.exists(),
                source_kind=cloud_ref.source.value,
                artifact_path=cloud_ref.path,
            )
        )
    return rows


def _row(
    sequence_manifest: SequenceManifest,
    profile_key: str,
    artifact_kind: str,
    stat_name: str,
    value: StatValue,
    *,
    unit: str | None = None,
    modality: str | None = None,
    source_kind: str | None = None,
    artifact_path: Path | None = None,
) -> NormalizedDatasetLongRow:
    if sequence_manifest.dataset_id is None:
        raise ValueError(f"Normalized dataset rows require dataset_id for sequence '{sequence_manifest.sequence_id}'.")
    return NormalizedDatasetLongRow(
        dataset_id=sequence_manifest.dataset_id.value,
        sequence_id=sequence_manifest.sequence_id,
        profile_key=profile_key,
        artifact_kind=artifact_kind,
        stat_name=stat_name,
        value=value,
        unit=unit,
        modality=modality,
        source_kind=source_kind,
        artifact_path=artifact_path,
    )


def write_long_csv(path: Path, rows: list[NormalizedDatasetLongRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(NormalizedDatasetLongRow.model_fields))
        writer.writeheader()
        for row in rows:
            writer.writerow(row.model_dump(mode="json"))


def _duration_s(timestamps_ns: list[int]) -> float:
    return 0.0 if len(timestamps_ns) < 2 else max((timestamps_ns[-1] - timestamps_ns[0]) / 1e9, 0.0)


def _fps(frame_count: int, duration_s: float) -> float:
    return 0.0 if duration_s <= 0.0 else max(frame_count - 1, 0) / duration_s


def _is_strictly_monotonic(values: list[int]) -> bool:
    return all(left < right for left, right in zip(values, values[1:], strict=False))


def _path_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(child.stat().st_size for child in path.rglob("*") if child.is_file())
    return 0


def read_long_csv(path: Path) -> list[JsonObject]:
    """Read one normalized long-table CSV as JSON-compatible rows."""
    with path.open(newline="", encoding="utf-8") as stream:
        return [dict(row) for row in csv.DictReader(stream)]


def load_timestamps_ns(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("timestamps_ns"), list):
        return [int(value) for value in payload["timestamps_ns"]]
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_field = stripped.split(",", maxsplit=1)[0].strip() if "," in stripped else stripped.split()[0]
            rows.append(int(round(float(first_field) * 1e9)))
    return rows
