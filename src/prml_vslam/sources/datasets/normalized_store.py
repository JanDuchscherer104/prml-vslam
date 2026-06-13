"""Persistent normalized dataset entries for offline dataset-backed sources."""

from __future__ import annotations

import json
import os
import shutil
import time
from collections.abc import Callable, Iterable
from csv import DictReader, DictWriter
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
from pydantic import BaseModel, Field

from prml_vslam.interfaces import ObservationSequenceIndex, ObservationSequenceRef, write_camera_intrinsics_yaml
from prml_vslam.sources.contracts import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.protocols import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.sources.replay import ImageSequenceObservationSource, ObservationStream, ReplayMode
from prml_vslam.utils import BaseData, JsonObject, JsonValue, PathConfig
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.utils.serialization import stable_hash, write_json
from prml_vslam.utils.video_frames import extract_video_frames

ENTRY_FILENAME = "entry.json"
SEQUENCE_MANIFEST_FILENAME = "sequence_manifest.json"
BENCHMARK_INPUTS_FILENAME = "benchmark_inputs.json"
STATS_LONG_FILENAME = "stats_long.csv"
METADATA_LONG_FILENAME = "metadata_long.csv"
STATS_LONG_HEADER = (
    "dataset_id",
    "sequence_id",
    "profile_key",
    "source_id",
    "scope",
    "subject",
    "stat",
    "value",
    "unit",
)
METADATA_LONG_HEADER = ("dataset_id", "sequence_id", "profile_key", "source_id", "scope", "key", "value")
STORE_SCHEMA_VERSION = 4


class NormalizedDatasetProfile(BaseData):
    """Canonical byte-affecting profile used to key one normalized entry."""

    schema_version: int = STORE_SCHEMA_VERSION
    dataset_id: DatasetId
    sequence_id: str
    source_id: str
    source_profile: dict[str, Any]

    @property
    def profile_key(self) -> str:
        """Return the deterministic store key for this profile."""
        return stable_hash(self.model_dump(mode="json"))[:24]


class NormalizedDatasetStoreIssue(BaseData):
    """Read-only diagnostic for a normalized-store entry that is not currently usable."""

    dataset_id: DatasetId
    sequence_id: str
    profile_key: str
    entry_path: Path
    status: str
    message: str
    entry_schema_version: int | None = None
    profile_schema_version: int | None = None


class NormalizedDatasetEntry(BaseData):
    """Metadata for one complete normalized dataset entry."""

    schema_version: int = STORE_SCHEMA_VERSION
    dataset_id: DatasetId
    sequence_id: str
    source_id: str
    profile_key: str
    profile: dict[str, Any]
    root: Path
    sequence_manifest_path: Path
    benchmark_inputs_path: Path
    stats_long_path: Path | None = None
    metadata_long_path: Path | None = None
    created_at_ns: int = Field(default_factory=time.time_ns)


class NormalizedDatasetStore:
    """Filesystem store for reusable full-frame normalized dataset payloads."""

    def __init__(self, *, store_root: Path, dataset_id: DatasetId) -> None:
        self.dataset_id = dataset_id
        self.store_root = store_root.resolve()

    @property
    def preview_root(self) -> Path:
        """Return the run-local preview scratch root for normalized entries."""
        return self.store_root / ".preview"

    def entry_root(self, profile: NormalizedDatasetProfile) -> Path:
        """Return the root directory for one profile."""
        return self.store_root / profile.sequence_id / profile.profile_key

    def load_entry(self, profile: NormalizedDatasetProfile) -> NormalizedDatasetEntry:
        """Load one complete normalized entry."""
        entry_path = self.entry_root(profile) / ENTRY_FILENAME
        if not entry_path.exists():
            raise FileNotFoundError(self.missing_entry_message(profile))
        entry = NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
        self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
        self._validate_entry_payloads(entry)
        return entry

    def entry_exists(self, profile: NormalizedDatasetProfile) -> bool:
        """Return whether one complete normalized entry exists."""
        try:
            self.load_entry(profile)
        except FileNotFoundError:
            return False
        return True

    def missing_entry_message(self, profile: NormalizedDatasetProfile) -> str:
        """Return an actionable missing-entry diagnostic."""
        return (
            "Missing normalized dataset entry "
            f"dataset_id={profile.dataset_id.value} sequence_id={profile.sequence_id} "
            f"profile_key={profile.profile_key}. Run: prml-vslam dataset normalize "
            f"--dataset {profile.dataset_id.value} --sequence {profile.sequence_id}"
        )

    def create_entry(
        self,
        *,
        profile: NormalizedDatasetProfile,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs,
    ) -> NormalizedDatasetEntry:
        """Persist one full-frame normalized entry."""
        return self._create_and_publish_entry(
            profile,
            lambda temp_root: self._create_entry_at_root(
                profile=profile,
                sequence_manifest=sequence_manifest,
                benchmark_inputs=benchmark_inputs,
                root=temp_root,
            ),
        )

    def _create_entry_at_root(
        self,
        *,
        profile: NormalizedDatasetProfile,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs,
        root: Path,
    ) -> NormalizedDatasetEntry:
        root.mkdir(parents=True, exist_ok=True)
        benchmark_inputs = self._normalize_benchmark_inputs(benchmark_inputs, root=root)
        sequence_manifest = self._normalize_sequence_manifest(
            sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            input_root=root / "input",
        )
        sequence_manifest_path = root / SEQUENCE_MANIFEST_FILENAME
        benchmark_inputs_path = root / BENCHMARK_INPUTS_FILENAME
        write_json(sequence_manifest_path, sequence_manifest)
        write_json(benchmark_inputs_path, benchmark_inputs)
        stats_long_path, metadata_long_path = _write_entry_analysis_tables(
            root=root,
            profile=profile,
            sequence_manifest=sequence_manifest,
            benchmark_inputs=benchmark_inputs,
        )
        entry = NormalizedDatasetEntry(
            dataset_id=self.dataset_id,
            sequence_id=profile.sequence_id,
            source_id=profile.source_id,
            profile_key=profile.profile_key,
            profile=profile.model_dump(mode="json"),
            root=root,
            sequence_manifest_path=sequence_manifest_path,
            benchmark_inputs_path=benchmark_inputs_path,
            stats_long_path=stats_long_path,
            metadata_long_path=metadata_long_path,
        )
        write_json(root / ENTRY_FILENAME, entry)
        return entry

    def create_entry_from_source(
        self,
        *,
        profile: NormalizedDatasetProfile,
        source: NormalizableDatasetSource,
    ) -> NormalizedDatasetEntry:
        """Prepare and persist one full-frame entry from a dataset source."""
        return self._create_and_publish_entry(
            profile,
            lambda temp_root: self._create_entry_at_root(
                profile=profile,
                sequence_manifest=source.prepare_sequence_manifest(temp_root / "input"),
                benchmark_inputs=source.prepare_benchmark_inputs(temp_root / "benchmark"),
                root=temp_root,
            ),
        )

    def _create_and_publish_entry(
        self,
        profile: NormalizedDatasetProfile,
        build: Callable[[Path], NormalizedDatasetEntry],
    ) -> NormalizedDatasetEntry:
        root = self.entry_root(profile).resolve()
        temp_root = _temporary_entry_root(root)
        if temp_root.exists():
            shutil.rmtree(temp_root)
        try:
            entry = build(temp_root)
            self._validate_entry(entry=entry, profile=profile, entry_path=temp_root / ENTRY_FILENAME)
            self._validate_entry_payloads(entry)
            _rebase_entry_metadata_paths(temp_root, old_root=temp_root, new_root=root)
            _publish_entry_root(temp_root=temp_root, final_root=root)
            return self.load_entry(profile)
        finally:
            _cleanup_temporary_entry_root(temp_root)

    def read_sequence_manifest(
        self,
        entry: NormalizedDatasetEntry,
        *,
        frame_selection: FrameSelectionConfig,
        output_dir: Path,
    ) -> SequenceManifest:
        """Load the stored manifest and apply run-local frame selection by index."""
        manifest = SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8"))
        if manifest.timestamps_path is None:
            return manifest
        timestamps_ns = load_timestamps_ns(manifest.timestamps_path)
        selected_indices = _selected_indices(timestamps_ns, frame_selection)
        output_dir.mkdir(parents=True, exist_ok=True)
        selected_timestamps_path = output_dir / "timestamps.json"
        selected_indices_path = output_dir / "source_frame_indices.json"
        write_json(selected_timestamps_path, {"timestamps_ns": [timestamps_ns[index] for index in selected_indices]})
        write_json(selected_indices_path, {"source_frame_indices": selected_indices})
        return manifest.model_copy(
            update={
                "timestamps_path": selected_timestamps_path.resolve(),
                "source_frame_indices_path": selected_indices_path.resolve(),
            }
        )

    def read_benchmark_inputs(
        self,
        entry: NormalizedDatasetEntry,
        *,
        frame_selection: FrameSelectionConfig,
        output_dir: Path,
    ) -> PreparedBenchmarkInputs:
        """Load benchmark inputs and apply run-local observation selection."""
        benchmark_inputs = PreparedBenchmarkInputs.model_validate_json(
            entry.benchmark_inputs_path.read_text(encoding="utf-8")
        )
        refs = [
            _select_observation_sequence(ref, frame_selection=frame_selection, output_dir=output_dir)
            for ref in benchmark_inputs.observation_sequences
        ]
        return benchmark_inputs.model_copy(update={"observation_sequences": refs})

    def open_stream(
        self,
        entry: NormalizedDatasetEntry,
        *,
        frame_selection: FrameSelectionConfig,
        output_dir: Path,
        loop: bool,
        replay_mode: ReplayMode,
        include_depth: bool = True,
    ) -> ObservationStream:
        """Open a replay stream backed by stored observation payloads."""
        benchmark_inputs = self.read_benchmark_inputs(
            entry,
            frame_selection=frame_selection,
            output_dir=output_dir,
        )
        sequence_ref = benchmark_inputs.default_observation_sequence()
        if sequence_ref is None:
            raise RuntimeError("The normalized dataset entry does not include a replayable observation sequence.")
        index = load_observation_sequence_index(sequence_ref.index_path)
        return ImageSequenceObservationSource(
            sequence_dir=sequence_ref.payload_root,
            rows=index.rows,
            loop=loop,
            replay_mode=replay_mode,
            include_depth=include_depth,
            depth_loader=load_depth_array,
        )

    def summary(self, *, strict: bool = True) -> list[NormalizedDatasetEntry]:
        """Return entries discovered from authoritative JSON files."""
        return list(self._scan_entries(strict=strict))

    def issues(self) -> list[NormalizedDatasetStoreIssue]:
        """Return normalized entries that need rebuild or operator attention."""
        if not self.store_root.exists():
            return []
        issues: list[NormalizedDatasetStoreIssue] = []
        for entry_path in sorted(self.store_root.glob(f"*/*/{ENTRY_FILENAME}")):
            try:
                entry = NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
                profile = NormalizedDatasetProfile.model_validate(entry.profile)
                if _is_stale_schema(entry, profile):
                    issues.append(
                        _stale_schema_issue(
                            dataset_id=self.dataset_id, entry=entry, profile=profile, entry_path=entry_path
                        )
                    )
                    continue
                self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
                self._validate_entry_payloads(entry)
            except Exception as exc:
                issues.append(_invalid_entry_issue(dataset_id=self.dataset_id, entry_path=entry_path, exc=exc))
        return issues

    def _scan_entries(self, *, strict: bool) -> Iterable[NormalizedDatasetEntry]:
        if not self.store_root.exists():
            return []
        entries: list[NormalizedDatasetEntry] = []
        for entry_path in sorted(self.store_root.glob(f"*/*/{ENTRY_FILENAME}")):
            try:
                entry = NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8"))
                profile = NormalizedDatasetProfile.model_validate(entry.profile)
                if _is_stale_schema(entry, profile):
                    continue
                self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
                self._validate_entry_payloads(entry)
            except Exception:
                if strict:
                    raise
                continue
            entries.append(entry)
        return entries

    def _validate_entry(
        self,
        *,
        entry: NormalizedDatasetEntry,
        profile: NormalizedDatasetProfile,
        entry_path: Path,
    ) -> None:
        expected_root = entry_path.parent.resolve()
        if entry.root.resolve() != expected_root:
            raise RuntimeError(
                f"Normalized entry root '{entry.root}' does not match entry file parent '{expected_root}'."
            )
        _ensure_under(self.store_root, entry.root)
        if entry.dataset_id is not self.dataset_id or profile.dataset_id is not self.dataset_id:
            raise RuntimeError(
                f"Normalized entry dataset_id does not belong to store '{self.dataset_id.value}': "
                f"entry={entry.dataset_id.value}, profile={profile.dataset_id.value}."
            )
        if entry.schema_version != STORE_SCHEMA_VERSION or profile.schema_version != STORE_SCHEMA_VERSION:
            raise RuntimeError(
                "Normalized entry schema_version does not match the current store schema: "
                f"entry={entry.schema_version}, profile={profile.schema_version}, expected={STORE_SCHEMA_VERSION}."
            )
        _validate_entry_paths(entry)
        if entry.root.parent.name != profile.sequence_id or entry.root.name != profile.profile_key:
            raise RuntimeError(
                "Normalized entry path does not match profile identity: "
                f"path_sequence={entry.root.parent.name}, path_profile={entry.root.name}, "
                f"profile_sequence={profile.sequence_id}, profile_key={profile.profile_key}."
            )
        mismatches = {
            field: (actual, expected)
            for field, actual, expected in (
                ("dataset_id", entry.dataset_id, profile.dataset_id),
                ("sequence_id", entry.sequence_id, profile.sequence_id),
                ("source_id", entry.source_id, profile.source_id),
                ("profile_key", entry.profile_key, profile.profile_key),
                ("profile", entry.profile, profile.model_dump(mode="json")),
            )
            if actual != expected
        }
        if mismatches:
            raise RuntimeError(f"Normalized entry metadata does not match requested profile: {mismatches}")

    def _validate_entry_payloads(self, entry: NormalizedDatasetEntry) -> None:
        manifest = SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8"))
        _validate_manifest_paths(entry.root, manifest)
        benchmark_inputs = PreparedBenchmarkInputs.model_validate_json(
            entry.benchmark_inputs_path.read_text(encoding="utf-8")
        )
        _validate_benchmark_input_paths(entry.root, benchmark_inputs)
        _validate_entry_analysis_tables(entry)

    def _normalize_sequence_manifest(
        self,
        manifest: SequenceManifest,
        *,
        benchmark_inputs: PreparedBenchmarkInputs,
        input_root: Path,
    ) -> SequenceManifest:
        updates: dict[str, Path | None] = {"source_frame_indices_path": None}
        if manifest.video_path is not None:
            extracted = extract_video_frames(video_path=manifest.video_path, output_dir=input_root / "rgb")
            updates["video_path"] = None
            updates["rgb_dir"] = extracted.rgb_dir
            timestamps_path = input_root / "timestamps.json"
            timestamps_ns = (
                load_timestamps_ns(manifest.timestamps_path)
                if manifest.timestamps_path is not None
                else extracted.timestamps_ns
            )
            if len(timestamps_ns) != len(extracted.timestamps_ns):
                raise RuntimeError(
                    "SequenceManifest video timestamps do not match extracted RGB frame count: "
                    f"{len(timestamps_ns)} timestamps in '{manifest.timestamps_path}' for "
                    f"{len(extracted.timestamps_ns)} extracted frame(s) from '{manifest.video_path}'."
                )
            write_json(timestamps_path, {"timestamps_ns": timestamps_ns})
            updates["timestamps_path"] = timestamps_path
        elif manifest.rgb_dir is not None:
            updates["rgb_dir"] = _copy_path(manifest.rgb_dir, input_root / "rgb")
        if manifest.timestamps_path is not None and "timestamps_path" not in updates:
            updates["timestamps_path"] = _copy_path(
                manifest.timestamps_path, input_root / manifest.timestamps_path.name
            )
        if manifest.intrinsics_path is not None:
            updates["intrinsics_path"] = _copy_path(
                manifest.intrinsics_path, input_root / manifest.intrinsics_path.name
            )
        if manifest.rotation_metadata_path is not None:
            updates["rotation_metadata_path"] = _copy_path(
                manifest.rotation_metadata_path, input_root / manifest.rotation_metadata_path.name
            )
        manifest = manifest.model_copy(update=updates)
        if manifest.advio is not None:
            manifest = manifest.model_copy(
                update={"advio": _normalize_advio_assets(manifest.advio, input_root=input_root)}
            )
        return _dedupe_manifest_rgb(manifest, benchmark_inputs, input_root=input_root)

    def _normalize_benchmark_inputs(
        self,
        benchmark_inputs: PreparedBenchmarkInputs,
        *,
        root: Path,
    ) -> PreparedBenchmarkInputs:
        observation_sequences = []
        for index, ref in enumerate(benchmark_inputs.observation_sequences):
            target_root = _normalized_observation_sequence_root(
                root=root,
                sequence_count=len(benchmark_inputs.observation_sequences),
                index=index,
            )
            normalized_ref = _normalize_observation_sequence_ref(ref, target_root=target_root)
            _remove_staged_observation_sequence(
                source_root=ref.payload_root,
                normalized_root=normalized_ref.payload_root,
                entry_root=root,
            )
            observation_sequences.append(normalized_ref)
        return benchmark_inputs.model_copy(update={"observation_sequences": observation_sequences})


def normalized_dataset_profile(
    *,
    dataset_id: DatasetId,
    sequence_id: str,
    source_id: str,
    payload: JsonObject,
) -> NormalizedDatasetProfile:
    """Build a profile from source settings that change stored bytes."""
    profile: dict[str, JsonValue] = dict(payload)
    profile["sequence_id"] = sequence_id
    return NormalizedDatasetProfile(
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        source_id=source_id,
        source_profile=profile,
    )


def normalized_store_for_path_config(dataset_id: DatasetId, path_config: PathConfig) -> NormalizedDatasetStore:
    """Build the normalized store for one dataset under the shared datastore root."""
    return NormalizedDatasetStore(
        store_root=path_config.resolve_normalized_datastore_dir(dataset_id.value),
        dataset_id=dataset_id,
    )


def _validate_entry_paths(entry: NormalizedDatasetEntry) -> None:
    _ensure_under(entry.root, entry.sequence_manifest_path)
    _ensure_under(entry.root, entry.benchmark_inputs_path)
    _ensure_optional_existing_under(entry.root, entry.stats_long_path)
    _ensure_optional_existing_under(entry.root, entry.metadata_long_path)


def normalized_entry_analysis_summary(entry: NormalizedDatasetEntry) -> JsonObject:
    """Return compact row-count metadata for one entry's analysis tables."""
    return {
        "stats_long_path": None if entry.stats_long_path is None else entry.stats_long_path.as_posix(),
        "stats_long_row_count": _csv_row_count(entry.stats_long_path, STATS_LONG_HEADER),
        "metadata_long_path": None if entry.metadata_long_path is None else entry.metadata_long_path.as_posix(),
        "metadata_long_row_count": _csv_row_count(entry.metadata_long_path, METADATA_LONG_HEADER),
    }


def load_normalized_entry_stats(entry: NormalizedDatasetEntry) -> list[JsonObject]:
    """Load persisted long-form statistics rows for one normalized entry."""
    return _read_analysis_csv(entry.stats_long_path, STATS_LONG_HEADER)


def load_normalized_entry_metadata(entry: NormalizedDatasetEntry) -> list[JsonObject]:
    """Load persisted long-form metadata rows for one normalized entry."""
    return _read_analysis_csv(entry.metadata_long_path, METADATA_LONG_HEADER)


def _validate_entry_analysis_tables(entry: NormalizedDatasetEntry) -> None:
    if entry.stats_long_path is not None:
        _read_analysis_csv(entry.stats_long_path, STATS_LONG_HEADER)
    if entry.metadata_long_path is not None:
        _read_analysis_csv(entry.metadata_long_path, METADATA_LONG_HEADER)


def _csv_row_count(path: Path | None, header: tuple[str, ...]) -> int:
    if path is None:
        return 0
    return len(_read_analysis_csv(path, header))


def _read_analysis_csv(path: Path | None, header: tuple[str, ...]) -> list[JsonObject]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = DictReader(handle)
        if tuple(reader.fieldnames or ()) != header:
            raise RuntimeError(f"Normalized analysis table '{path}' has invalid CSV header {reader.fieldnames}.")
        return [dict(row) for row in reader]


def _write_entry_analysis_tables(
    *,
    root: Path,
    profile: NormalizedDatasetProfile,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
) -> tuple[Path, Path]:
    stats_path = root / STATS_LONG_FILENAME
    metadata_path = root / METADATA_LONG_FILENAME
    _write_csv(stats_path, STATS_LONG_HEADER, _entry_stats_rows(profile, sequence_manifest, benchmark_inputs))
    _write_csv(metadata_path, METADATA_LONG_HEADER, _entry_metadata_rows(profile, sequence_manifest, benchmark_inputs))
    return stats_path.resolve(), metadata_path.resolve()


def _write_csv(path: Path, header: tuple[str, ...], rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _entry_stats_rows(
    profile: NormalizedDatasetProfile,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
) -> list[JsonObject]:
    rows: list[JsonObject] = []
    timestamps_ns = _manifest_timestamps_ns(sequence_manifest)
    frame_count = _manifest_frame_count(sequence_manifest, timestamps_ns)
    duration_s = _duration_s_from_ns(timestamps_ns)
    rows.extend(
        _stats_rows(
            profile,
            scope="sequence",
            subject=profile.sequence_id,
            values={
                "manifest_frame_count": (frame_count, "count"),
                "manifest_duration_s": (duration_s, "s"),
                "manifest_mean_fps": (_mean_fps(frame_count, duration_s), "Hz"),
            },
        )
    )
    for ref in benchmark_inputs.observation_sequences:
        rows.extend(_observation_sequence_stats_rows(profile, ref))
    for scope, trajectories in (
        ("reference_trajectory", benchmark_inputs.reference_trajectories),
        ("candidate_trajectory", benchmark_inputs.candidate_trajectories),
    ):
        for trajectory_ref in trajectories:
            rows.extend(_trajectory_stats_rows(profile, scope=scope, trajectory_ref=trajectory_ref))
    return rows


def _entry_metadata_rows(
    profile: NormalizedDatasetProfile,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
) -> list[JsonObject]:
    rows = [
        _metadata_row(profile, scope="entry", key="schema_version", value=str(STORE_SCHEMA_VERSION)),
        _metadata_row(profile, scope="entry", key="dataset_id", value=profile.dataset_id.value),
        _metadata_row(profile, scope="entry", key="sequence_id", value=profile.sequence_id),
        _metadata_row(profile, scope="entry", key="source_id", value=profile.source_id),
    ]
    for key, value in sorted(profile.source_profile.items()):
        rows.append(_metadata_row(profile, scope="profile", key=key, value=_metadata_value(value)))
    if sequence_manifest.timestamps_path is not None:
        rows.append(
            _metadata_row(
                profile, scope="sequence", key="timestamps_path", value=sequence_manifest.timestamps_path.as_posix()
            )
        )
    if sequence_manifest.rgb_dir is not None:
        rows.append(_metadata_row(profile, scope="sequence", key="rgb_dir", value=sequence_manifest.rgb_dir.as_posix()))
    for ref in benchmark_inputs.observation_sequences:
        rows.append(_metadata_row(profile, scope="observation_sequence", key="source_id", value=ref.source_id))
        rows.append(
            _metadata_row(profile, scope="observation_sequence", key="payload_root", value=ref.payload_root.as_posix())
        )
    return rows


def _metadata_value(value: JsonValue) -> str:
    if isinstance(value, str | int | float | bool) or value is None:
        return str(value)
    return json.dumps(value, sort_keys=True)


def _manifest_timestamps_ns(manifest: SequenceManifest) -> list[int]:
    if manifest.timestamps_path is None:
        return []
    return load_timestamps_ns(manifest.timestamps_path)


def _manifest_frame_count(manifest: SequenceManifest, timestamps_ns: list[int]) -> int:
    if timestamps_ns:
        return len(timestamps_ns)
    if manifest.rgb_dir is None or not manifest.rgb_dir.exists():
        return 0
    return sum(1 for path in manifest.rgb_dir.iterdir() if path.is_file())


def _observation_sequence_stats_rows(
    profile: NormalizedDatasetProfile, ref: ObservationSequenceRef
) -> list[JsonObject]:
    index = load_observation_sequence_index(ref.index_path)
    frame_count = len(index.rows)
    depth_count = sum(1 for row in index.rows if row.depth_path is not None)
    duration_s = _duration_s_from_ns([row.timestamp_ns for row in index.rows])
    return _stats_rows(
        profile,
        scope="observation_sequence",
        subject=ref.source_id,
        values={
            "observation_frame_count": (frame_count, "count"),
            "rgb_frame_count": (sum(1 for row in index.rows if row.rgb_path is not None), "count"),
            "depth_frame_count": (depth_count, "count"),
            "depth_coverage_ratio": (0.0 if frame_count == 0 else depth_count / frame_count, "ratio"),
            "observation_duration_s": (duration_s, "s"),
            "observation_mean_fps": (_mean_fps(frame_count, duration_s), "Hz"),
        },
    )


def _trajectory_stats_rows(
    profile: NormalizedDatasetProfile, *, scope: str, trajectory_ref: ReferenceTrajectoryRef
) -> list[JsonObject]:
    trajectory = load_tum_trajectory(trajectory_ref.path)
    positions = np.asarray(trajectory.positions_xyz, dtype=np.float64)
    timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    pose_count = int(len(positions))
    duration_s = _duration_s(timestamps_s)
    segment_lengths = np.linalg.norm(np.diff(positions, axis=0), axis=1) if pose_count >= 2 else np.asarray([])
    positive_dt = np.diff(timestamps_s)
    speeds = np.divide(
        segment_lengths,
        positive_dt,
        out=np.zeros_like(segment_lengths),
        where=positive_dt > 0.0,
    )
    path_length_m = float(np.sum(segment_lengths))
    tangent_angle_sum_rad = _tangent_angle_sum_rad(positions)
    curvature_rad_m = 0.0 if path_length_m <= 0.0 else tangent_angle_sum_rad / path_length_m
    subject = trajectory_ref.source.value
    if trajectory_ref.coordinate_status is not None:
        subject = f"{subject}/{trajectory_ref.coordinate_status.value}"
    return _stats_rows(
        profile,
        scope=scope,
        subject=subject,
        values={
            "trajectory_pose_count": (pose_count, "count"),
            "trajectory_duration_s": (duration_s, "s"),
            "trajectory_path_length_m": (path_length_m, "m"),
            "trajectory_mean_speed_m_s": (float(np.mean(speeds)) if speeds.size else 0.0, "m/s"),
            "trajectory_max_speed_m_s": (float(np.max(speeds)) if speeds.size else 0.0, "m/s"),
            "trajectory_tangent_angle_sum_rad": (tangent_angle_sum_rad, "rad"),
            "trajectory_mean_angular_rate_rad_s": (
                0.0 if duration_s <= 0.0 else tangent_angle_sum_rad / duration_s,
                "rad/s",
            ),
            "trajectory_mean_curvature_rad_m": (curvature_rad_m, "rad/m"),
            "ego_motion_class": (_ego_motion_class(pose_count, duration_s, path_length_m, curvature_rad_m), "class"),
        },
    )


def _tangent_angle_sum_rad(positions: np.ndarray) -> float:
    segments = np.diff(positions, axis=0)
    lengths = np.linalg.norm(segments, axis=1)
    valid = segments[lengths > 0.0]
    if len(valid) < 2:
        return 0.0
    unit = valid / np.linalg.norm(valid, axis=1, keepdims=True)
    dots = np.sum(unit[:-1] * unit[1:], axis=1)
    return float(np.sum(np.arccos(np.clip(dots, -1.0, 1.0))))


def _ego_motion_class(pose_count: int, duration_s: float, path_length_m: float, curvature_rad_m: float) -> str:
    if pose_count < 3 or duration_s <= 0.0:
        return "degenerate"
    if path_length_m < 0.25:
        return "stationary"
    if curvature_rad_m < 0.10:
        return "low_curvature"
    if curvature_rad_m < 0.30:
        return "medium_curvature"
    return "high_curvature"


def _duration_s_from_ns(timestamps_ns: list[int]) -> float:
    if len(timestamps_ns) < 2:
        return 0.0
    return float((timestamps_ns[-1] - timestamps_ns[0]) / 1e9)


def _duration_s(timestamps_s: np.ndarray) -> float:
    if timestamps_s.size < 2:
        return 0.0
    return float(timestamps_s[-1] - timestamps_s[0])


def _mean_fps(frame_count: int, duration_s: float) -> float:
    return 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)


def _stats_rows(
    profile: NormalizedDatasetProfile,
    *,
    scope: str,
    subject: str,
    values: dict[str, tuple[int | float | str, str]],
) -> list[JsonObject]:
    return [
        {
            "dataset_id": profile.dataset_id.value,
            "sequence_id": profile.sequence_id,
            "profile_key": profile.profile_key,
            "source_id": profile.source_id,
            "scope": scope,
            "subject": subject,
            "stat": stat,
            "value": _csv_value(value),
            "unit": unit,
        }
        for stat, (value, unit) in values.items()
    ]


def _metadata_row(profile: NormalizedDatasetProfile, *, scope: str, key: str, value: str) -> JsonObject:
    return {
        "dataset_id": profile.dataset_id.value,
        "sequence_id": profile.sequence_id,
        "profile_key": profile.profile_key,
        "source_id": profile.source_id,
        "scope": scope,
        "key": key,
        "value": value,
    }


def _csv_value(value: int | float | str) -> str:
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _is_stale_schema(entry: NormalizedDatasetEntry, profile: NormalizedDatasetProfile) -> bool:
    return entry.schema_version != STORE_SCHEMA_VERSION or profile.schema_version != STORE_SCHEMA_VERSION


def _stale_schema_issue(
    *, dataset_id: DatasetId, entry: NormalizedDatasetEntry, profile: NormalizedDatasetProfile, entry_path: Path
) -> NormalizedDatasetStoreIssue:
    return NormalizedDatasetStoreIssue(
        dataset_id=dataset_id,
        sequence_id=entry.sequence_id,
        profile_key=entry.profile_key,
        entry_path=entry_path,
        status="stale_schema",
        message=(
            "Normalized entry schema_version does not match the current store schema: "
            f"entry={entry.schema_version}, profile={profile.schema_version}, expected={STORE_SCHEMA_VERSION}. "
            "Rebuild this normalized entry."
        ),
        entry_schema_version=entry.schema_version,
        profile_schema_version=profile.schema_version,
    )


def _invalid_entry_issue(*, dataset_id: DatasetId, entry_path: Path, exc: Exception) -> NormalizedDatasetStoreIssue:
    sequence_id = entry_path.parent.parent.name if entry_path.parent.parent != entry_path.parent else ""
    profile_key = entry_path.parent.name
    return NormalizedDatasetStoreIssue(
        dataset_id=dataset_id,
        sequence_id=sequence_id,
        profile_key=profile_key,
        entry_path=entry_path,
        status="invalid",
        message=f"{type(exc).__name__}: {exc}",
    )


def _validate_manifest_paths(root: Path, manifest: SequenceManifest) -> None:
    for path in (
        manifest.video_path,
        manifest.rgb_dir,
        manifest.timestamps_path,
        manifest.source_frame_indices_path,
        manifest.intrinsics_path,
        manifest.rotation_metadata_path,
    ):
        _ensure_optional_existing_under(root, path)
    if manifest.advio is None:
        return
    _ensure_existing_under(root, manifest.advio.calibration_path)
    _ensure_optional_existing_under(root, manifest.advio.fixpoints_csv_path)
    _ensure_existing_under(root, manifest.advio.pose_refs.ground_truth_csv_path)
    _ensure_optional_existing_under(root, manifest.advio.pose_refs.arcore_csv_path)
    _ensure_optional_existing_under(root, manifest.advio.pose_refs.arkit_csv_path)
    _ensure_optional_existing_under(root, manifest.advio.pose_refs.selected_pose_csv_path)


def _validate_benchmark_input_paths(root: Path, benchmark_inputs: PreparedBenchmarkInputs) -> None:
    for trajectory in benchmark_inputs.reference_trajectories:
        _ensure_existing_under(root, trajectory.path)
        _ensure_optional_existing_under(root, trajectory.metadata_path)
    for cloud in benchmark_inputs.reference_clouds:
        _ensure_existing_under(root, cloud.path)
        _ensure_existing_under(root, cloud.metadata_path)
    for ref in benchmark_inputs.observation_sequences:
        _ensure_existing_under(root, ref.index_path)
        _ensure_existing_under(root, ref.payload_root)
        index = ObservationSequenceIndex.model_validate_json(ref.index_path.read_text(encoding="utf-8"))
        for row in index.rows:
            _ensure_optional_existing_under(
                ref.payload_root, _resolve_observation_payload(ref.payload_root, row.rgb_path)
            )
            _ensure_optional_existing_under(
                ref.payload_root,
                _resolve_observation_payload(ref.payload_root, row.depth_path),
            )


def _resolve_observation_payload(payload_root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    return path if path.is_absolute() else payload_root / path


def _ensure_optional_existing_under(root: Path, path: Path | None) -> None:
    if path is not None:
        _ensure_existing_under(root, path)


def _ensure_existing_under(root: Path, path: Path) -> None:
    _ensure_under(root, path)
    if not path.exists():
        raise RuntimeError(f"Normalized entry path '{path}' does not exist.")


def _ensure_under(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Normalized entry path '{path}' is outside entry root '{root}'.") from exc


def _copy_path(source: Path, target: Path) -> Path:
    if source.resolve() == target.resolve():
        return source.resolve()
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return target.resolve()


def load_depth_array(path: Path) -> np.ndarray:
    """Load a metric-depth payload stored as `.npy` or image data."""
    if path.suffix.lower() == ".npy":
        return np.load(path).astype(np.float32)
    depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise FileNotFoundError(f"Could not load depth image: {path}")
    return depth.astype(np.float32)


def load_timestamps_ns(path: Path) -> list[int]:
    """Load normalized timestamps from JSON or simple delimited text."""
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        timestamp_values = payload["timestamps_ns"] if isinstance(payload, dict) else payload
        return [int(value) for value in timestamp_values]
    timestamps_ns: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        timestamp_s = stripped.split(",", maxsplit=1)[0].split(maxsplit=1)[0]
        timestamps_ns.append(int(round(float(timestamp_s) * 1e9)))
    return timestamps_ns


def _temporary_entry_root(final_root: Path) -> Path:
    workspace = final_root.parents[1] / f".tmp-normalized-{time.time_ns()}"
    return workspace / final_root.parent.name / final_root.name


def _cleanup_temporary_entry_root(temp_root: Path) -> None:
    workspace = temp_root.parents[1]
    if workspace.name.startswith(".tmp-normalized-") and workspace.exists():
        shutil.rmtree(workspace)
    elif temp_root.exists():
        shutil.rmtree(temp_root)


def _rebase_entry_metadata_paths(root: Path, *, old_root: Path, new_root: Path) -> None:
    sequence_manifest_path = root / SEQUENCE_MANIFEST_FILENAME
    benchmark_inputs_path = root / BENCHMARK_INPUTS_FILENAME
    entry_path = root / ENTRY_FILENAME
    temp_sequence_manifest = SequenceManifest.model_validate_json(sequence_manifest_path.read_text(encoding="utf-8"))
    temp_benchmark_inputs = PreparedBenchmarkInputs.model_validate_json(
        benchmark_inputs_path.read_text(encoding="utf-8")
    )
    sequence_manifest = _rebase_model_paths(temp_sequence_manifest, old_root=old_root, new_root=new_root)
    benchmark_inputs = _rebase_model_paths(temp_benchmark_inputs, old_root=old_root, new_root=new_root)
    entry = _rebase_model_paths(
        NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
        old_root=old_root,
        new_root=new_root,
    )
    profile = NormalizedDatasetProfile.model_validate(entry.profile)
    stats_long_path = root / STATS_LONG_FILENAME
    metadata_long_path = root / METADATA_LONG_FILENAME
    _write_csv(
        stats_long_path, STATS_LONG_HEADER, _entry_stats_rows(profile, temp_sequence_manifest, temp_benchmark_inputs)
    )
    _write_csv(
        metadata_long_path, METADATA_LONG_HEADER, _entry_metadata_rows(profile, sequence_manifest, benchmark_inputs)
    )
    entry = entry.model_copy(
        update={
            "stats_long_path": _rebase_path(stats_long_path, old_root=root, new_root=new_root),
            "metadata_long_path": _rebase_path(metadata_long_path, old_root=root, new_root=new_root),
        }
    )
    write_json(sequence_manifest_path, sequence_manifest)
    write_json(benchmark_inputs_path, benchmark_inputs)
    write_json(entry_path, entry)


def _rebase_model_paths(model: BaseModel, *, old_root: Path, new_root: Path) -> BaseModel:
    return type(model).model_validate(_rebase_path_values(model.model_dump(mode="python"), old_root, new_root))


def _rebase_path_values(value: object, old_root: Path, new_root: Path) -> object:
    if isinstance(value, Path):
        return _rebase_path(value, old_root=old_root, new_root=new_root)
    if isinstance(value, BaseModel):
        return _rebase_model_paths(value, old_root=old_root, new_root=new_root)
    if isinstance(value, list):
        return [_rebase_path_values(item, old_root, new_root) for item in value]
    if isinstance(value, tuple):
        return tuple(_rebase_path_values(item, old_root, new_root) for item in value)
    if isinstance(value, dict):
        return {key: _rebase_path_values(item, old_root, new_root) for key, item in value.items()}
    return value


def _rebase_path(path: Path, *, old_root: Path, new_root: Path) -> Path:
    resolved = path.resolve()
    old_resolved = old_root.resolve()
    try:
        relative_path = resolved.relative_to(old_resolved)
    except ValueError:
        return path
    return (new_root.resolve() / relative_path).resolve()


def _publish_entry_root(*, temp_root: Path, final_root: Path) -> None:
    final_root.parent.mkdir(parents=True, exist_ok=True)
    backup_root = final_root.with_name(f".{final_root.name}.old-{time.time_ns()}")
    moved_existing = False
    try:
        if final_root.exists():
            os.replace(final_root, backup_root)
            moved_existing = True
        os.replace(temp_root, final_root)
    except Exception:
        if moved_existing and backup_root.exists() and not final_root.exists():
            os.replace(backup_root, final_root)
        raise
    if backup_root.exists():
        shutil.rmtree(backup_root)


def _normalize_observation_sequence_ref(ref: ObservationSequenceRef, *, target_root: Path) -> ObservationSequenceRef:
    if ref.payload_root.resolve() != target_root.resolve():
        payload_root = _copy_path(ref.payload_root, target_root)
    else:
        payload_root = ref.payload_root.resolve()
    index = ObservationSequenceIndex.model_validate_json(ref.index_path.read_text(encoding="utf-8"))
    index_path = payload_root / ref.index_path.name
    write_json(index_path, index)
    return ref.model_copy(update={"index_path": index_path.resolve(), "payload_root": payload_root})


def _normalize_advio_assets(assets: AdvioManifestAssets, *, input_root: Path) -> AdvioManifestAssets:
    advio_root = input_root / "advio"
    pose_refs = AdvioRawPoseRefs(
        ground_truth_csv_path=_copy_path(assets.pose_refs.ground_truth_csv_path, advio_root / "ground_truth_pose.csv"),
        arcore_csv_path=_copy_optional_path(assets.pose_refs.arcore_csv_path, advio_root / "arcore.csv"),
        arkit_csv_path=_copy_optional_path(assets.pose_refs.arkit_csv_path, advio_root / "arkit.csv"),
        selected_pose_csv_path=_copy_optional_path(
            assets.pose_refs.selected_pose_csv_path, advio_root / "selected_pose.csv"
        ),
    )
    return assets.model_copy(
        update={
            "calibration_path": _copy_path(assets.calibration_path, advio_root / "calibration.yaml"),
            "fixpoints_csv_path": _copy_optional_path(assets.fixpoints_csv_path, advio_root / "fixpoints.csv"),
            "pose_refs": pose_refs,
        }
    )


def _copy_optional_path(source: Path | None, target: Path) -> Path | None:
    if source is None:
        return None
    return _copy_path(source, target)


def _normalized_observation_sequence_root(*, root: Path, sequence_count: int, index: int) -> Path:
    if sequence_count == 1:
        return root / "observations"
    return root / "observations" / str(index)


def _remove_staged_observation_sequence(*, source_root: Path, normalized_root: Path, entry_root: Path) -> None:
    transient_root = (entry_root / "benchmark" / "observations").resolve()
    if source_root.resolve() != transient_root or normalized_root.resolve() == transient_root:
        return
    if source_root.exists():
        shutil.rmtree(source_root)


def _dedupe_manifest_rgb(
    manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
    *,
    input_root: Path,
) -> SequenceManifest:
    observation_sequence = benchmark_inputs.default_observation_sequence()
    if observation_sequence is None:
        return manifest
    rgb_dir = observation_sequence.payload_root / "rgb"
    if not rgb_dir.is_dir():
        return manifest
    if manifest.rgb_dir is not None and manifest.rgb_dir.exists() and manifest.rgb_dir.resolve() != rgb_dir.resolve():
        shutil.rmtree(manifest.rgb_dir)
    updates: dict[str, Path] = {"rgb_dir": rgb_dir.resolve()}
    index = ObservationSequenceIndex.model_validate_json(observation_sequence.index_path.read_text(encoding="utf-8"))
    first_intrinsics = next((row.intrinsics for row in index.rows if row.intrinsics is not None), None)
    if first_intrinsics is not None:
        updates["intrinsics_path"] = write_camera_intrinsics_yaml(first_intrinsics, input_root / "intrinsics.yaml")
    return manifest.model_copy(update=updates)


def _select_observation_sequence(
    ref: ObservationSequenceRef,
    *,
    frame_selection: FrameSelectionConfig,
    output_dir: Path,
) -> ObservationSequenceRef:
    index = ObservationSequenceIndex.model_validate_json(ref.index_path.read_text(encoding="utf-8"))
    timestamps_ns = [row.timestamp_ns for row in index.rows]
    selected_indices = _selected_indices(timestamps_ns, frame_selection)
    selected_rows = [
        index.rows[source_index].model_copy(update={"seq": seq}) for seq, source_index in enumerate(selected_indices)
    ]
    selected = index.model_copy(update={"rows": selected_rows, "observation_count": len(selected_rows)})
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / f"{ref.source_id}_{ref.sequence_id}_observations.json"
    write_json(index_path, selected)
    return ref.model_copy(update={"index_path": index_path.resolve(), "observation_count": len(selected_rows)})


def _selected_indices(timestamps_ns: list[int], frame_selection: FrameSelectionConfig) -> list[int]:
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    return list(range(0, len(timestamps_ns), stride))


class NormalizableDatasetSource(OfflineSequenceSource, BenchmarkInputSource, Protocol):
    """Source that can materialize both normalized run input and benchmark sidecars."""

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        """Materialize benchmark inputs required for a normalized-store entry."""
        ...
