"""Persistent normalized dataset entries for offline dataset-backed sources."""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import warnings
from collections.abc import Callable, ItemsView, Iterable
from pathlib import Path
from typing import Any, Protocol, cast

import cv2
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from evo.core import geometry, sync
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from pydantic import AliasChoices, BaseModel, Field, RootModel

from prml_vslam.interfaces import (
    FrameTransform,
    ObservationSequenceIndex,
    ObservationSequenceRef,
    write_camera_intrinsics_yaml,
)
from prml_vslam.sources.contracts import (
    AdvioManifestAssets,
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import (
    ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION,
    AdvioPoseFrameMode,
    AdvioPoseSource,
    AdvioServingConfig,
    DatasetId,
    FrameSelectionConfig,
)
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.protocols import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.sources.replay import ImageSequenceObservationSource, ObservationStream, ReplayMode
from prml_vslam.utils import BaseData, JsonObject, JsonValue, PathConfig
from prml_vslam.utils.geometry import (
    apply_similarity_to_trajectory,
    load_tum_trajectory,
    trajectory_relative_to_first_pose,
    write_tum_trajectory,
    yaw_similarity_align,
)
from prml_vslam.utils.portable_paths import rebase_model_paths, write_portable_json
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
STORE_SCHEMA_VERSION = 10
_ADVIO_ALIGN_MAX_DIFF_S = 0.01
_ADVIO_ALIGN_MIN_PAIRS = 3
_ADVIO_RDF_DOWN_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)
_ADVIO_GT_LOCAL_FIRST_POSE_FRAME = "advio_gt_world_local_first_pose"
_PROFILE_KEY_PATTERN = re.compile(r"^[0-9a-f]{24}$")
_ADVIO_LOCAL_FIRST_POSE_FRAMES = {
    ReferenceSource.GROUND_TRUTH: _ADVIO_GT_LOCAL_FIRST_POSE_FRAME,
    ReferenceSource.ARCORE: "advio_arcore_world_local_first_pose",
    ReferenceSource.ARKIT: "advio_arkit_world_local_first_pose",
}
_RUNTIME_SOFT_SOURCE_PROFILE_KEYS = frozenset({"frame_stride", "target_fps", "reference_cloud", "replay_mode"})


class NormalizedSourceProfile(RootModel[dict[str, Any]]):
    """Typed access boundary for byte-affecting normalized source settings."""

    root: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of the persisted profile payload."""
        return dict(self.root)

    def get(self, key: str, default: Any = None) -> Any:
        """Return one profile value by key."""
        return self.root.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Return one required profile value by key."""
        return self.root[key]

    def __contains__(self, key: str) -> bool:
        """Return whether a profile key is present."""
        return key in self.root

    def items(self) -> ItemsView[str, Any]:
        """Return profile key/value pairs."""
        return self.root.items()

    @property
    def frame_stride(self) -> int:
        """Requested frame stride recorded in the normalized profile."""
        return int(self.root.get("frame_stride", 1))

    @property
    def target_fps(self) -> float | None:
        """Requested target FPS recorded in the normalized profile."""
        return _optional_float(self.root.get("target_fps"))

    @property
    def trajectory_convention(self) -> str | None:
        """Named trajectory convention for normalized entries that define one."""
        value = self.root.get("trajectory_convention")
        return value if isinstance(value, str) else None

    @property
    def dataset_serving(self) -> dict[str, Any]:
        """Dataset-serving settings embedded in the normalized profile."""
        value = self.root.get("dataset_serving")
        return value if isinstance(value, dict) else {}


class NormalizedDatasetProfile(BaseData):
    """Canonical byte-affecting profile used to key one normalized entry."""

    schema_version: int = STORE_SCHEMA_VERSION
    dataset_id: DatasetId
    sequence_id: str
    source_id: str
    source_profile: NormalizedSourceProfile

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
    profile: NormalizedDatasetProfile
    root: Path
    sequence_manifest_path: Path
    benchmark_inputs_path: Path
    stats_long_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("stats_long_path", "stats_long_csv_path"),
    )
    metadata_long_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_long_path", "metadata_long_csv_path"),
    )
    created_at_ns: int = Field(default_factory=time.time_ns)


class NormalizedDatasetStore:
    """Filesystem store for reusable normalized dataset replay payloads."""

    def __init__(self, *, store_root: Path, dataset_id: DatasetId) -> None:
        self.dataset_id = dataset_id
        self.store_root = store_root.resolve()

    @property
    def preview_root(self) -> Path:
        """Return the run-local preview scratch root for normalized entries."""
        return self.store_root / ".preview"

    def entry_root(self, profile: NormalizedDatasetProfile) -> Path:
        """Return the root directory for one profile."""
        return self._entry_root_for_identity(sequence_id=profile.sequence_id, profile_key=profile.profile_key)

    def load_entry(self, profile: NormalizedDatasetProfile) -> NormalizedDatasetEntry:
        """Load one complete normalized entry."""
        entry_path = self.entry_root(profile) / ENTRY_FILENAME
        if not entry_path.exists():
            raise FileNotFoundError(self.missing_entry_message(profile))
        entry = rebase_model_paths(
            NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
            root=entry_path.parent,
        )
        self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
        self._validate_entry_payloads(entry)
        return entry

    def load_entry_for_runtime(
        self,
        profile: NormalizedDatasetProfile,
        *,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> NormalizedDatasetEntry:
        """Load the exact normalized entry required by runtime paths."""
        entry = self.load_entry(profile)
        self._validate_runtime_entry(entry)
        _validate_read_frame_selection(entry, frame_selection)
        return entry

    def select_entry_for_runtime(
        self,
        profile: NormalizedDatasetProfile,
        *,
        frame_selection: FrameSelectionConfig | None = None,
        prefer_reference_cloud: bool = False,
    ) -> NormalizedDatasetEntry:
        """Select a current runtime entry, allowing only run-local soft fields to differ."""
        candidates = [entry for entry in self.summary(strict=False) if _runtime_profiles_match(profile, entry.profile)]
        if not candidates:
            raise FileNotFoundError(self.missing_runtime_entry_message(profile))
        entry = min(
            candidates,
            key=lambda candidate: _runtime_selection_sort_key(candidate, prefer_reference_cloud=prefer_reference_cloud),
        )
        _validate_read_frame_selection(entry, frame_selection)
        _warn_runtime_profile_soft_mismatch(requested=profile, selected=entry)
        return entry

    def load_entry_by_key_for_runtime(
        self,
        *,
        sequence_id: str,
        profile_key: str,
        frame_selection: FrameSelectionConfig | None = None,
    ) -> NormalizedDatasetEntry:
        """Load an exact normalized entry selected by sequence/profile key for runtime replay."""
        entry_path = self._entry_root_for_identity(sequence_id=sequence_id, profile_key=profile_key) / ENTRY_FILENAME
        if not entry_path.exists():
            raise FileNotFoundError(
                f"Missing normalized dataset entry dataset_id={self.dataset_id.value} "
                f"sequence_id={sequence_id} profile_key={profile_key}."
            )
        entry = rebase_model_paths(
            NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
            root=entry_path.parent,
        )
        profile = NormalizedDatasetProfile.model_validate(entry.profile)
        self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
        self._validate_entry_payloads(entry)
        self._validate_runtime_entry(entry)
        _validate_read_frame_selection(entry, frame_selection)
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

    def missing_runtime_entry_message(self, profile: NormalizedDatasetProfile) -> str:
        """Return an actionable compatible-runtime-entry diagnostic."""
        return (
            "Missing compatible normalized runtime entry "
            f"dataset_id={profile.dataset_id.value} sequence_id={profile.sequence_id} "
            f"source_id={profile.source_id} requested_profile_key={profile.profile_key}. "
            "Build a normalized datastore entry for the same observation-affecting profile. "
            f"Run: prml-vslam dataset normalize --dataset {profile.dataset_id.value} "
            f"--sequence {profile.sequence_id}"
        )

    def create_entry(
        self,
        *,
        profile: NormalizedDatasetProfile,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs,
    ) -> NormalizedDatasetEntry:
        """Persist one normalized entry."""
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
        benchmark_inputs = self._normalize_benchmark_inputs(
            benchmark_inputs, root=root, sequence_manifest=sequence_manifest
        )
        sequence_manifest = self._normalize_sequence_manifest(
            sequence_manifest,
            profile=profile,
            benchmark_inputs=benchmark_inputs,
            input_root=root / "input",
        )
        sequence_manifest_path = root / SEQUENCE_MANIFEST_FILENAME
        benchmark_inputs_path = root / BENCHMARK_INPUTS_FILENAME
        write_portable_json(sequence_manifest_path, sequence_manifest, root=root)
        write_portable_json(benchmark_inputs_path, benchmark_inputs, root=root)
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
        write_portable_json(root / ENTRY_FILENAME, entry, root=root)
        return entry

    def create_entry_from_source(
        self,
        *,
        profile: NormalizedDatasetProfile,
        source: NormalizableDatasetSource,
    ) -> NormalizedDatasetEntry:
        """Prepare and persist one normalized entry from a dataset source."""
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
        manifest = rebase_model_paths(
            SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8")),
            root=entry.root,
        )
        if manifest.timestamps_path is None:
            return manifest
        observation_sequence = rebase_model_paths(
            PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
            root=entry.root,
        ).default_observation_sequence()
        observation_index = (
            None if observation_sequence is None else load_observation_sequence_index(observation_sequence.index_path)
        )
        timestamps_ns = (
            [row.timestamp_ns for row in observation_index.rows]
            if observation_index is not None
            else load_timestamps_ns(manifest.timestamps_path)
        )
        selected_indices, sampling_payload = _selected_indices_and_sampling_payload(timestamps_ns, frame_selection)
        output_dir.mkdir(parents=True, exist_ok=True)
        selected_timestamps_path = output_dir / "timestamps.json"
        selected_indices_path = output_dir / "source_frame_indices.json"
        selected_observation_sequence = (
            _select_observation_sequence(observation_sequence, frame_selection=frame_selection, output_dir=output_dir)
            if observation_sequence is not None
            else None
        )
        selected_source_frame_indices = selected_indices
        if observation_index is not None:
            selected_source_frame_indices = [
                row.provenance.source_frame_index if row.provenance.source_frame_index is not None else row.seq
                for row in (observation_index.rows[index] for index in selected_indices)
            ]
        _warn_runtime_sampling_if_downsampled(
            entry=entry,
            frame_selection=frame_selection,
            sampling_payload=sampling_payload,
            stored_timestamps_ns=timestamps_ns,
        )
        timestamp_payload: JsonObject = {
            "timestamps_ns": [timestamps_ns[index] for index in selected_indices],
            **sampling_payload,
        }
        write_json(selected_timestamps_path, timestamp_payload)
        write_json(selected_indices_path, {"source_frame_indices": selected_source_frame_indices})
        return manifest.model_copy(
            update={
                "timestamps_path": selected_timestamps_path.resolve(),
                "source_frame_indices_path": selected_indices_path.resolve(),
                "observation_index_path": (
                    None if selected_observation_sequence is None else selected_observation_sequence.index_path
                ),
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
        benchmark_inputs = rebase_model_paths(
            PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
            root=entry.root,
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
                entry = rebase_model_paths(
                    NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
                    root=entry_path.parent,
                )
                profile = entry.profile
                if not _is_current_schema(entry, profile):
                    issues.append(
                        _stale_schema_issue(
                            dataset_id=self.dataset_id, entry=entry, profile=profile, entry_path=entry_path
                        )
                    )
                    continue
                self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
                self._validate_entry_payloads(entry)
                self._validate_runtime_entry(entry)
            except Exception as exc:
                issues.append(_invalid_entry_issue(dataset_id=self.dataset_id, entry_path=entry_path, exc=exc))
        return issues

    def _scan_entries(self, *, strict: bool) -> Iterable[NormalizedDatasetEntry]:
        if not self.store_root.exists():
            return []
        entries: list[NormalizedDatasetEntry] = []
        for entry_path in sorted(self.store_root.glob(f"*/*/{ENTRY_FILENAME}")):
            try:
                entry = rebase_model_paths(
                    NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
                    root=entry_path.parent,
                )
                profile = entry.profile
                if not _is_current_schema(entry, profile):
                    continue
                self._validate_entry(entry=entry, profile=profile, entry_path=entry_path)
                self._validate_entry_payloads(entry)
                self._validate_runtime_entry(entry)
            except Exception:
                if strict:
                    raise
                continue
            entries.append(entry)
        return entries

    def _entry_root_for_identity(self, *, sequence_id: str, profile_key: str) -> Path:
        _validate_entry_identity_components(sequence_id=sequence_id, profile_key=profile_key)
        root = (self.store_root / sequence_id / profile_key).resolve()
        _ensure_under(self.store_root, root)
        return root

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
        if not _is_current_schema(entry, profile):
            raise RuntimeError(
                "Normalized entry schema_version does not match the current store schema: "
                f"entry={entry.schema_version}, profile={profile.schema_version}, expected={STORE_SCHEMA_VERSION}."
            )
        _validate_entry_identity_components(sequence_id=entry.sequence_id, profile_key=entry.profile_key)
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
                ("profile", entry.profile, profile),
            )
            if actual != expected
        }
        if mismatches:
            raise RuntimeError(f"Normalized entry metadata does not match requested profile: {mismatches}")

    def _validate_runtime_entry(self, entry: NormalizedDatasetEntry) -> None:
        _validate_current_runtime_entry(entry)

    def _validate_entry_payloads(self, entry: NormalizedDatasetEntry) -> None:
        manifest = rebase_model_paths(
            SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8")),
            root=entry.root,
        )
        _validate_manifest_paths(entry.root, manifest)
        benchmark_inputs = rebase_model_paths(
            PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
            root=entry.root,
        )
        _validate_benchmark_input_paths(entry.root, benchmark_inputs)
        _validate_entry_analysis_tables(entry)

    def _normalize_sequence_manifest(
        self,
        manifest: SequenceManifest,
        *,
        profile: NormalizedDatasetProfile,
        benchmark_inputs: PreparedBenchmarkInputs,
        input_root: Path,
    ) -> SequenceManifest:
        updates: dict[str, Path | None] = {"source_frame_indices_path": None}
        observation_sequence = benchmark_inputs.default_observation_sequence()
        if manifest.video_path is not None and observation_sequence is not None:
            index = ObservationSequenceIndex.model_validate_json(
                observation_sequence.index_path.read_text(encoding="utf-8")
            )
            timestamps_path = input_root / "timestamps.json"
            write_json(
                timestamps_path,
                {
                    "timestamps_ns": [row.timestamp_ns for row in index.rows],
                    **_stored_sampling_payload(profile.source_profile, index.rows),
                },
            )
            updates["video_path"] = None
            updates["rgb_dir"] = observation_sequence.payload_root / "rgb"
            updates["timestamps_path"] = timestamps_path
            updates["observation_index_path"] = observation_sequence.index_path
        elif manifest.video_path is not None:
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
            write_json(
                timestamps_path,
                {
                    "timestamps_ns": timestamps_ns,
                    **_source_profile_sampling_payload(profile.source_profile, timestamps_ns),
                },
            )
            updates["timestamps_path"] = timestamps_path
        elif manifest.rgb_dir is not None:
            updates["rgb_dir"] = _copy_path(manifest.rgb_dir, input_root / "rgb")
        if manifest.timestamps_path is not None and "timestamps_path" not in updates:
            timestamps_path = input_root / "timestamps.json"
            timestamps_ns = load_timestamps_ns(manifest.timestamps_path)
            write_json(
                timestamps_path,
                {
                    "timestamps_ns": timestamps_ns,
                    **_source_profile_sampling_payload(profile.source_profile, timestamps_ns),
                },
            )
            updates["timestamps_path"] = timestamps_path
        if manifest.intrinsics_path is not None:
            updates["intrinsics_path"] = _copy_path(manifest.intrinsics_path, input_root / "intrinsics.yaml")
        if manifest.rotation_metadata_path is not None:
            updates["rotation_metadata_path"] = _copy_path(
                manifest.rotation_metadata_path, input_root / manifest.rotation_metadata_path.name
            )
        manifest = manifest.model_copy(update=updates)
        if manifest.advio is not None:
            manifest = manifest.model_copy(
                update={"advio": _normalize_advio_assets(manifest.advio, input_root=input_root)}
            )
        if self.dataset_id is DatasetId.ADVIO and manifest.dataset_serving is not None:
            manifest = manifest.model_copy(
                update={
                    "dataset_serving": manifest.dataset_serving.model_copy(
                        update={"pose_frame_mode": AdvioPoseFrameMode.FIXEDPOINT_COMMON_START_LOCAL}
                    )
                }
            )
        return _dedupe_manifest_rgb(manifest, benchmark_inputs, input_root=input_root)

    def _normalize_benchmark_inputs(
        self,
        benchmark_inputs: PreparedBenchmarkInputs,
        *,
        root: Path,
        sequence_manifest: SequenceManifest,
    ) -> PreparedBenchmarkInputs:
        if self.dataset_id is DatasetId.ADVIO:
            return _normalize_advio_benchmark_inputs(benchmark_inputs, root=root, sequence_manifest=sequence_manifest)
        trajectory_copies: dict[Path, Path] = {}
        reference_trajectories = _normalize_reference_trajectories(
            benchmark_inputs.reference_trajectories,
            target_root=root / "benchmark" / "trajectories",
            copies=trajectory_copies,
            relative_to_first_pose=True,
        )
        candidate_trajectories = _normalize_reference_trajectories(
            benchmark_inputs.candidate_trajectories,
            target_root=root / "benchmark" / "trajectories",
            copies=trajectory_copies,
            relative_to_first_pose=True,
        )
        reference_clouds = _normalize_reference_clouds(
            benchmark_inputs.reference_clouds,
            target_root=root / "benchmark" / "reference_clouds",
        )
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
        _remove_rebased_benchmark_sources(
            source_inputs=benchmark_inputs,
            kept_paths=_benchmark_artifact_paths([*reference_trajectories, *candidate_trajectories, *reference_clouds]),
            entry_root=root,
        )
        return benchmark_inputs.model_copy(
            update={
                "reference_trajectories": reference_trajectories,
                "candidate_trajectories": candidate_trajectories,
                "reference_clouds": reference_clouds,
                "observation_sequences": observation_sequences,
            }
        )


def normalized_dataset_profile(
    *,
    dataset_id: DatasetId,
    sequence_id: str,
    source_id: str,
    payload: JsonObject,
) -> NormalizedDatasetProfile:
    """Build a profile from source settings that change stored bytes."""
    profile: dict[str, JsonValue] = {
        key: value for key, value in payload.items() if key not in {"dataset_id", "sequence_id", "source_id"}
    }
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
        "stats_long_row_count": len(_read_analysis_table(entry.stats_long_path, STATS_LONG_HEADER).index),
        "metadata_long_path": None if entry.metadata_long_path is None else entry.metadata_long_path.as_posix(),
        "metadata_long_row_count": len(_read_analysis_table(entry.metadata_long_path, METADATA_LONG_HEADER).index),
    }


def load_normalized_entry_stats_table(entry: NormalizedDatasetEntry) -> pd.DataFrame:
    """Load persisted long-form statistics as a dataframe."""
    return _read_analysis_table(entry.stats_long_path, STATS_LONG_HEADER)


def load_normalized_entry_stats(entry: NormalizedDatasetEntry) -> list[JsonObject]:
    """Load persisted long-form statistics rows for one normalized entry."""
    return load_normalized_entry_stats_table(entry).to_dict(orient="records")


def load_normalized_entry_metadata_table(entry: NormalizedDatasetEntry) -> pd.DataFrame:
    """Load persisted long-form metadata as a dataframe."""
    return _read_analysis_table(entry.metadata_long_path, METADATA_LONG_HEADER)


def load_normalized_entry_metadata(entry: NormalizedDatasetEntry) -> list[JsonObject]:
    """Load persisted long-form metadata rows for one normalized entry."""
    return load_normalized_entry_metadata_table(entry).to_dict(orient="records")


def _validate_entry_analysis_tables(entry: NormalizedDatasetEntry) -> None:
    if entry.stats_long_path is not None:
        _read_analysis_table(entry.stats_long_path, STATS_LONG_HEADER)
    if entry.metadata_long_path is not None:
        _read_analysis_table(entry.metadata_long_path, METADATA_LONG_HEADER)


def _read_analysis_table(path: Path | None, header: tuple[str, ...]) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame(columns=header)
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    if tuple(table.columns) != header:
        raise RuntimeError(f"Normalized analysis table '{path}' has invalid CSV header {list(table.columns)}.")
    return table


def _write_entry_analysis_tables(
    *,
    root: Path,
    profile: NormalizedDatasetProfile,
    sequence_manifest: SequenceManifest,
    benchmark_inputs: PreparedBenchmarkInputs,
) -> tuple[Path, Path]:
    stats_path = root / STATS_LONG_FILENAME
    metadata_path = root / METADATA_LONG_FILENAME
    _write_analysis_table(
        stats_path, STATS_LONG_HEADER, _entry_stats_rows(profile, sequence_manifest, benchmark_inputs)
    )
    _write_analysis_table(
        metadata_path, METADATA_LONG_HEADER, _entry_metadata_rows(profile, sequence_manifest, benchmark_inputs)
    )
    return stats_path.resolve(), metadata_path.resolve()


def _write_analysis_table(path: Path, header: tuple[str, ...], rows: list[JsonObject]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=header).to_csv(path, index=False)


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
    timestamp_metadata: JsonObject | None = None,
) -> list[JsonObject]:
    rows = [
        _metadata_row(profile, scope="entry", key="schema_version", value=str(STORE_SCHEMA_VERSION)),
    ]
    for key, value in sorted(profile.source_profile.items()):
        rows.append(_metadata_row(profile, scope="profile", key=key, value=_metadata_value(value)))
    if sequence_manifest.timestamps_path is not None:
        rows.append(
            _metadata_row(
                profile, scope="sequence", key="timestamps_path", value=sequence_manifest.timestamps_path.as_posix()
            )
        )
        metadata = (
            _read_timestamp_metadata(sequence_manifest.timestamps_path)
            if timestamp_metadata is None
            else timestamp_metadata
        )
        for key, value in metadata.items():
            rows.append(_metadata_row(profile, scope="sequence", key=key, value=_metadata_value(value)))
    if sequence_manifest.rgb_dir is not None:
        rows.append(_metadata_row(profile, scope="sequence", key="rgb_dir", value=sequence_manifest.rgb_dir.as_posix()))
    if sequence_manifest.video_path is not None:
        rows.append(
            _metadata_row(profile, scope="sequence", key="video_path", value=sequence_manifest.video_path.as_posix())
        )
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


def _read_timestamp_metadata(path: Path) -> JsonObject:
    if path.suffix != ".json":
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}
    return {
        key: value
        for key, value in payload.items()
        if key
        in {
            "requested_frame_stride",
            "requested_target_fps",
            "resolved_frame_stride",
            "resolved_target_fps",
            "frame_stride",
            "target_fps",
        }
    }


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


def _duration_s_from_ns(timestamps_ns: list[int]) -> float:
    if len(timestamps_ns) < 2:
        return 0.0
    return float((timestamps_ns[-1] - timestamps_ns[0]) / 1e9)


def _runtime_profiles_match(
    requested: NormalizedDatasetProfile,
    stored: NormalizedDatasetProfile,
) -> bool:
    return _runtime_identity_payload(requested) == _runtime_identity_payload(stored)


def _runtime_identity_payload(profile: NormalizedDatasetProfile) -> JsonObject:
    payload = cast(JsonObject, profile.model_dump(mode="json"))
    source_profile = dict(profile.source_profile.as_dict())
    for key in _RUNTIME_SOFT_SOURCE_PROFILE_KEYS:
        source_profile.pop(key, None)
    payload["source_profile"] = source_profile
    return payload


def _runtime_selection_sort_key(
    entry: NormalizedDatasetEntry,
    *,
    prefer_reference_cloud: bool,
) -> tuple[int, float, int, str]:
    timestamps_ns = _entry_runtime_timestamps_ns(entry)
    fps = _mean_fps(len(timestamps_ns), _duration_s_from_ns(timestamps_ns))
    reference_cloud_rank = 0 if prefer_reference_cloud and _entry_has_existing_reference_cloud(entry) else 1
    return (
        reference_cloud_rank,
        -fps,
        -len(timestamps_ns),
        entry.profile_key,
    )


def _entry_runtime_timestamps_ns(entry: NormalizedDatasetEntry) -> list[int]:
    benchmark_inputs = rebase_model_paths(
        PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
        root=entry.root,
    )
    observation_sequence = benchmark_inputs.default_observation_sequence()
    if observation_sequence is not None:
        return [row.timestamp_ns for row in load_observation_sequence_index(observation_sequence.index_path).rows]
    manifest = rebase_model_paths(
        SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8")),
        root=entry.root,
    )
    if manifest.timestamps_path is None:
        return []
    return load_timestamps_ns(manifest.timestamps_path)


def _entry_has_existing_reference_cloud(entry: NormalizedDatasetEntry) -> bool:
    benchmark_inputs = rebase_model_paths(
        PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8")),
        root=entry.root,
    )
    return any(ref.path.exists() and ref.metadata_path.exists() for ref in benchmark_inputs.reference_clouds)


def _warn_runtime_profile_soft_mismatch(
    *,
    requested: NormalizedDatasetProfile,
    selected: NormalizedDatasetEntry,
) -> None:
    requested_profile = requested.source_profile.as_dict()
    selected_profile = selected.profile.source_profile.as_dict()
    mismatches = {
        key: (
            selected_profile.get(key),
            requested_profile.get(key),
        )
        for key in sorted(_RUNTIME_SOFT_SOURCE_PROFILE_KEYS)
        if selected_profile.get(key) != requested_profile.get(key)
    }
    if not mismatches:
        return
    details = ", ".join(
        f"{key}: stored={stored!r}, requested={requested!r}" for key, (stored, requested) in mismatches.items()
    )
    warnings.warn(
        "Selected compatible normalized runtime entry with run-local profile differences: "
        f"selected_profile_key={selected.profile_key}; {details}. Runtime sampling and cloud stages use "
        "the selected stored observations/artifacts.",
        RuntimeWarning,
        stacklevel=3,
    )


def _duration_s(timestamps_s: np.ndarray) -> float:
    if timestamps_s.size < 2:
        return 0.0
    return float(timestamps_s[-1] - timestamps_s[0])


def _mean_fps(frame_count: int, duration_s: float) -> float:
    return 0.0 if duration_s <= 0.0 else float(max(frame_count - 1, 0) / duration_s)


def _selected_indices_and_sampling_payload(
    timestamps_ns: list[int],
    frame_selection: FrameSelectionConfig,
) -> tuple[list[int], JsonObject]:
    _validate_requested_target_fps(timestamps_ns, frame_selection)
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    selected_indices = list(range(0, len(timestamps_ns), stride))
    selected_timestamps_ns = [timestamps_ns[index] for index in selected_indices]
    return selected_indices, _sampling_payload(
        requested_frame_stride=frame_selection.frame_stride,
        requested_target_fps=frame_selection.target_fps,
        resolved_frame_stride=stride,
        resolved_target_fps=_mean_fps(len(selected_timestamps_ns), _duration_s_from_ns(selected_timestamps_ns)),
    )


def _warn_runtime_sampling_if_downsampled(
    *,
    entry: NormalizedDatasetEntry,
    frame_selection: FrameSelectionConfig,
    sampling_payload: JsonObject,
    stored_timestamps_ns: list[int],
) -> None:
    if frame_selection.frame_stride == 1 and frame_selection.target_fps is None:
        return
    stored_fps = _mean_fps(len(stored_timestamps_ns), _duration_s_from_ns(stored_timestamps_ns))
    if frame_selection.target_fps is not None and stored_fps > 0.0 and frame_selection.target_fps > stored_fps * 1.01:
        return
    if int(sampling_payload["resolved_frame_stride"]) == 1:
        return
    source_profile = entry.profile.source_profile
    warnings.warn(
        "Runtime frame selection downsampled normalized observations: "
        f"stored_frame_stride={source_profile.frame_stride}, "
        f"stored_target_fps={source_profile.target_fps}, "
        f"requested_frame_stride={sampling_payload['requested_frame_stride']}, "
        f"requested_target_fps={sampling_payload['requested_target_fps']}, "
        f"resolved_frame_stride={sampling_payload['resolved_frame_stride']}, "
        f"resolved_target_fps={sampling_payload['resolved_target_fps']:.6g}.",
        RuntimeWarning,
        stacklevel=3,
    )


def _stored_sampling_payload(source_profile: NormalizedSourceProfile, rows: list[Any]) -> JsonObject:
    timestamps_ns = [int(row.timestamp_ns) for row in rows]
    return _sampling_payload(
        requested_frame_stride=source_profile.frame_stride,
        requested_target_fps=source_profile.target_fps,
        resolved_frame_stride=_resolved_source_frame_stride(rows, source_profile),
        resolved_target_fps=_mean_fps(len(timestamps_ns), _duration_s_from_ns(timestamps_ns)),
    )


def _source_profile_sampling_payload(source_profile: NormalizedSourceProfile, timestamps_ns: list[int]) -> JsonObject:
    frame_selection = FrameSelectionConfig(
        frame_stride=source_profile.frame_stride,
        target_fps=source_profile.target_fps,
    )
    stride = frame_selection.stride_for_timestamps_ns(timestamps_ns)
    selected_timestamps_ns = timestamps_ns[::stride]
    return _sampling_payload(
        requested_frame_stride=frame_selection.frame_stride,
        requested_target_fps=frame_selection.target_fps,
        resolved_frame_stride=stride,
        resolved_target_fps=_mean_fps(len(selected_timestamps_ns), _duration_s_from_ns(selected_timestamps_ns)),
    )


def _sampling_payload(
    *,
    requested_frame_stride: int,
    requested_target_fps: float | None,
    resolved_frame_stride: int,
    resolved_target_fps: float,
) -> JsonObject:
    return {
        "requested_frame_stride": requested_frame_stride,
        "requested_target_fps": requested_target_fps,
        "resolved_frame_stride": resolved_frame_stride,
        "resolved_target_fps": resolved_target_fps,
        "frame_stride": resolved_frame_stride,
        "target_fps": resolved_target_fps,
    }


def _resolved_source_frame_stride(rows: list[Any], source_profile: NormalizedSourceProfile) -> int:
    indices = [int(row.provenance.source_frame_index) for row in rows if row.provenance.source_frame_index is not None]
    if len(indices) < 2:
        return source_profile.frame_stride
    deltas = [right - left for left, right in zip(indices, indices[1:], strict=False)]
    positive = [delta for delta in deltas if delta > 0]
    return int(round(float(np.median(positive)))) if positive else source_profile.frame_stride


def _validate_requested_target_fps(
    timestamps_ns: list[int],
    frame_selection: FrameSelectionConfig | None,
) -> None:
    if frame_selection is None or frame_selection.target_fps is None:
        return
    stored_fps = _mean_fps(len(timestamps_ns), _duration_s_from_ns(timestamps_ns))
    if stored_fps > 0.0 and frame_selection.target_fps > stored_fps * 1.01:
        warnings.warn(
            "Requested target_fps would require upsampling normalized observations: "
            f"requested={frame_selection.target_fps:.6g}, stored={stored_fps:.6g}. "
            "Using all stored normalized frames instead.",
            RuntimeWarning,
            stacklevel=3,
        )


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


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


def _is_current_schema(entry: NormalizedDatasetEntry, profile: NormalizedDatasetProfile) -> bool:
    return entry.schema_version == STORE_SCHEMA_VERSION and profile.schema_version == STORE_SCHEMA_VERSION


def _validate_current_runtime_entry(entry: NormalizedDatasetEntry) -> None:
    if entry.schema_version != STORE_SCHEMA_VERSION or entry.profile.schema_version != STORE_SCHEMA_VERSION:
        raise RuntimeError(
            "Normalized runtime entries must use the current store schema: "
            f"entry={entry.schema_version}, profile={entry.profile.schema_version}, expected={STORE_SCHEMA_VERSION}."
        )
    if (
        entry.dataset_id is DatasetId.ADVIO
        and entry.profile.source_profile.trajectory_convention != ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION
    ):
        raise RuntimeError(
            "ADVIO normalized runtime entries must use the fixedpoint common-start trajectory convention. "
            "Rebuild this normalized entry."
        )


def _validate_entry_identity_components(*, sequence_id: str, profile_key: str) -> None:
    if sequence_id in {"", ".", ".."} or "/" in sequence_id or "\\" in sequence_id:
        raise ValueError(f"Invalid normalized sequence_id path component: {sequence_id!r}.")
    if not _PROFILE_KEY_PATTERN.fullmatch(profile_key):
        raise ValueError(f"Invalid normalized profile_key: {profile_key!r}.")


def _validate_read_frame_selection(
    entry: NormalizedDatasetEntry,
    frame_selection: FrameSelectionConfig | None,
) -> None:
    if frame_selection is None:
        return
    manifest = rebase_model_paths(
        SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8")),
        root=entry.root,
    )
    if manifest.timestamps_path is not None:
        _validate_requested_target_fps(load_timestamps_ns(manifest.timestamps_path), frame_selection)


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
        manifest.observation_index_path,
        manifest.intrinsics_path,
        manifest.rotation_metadata_path,
    ):
        _ensure_optional_existing_under(root, path)
    if manifest.advio is None:
        return
    _ensure_existing_under(root, manifest.advio.calibration_path)
    if manifest.advio.fixpoints_csv_path is not None or manifest.advio.pose_refs is not None:
        raise RuntimeError("Normalized ADVIO entries must not persist raw pose or fixpoint sidecars.")
    _validate_no_raw_advio_sidecars(root)


def _validate_benchmark_input_paths(root: Path, benchmark_inputs: PreparedBenchmarkInputs) -> None:
    for trajectory in [*benchmark_inputs.reference_trajectories, *benchmark_inputs.candidate_trajectories]:
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
            if row.rgb_path is None:
                raise RuntimeError("Normalized observation rows require rgb_path image payloads.")
            _ensure_optional_existing_under(
                ref.payload_root, _resolve_observation_payload(ref.payload_root, row.rgb_path)
            )
            _ensure_optional_existing_under(
                ref.payload_root,
                _resolve_observation_payload(ref.payload_root, row.depth_path),
            )


def _validate_no_raw_advio_sidecars(root: Path) -> None:
    raw_sidecar_names = {
        "ground_truth_pose.csv",
        "selected_pose.csv",
        "fixpoints.csv",
        "arcore.csv",
        "arkit.csv",
    }
    raw_sidecars = sorted(
        path.relative_to(root).as_posix() for path in root.rglob("*.csv") if path.name in raw_sidecar_names
    )
    if raw_sidecars:
        raise RuntimeError(f"Normalized ADVIO entries must not persist raw pose or fixpoint sidecars: {raw_sidecars}.")


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
    temp_sequence_manifest = rebase_model_paths(
        SequenceManifest.model_validate_json(sequence_manifest_path.read_text(encoding="utf-8")),
        root=old_root,
    )
    temp_benchmark_inputs = rebase_model_paths(
        PreparedBenchmarkInputs.model_validate_json(benchmark_inputs_path.read_text(encoding="utf-8")),
        root=old_root,
    )
    timestamp_metadata = (
        {}
        if temp_sequence_manifest.timestamps_path is None
        else _read_timestamp_metadata(temp_sequence_manifest.timestamps_path)
    )
    sequence_manifest = cast(
        SequenceManifest,
        _rebase_model_paths(temp_sequence_manifest, old_root=old_root, new_root=new_root),
    )
    benchmark_inputs = cast(
        PreparedBenchmarkInputs,
        _rebase_model_paths(temp_benchmark_inputs, old_root=old_root, new_root=new_root),
    )
    entry = cast(
        NormalizedDatasetEntry,
        _rebase_model_paths(
            rebase_model_paths(
                NormalizedDatasetEntry.model_validate_json(entry_path.read_text(encoding="utf-8")),
                root=old_root,
            ),
            old_root=old_root,
            new_root=new_root,
        ),
    )
    profile = entry.profile
    stats_long_path = root / STATS_LONG_FILENAME
    metadata_long_path = root / METADATA_LONG_FILENAME
    _write_analysis_table(
        stats_long_path, STATS_LONG_HEADER, _entry_stats_rows(profile, temp_sequence_manifest, temp_benchmark_inputs)
    )
    _write_analysis_table(
        metadata_long_path,
        METADATA_LONG_HEADER,
        _entry_metadata_rows(
            profile,
            sequence_manifest,
            benchmark_inputs,
            timestamp_metadata=timestamp_metadata,
        ),
    )
    entry = entry.model_copy(
        update={
            "stats_long_path": _rebase_path(stats_long_path, old_root=root, new_root=new_root),
            "metadata_long_path": _rebase_path(metadata_long_path, old_root=root, new_root=new_root),
        }
    )
    write_portable_json(sequence_manifest_path, sequence_manifest, root=new_root)
    write_portable_json(benchmark_inputs_path, benchmark_inputs, root=new_root)
    write_portable_json(entry_path, entry, root=new_root)


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
    return ref.model_copy(
        update={
            "index_path": index_path.resolve(),
            "payload_root": payload_root,
        }
    )


def _normalize_advio_benchmark_inputs(
    benchmark_inputs: PreparedBenchmarkInputs,
    *,
    root: Path,
    sequence_manifest: SequenceManifest,
) -> PreparedBenchmarkInputs:
    from prml_vslam.sources.datasets.advio.advio_fixedpoints import (
        ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
        ADVIO_PROVIDER_WORLD_RDF_FRAMES,
        advio_common_start_local_trajectories,
        apply_advio_fixedpoint_registration,
        estimate_advio_fixedpoint_registration,
        load_advio_fixpoints,
    )

    trajectory_root = root / "benchmark" / "trajectories"
    source_refs = {
        ref.source: ref for ref in benchmark_inputs.reference_trajectories if _is_advio_source_native_trajectory(ref)
    }
    if not source_refs:
        return benchmark_inputs
    if sequence_manifest.advio is None or sequence_manifest.advio.fixpoints_csv_path is None:
        raise RuntimeError("ADVIO fixedpoint-common-start normalization requires manifest ADVIO fixpoints.")
    fixedpoints = load_advio_fixpoints(sequence_manifest.advio.fixpoints_csv_path)
    selected_pose_source = _advio_reference_source_for_serving(sequence_manifest.dataset_serving)
    if ReferenceSource.GROUND_TRUTH not in source_refs:
        raise RuntimeError(
            "ADVIO fixedpoint-common-start normalization requires a source-native ground-truth trajectory."
        )
    registered_trajectories: dict[ReferenceSource, PoseTrajectory3D] = {}
    registrations: dict[ReferenceSource, JsonObject] = {}
    for source, ref in source_refs.items():
        native_frame = ADVIO_PROVIDER_WORLD_RDF_FRAMES[source]
        try:
            source_trajectory = load_tum_trajectory(ref.path, canonicalize_timestamps=True)
            registration = estimate_advio_fixedpoint_registration(
                source_trajectory,
                fixedpoints,
                provider_source=source,
                native_frame=native_frame,
            )
        except ValueError as exc:
            if source in {ReferenceSource.GROUND_TRUTH, selected_pose_source}:
                raise RuntimeError(f"{source.value} ADVIO fixedpoint registration failed.") from exc
            warnings.warn(
                f"Skipping ADVIO {source.value} trajectory because fixedpoint registration failed: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            continue
        registered_trajectories[source] = apply_advio_fixedpoint_registration(source_trajectory, registration)
        registrations[source] = registration.model_dump(mode="json")
    normalized_trajectories, common_start = advio_common_start_local_trajectories(registered_trajectories)
    reference_trajectories = _write_advio_registered_references(
        normalized_trajectories,
        registrations=registrations,
        common_start=common_start,
        target_root=trajectory_root,
    )
    candidate_trajectories = [
        ref for ref in reference_trajectories if ref.source in {ReferenceSource.ARCORE, ReferenceSource.ARKIT}
    ]
    reference_trajectories.extend(
        _advio_aligned_diagnostic_references(reference_trajectories, target_root=trajectory_root)
    )
    observation_sequences = []
    for index, ref in enumerate(benchmark_inputs.observation_sequences):
        target_root = _normalized_observation_sequence_root(
            root=root,
            sequence_count=len(benchmark_inputs.observation_sequences),
            index=index,
        )
        normalized_ref = _normalize_observation_sequence_ref(ref, target_root=target_root)
        normalized_ref = _normalize_advio_observation_sequence_ref(
            normalized_ref,
            pose_source=selected_pose_source,
            normalized_trajectories=normalized_trajectories,
            target_frame=ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
        )
        _remove_staged_observation_sequence(
            source_root=ref.payload_root,
            normalized_root=normalized_ref.payload_root,
            entry_root=root,
        )
        observation_sequences.append(normalized_ref)
    _remove_rebased_benchmark_sources(
        source_inputs=benchmark_inputs,
        kept_paths=_benchmark_artifact_paths([*reference_trajectories, *candidate_trajectories]),
        entry_root=root,
    )
    return benchmark_inputs.model_copy(
        update={
            "reference_trajectories": reference_trajectories,
            "candidate_trajectories": candidate_trajectories,
            "reference_clouds": [],
            "observation_sequences": observation_sequences,
        }
    )


def _is_advio_source_native_trajectory(ref: ReferenceTrajectoryRef) -> bool:
    from prml_vslam.sources.datasets.advio.advio_fixedpoints import ADVIO_PROVIDER_WORLD_RDF_FRAMES

    return (
        ref.coordinate_status is ReferenceCloudCoordinateStatus.SOURCE_NATIVE
        and ref.source in ADVIO_PROVIDER_WORLD_RDF_FRAMES
    )


def _write_advio_registered_references(
    trajectories: dict[ReferenceSource, PoseTrajectory3D],
    *,
    registrations: dict[ReferenceSource, JsonObject],
    common_start: JsonObject,
    target_root: Path,
) -> list[ReferenceTrajectoryRef]:
    from prml_vslam.sources.datasets.advio.advio_fixedpoints import (
        ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
        ADVIO_PROVIDER_WORLD_RDF_FRAMES,
    )

    refs: list[ReferenceTrajectoryRef] = []
    for source in (ReferenceSource.GROUND_TRUTH, ReferenceSource.ARCORE, ReferenceSource.ARKIT):
        trajectory = trajectories.get(source)
        if trajectory is None:
            continue
        path = target_root / f"{source.value}.tum"
        metadata_path = path.with_suffix(".metadata.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        file_interface.write_tum_trajectory_file(path, trajectory)
        write_json(
            metadata_path,
            {
                "source": source.value,
                "target_frame": ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
                "native_frame": ADVIO_PROVIDER_WORLD_RDF_FRAMES[source],
                "coordinate_status": ReferenceCloudCoordinateStatus.REGISTERED.value,
                "trajectory_origin": "advio_fixedpoint_common_start",
                "pose_normalization": "fixedpoint_common_start_local",
                "trajectory_convention": "fixedpoint_common_start_local_rdf_v1",
                "frame_registration": registrations[source],
                "common_start": common_start,
            },
        )
        refs.append(
            ReferenceTrajectoryRef(
                source=source,
                path=path.resolve(),
                target_frame=ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
                native_frame=ADVIO_PROVIDER_WORLD_RDF_FRAMES[source],
                coordinate_status=ReferenceCloudCoordinateStatus.REGISTERED,
                metadata_path=metadata_path.resolve(),
            )
        )
    return refs


def _normalize_advio_observation_sequence_ref(
    ref: ObservationSequenceRef,
    *,
    pose_source: ReferenceSource,
    normalized_trajectories: dict[ReferenceSource, PoseTrajectory3D],
    target_frame: str,
) -> ObservationSequenceRef:
    from prml_vslam.sources.datasets.advio.advio_fixedpoints import advio_frame_transform_from_pose

    trajectory = normalized_trajectories.get(pose_source)
    if trajectory is None:
        return ref
    index = ObservationSequenceIndex.model_validate_json(ref.index_path.read_text(encoding="utf-8"))
    rows = []
    trajectory_timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
    poses = [np.asarray(pose, dtype=np.float64) for pose in trajectory.poses_se3]
    for row in index.rows:
        timestamp_s = row.timestamp_ns / 1e9
        pose_index = int(np.argmin(np.abs(trajectory_timestamps - timestamp_s)))
        T_world_camera = advio_frame_transform_from_pose(poses[pose_index], target_frame=target_frame)
        rows.append(
            row.model_copy(
                update={
                    "T_world_camera": T_world_camera,
                    "provenance": row.provenance.model_copy(
                        update={"pose_source": pose_source.value, "world_frame": target_frame}
                    ),
                }
            )
        )
    normalized_index = index.model_copy(update={"world_frame": target_frame, "rows": rows})
    write_json(ref.index_path, normalized_index)
    return ref.model_copy(update={"world_frame": target_frame})


def _advio_reference_source_for_serving(serving: AdvioServingConfig | None) -> ReferenceSource:
    if serving is None:
        return ReferenceSource.GROUND_TRUTH
    return {
        AdvioPoseSource.GROUND_TRUTH: ReferenceSource.GROUND_TRUTH,
        AdvioPoseSource.ARCORE: ReferenceSource.ARCORE,
        AdvioPoseSource.ARKIT: ReferenceSource.ARKIT,
    }[serving.pose_source]


def _advio_aligned_diagnostic_references(
    source_references: list[ReferenceTrajectoryRef],
    *,
    target_root: Path,
) -> list[ReferenceTrajectoryRef]:
    ground_truth = next(
        (
            ref
            for ref in source_references
            if ref.source is ReferenceSource.GROUND_TRUTH
            and ref.coordinate_status
            in {ReferenceCloudCoordinateStatus.SOURCE_NATIVE, ReferenceCloudCoordinateStatus.REGISTERED}
        ),
        None,
    )
    if ground_truth is None:
        return []
    diagnostics: list[ReferenceTrajectoryRef] = []
    ground_truth_trajectory = load_tum_trajectory(ground_truth.path, canonicalize_timestamps=True)
    for ref in source_references:
        if ref.source not in {ReferenceSource.ARCORE, ReferenceSource.ARKIT}:
            continue
        diagnostic = _advio_aligned_diagnostic_reference(
            ground_truth_ref=ground_truth,
            ground_truth_trajectory=ground_truth_trajectory,
            provider_ref=ref,
            target_root=target_root,
        )
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return diagnostics


def _advio_aligned_diagnostic_reference(
    *,
    ground_truth_ref: ReferenceTrajectoryRef,
    ground_truth_trajectory: PoseTrajectory3D,
    provider_ref: ReferenceTrajectoryRef,
    target_root: Path,
) -> ReferenceTrajectoryRef | None:
    provider_trajectory = load_tum_trajectory(provider_ref.path, canonicalize_timestamps=True)
    try:
        ground_truth_assoc, provider_assoc = sync.associate_trajectories(
            ground_truth_trajectory,
            provider_trajectory,
            max_diff=_ADVIO_ALIGN_MAX_DIFF_S,
        )
    except (ValueError, sync.SyncException):
        return None
    matched_pairs = int(len(ground_truth_assoc.positions_xyz))
    if matched_pairs < _ADVIO_ALIGN_MIN_PAIRS:
        return None
    method = "sim3_umeyama_post_fixedpoint_common_start"
    try:
        rotation, translation, scale = provider_assoc.align(ground_truth_assoc, correct_scale=True)
    except (ValueError, geometry.GeometryException):
        method = "yaw_similarity_umeyama_post_fixedpoint_common_start"
        scale, rotation, translation = yaw_similarity_align(
            np.asarray(provider_assoc.positions_xyz, dtype=np.float64),
            np.asarray(ground_truth_assoc.positions_xyz, dtype=np.float64),
            up_axis=_ADVIO_RDF_DOWN_AXIS,
            correct_scale=True,
        )
        provider_assoc = apply_similarity_to_trajectory(
            provider_assoc,
            scale=float(scale),
            rotation=np.asarray(rotation, dtype=np.float64),
            translation=np.asarray(translation, dtype=np.float64),
        )
    aligned = apply_similarity_to_trajectory(
        provider_trajectory,
        scale=float(scale),
        rotation=np.asarray(rotation, dtype=np.float64),
        translation=np.asarray(translation, dtype=np.float64),
    )
    residual = np.asarray(ground_truth_assoc.positions_xyz, dtype=np.float64) - np.asarray(
        provider_assoc.positions_xyz,
        dtype=np.float64,
    )
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    aligned_path = target_root / f"{provider_ref.source.value}_aligned_to_gt.tum"
    metadata_path = aligned_path.with_suffix(".metadata.json")
    aligned_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(aligned_path, aligned)
    write_json(
        metadata_path,
        {
            "source": provider_ref.source.value,
            "target_frame": ground_truth_ref.target_frame,
            "native_frame": provider_ref.native_frame,
            "coordinate_status": ReferenceCloudCoordinateStatus.ALIGNED.value,
            "trajectory_origin": "advio_fixedpoint_common_start",
            "pose_normalization": "fixedpoint_common_start_local",
            "alignment": {
                "method": method,
                "scale": float(scale),
                "rotation": np.asarray(rotation, dtype=np.float64).tolist(),
                "translation": np.asarray(translation, dtype=np.float64).reshape(3).tolist(),
                "matched_pairs": matched_pairs,
                "rms_error_m": rms_error_m,
                "sync_max_diff_s": _ADVIO_ALIGN_MAX_DIFF_S,
            },
        },
    )
    return ReferenceTrajectoryRef(
        source=provider_ref.source,
        path=aligned_path.resolve(),
        target_frame=ground_truth_ref.target_frame,
        native_frame=provider_ref.native_frame,
        coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
        metadata_path=metadata_path.resolve(),
    )


def _normalize_reference_trajectories(
    trajectories: list[ReferenceTrajectoryRef],
    *,
    target_root: Path,
    copies: dict[Path, Path],
    relative_to_first_pose: bool,
) -> list[ReferenceTrajectoryRef]:
    source_counts: dict[str, int] = {}
    for trajectory in trajectories:
        source_counts[trajectory.source.value] = source_counts.get(trajectory.source.value, 0) + 1
    return [
        _normalize_reference_trajectory(
            trajectory,
            target_root=target_root,
            slug=_trajectory_slug(trajectory, duplicate_source=source_counts[trajectory.source.value] > 1),
            copies=copies,
            relative_to_first_pose=relative_to_first_pose,
        )
        for trajectory in trajectories
    ]


def _normalize_reference_trajectory(
    trajectory: ReferenceTrajectoryRef,
    *,
    target_root: Path,
    slug: str,
    copies: dict[Path, Path],
    relative_to_first_pose: bool,
) -> ReferenceTrajectoryRef:
    target_path = target_root / f"{slug}.tum"
    normalized_path = _normalize_trajectory_once(
        trajectory.path,
        target_path,
        copies,
        target_frame=trajectory.target_frame or "world",
        relative_to_first_pose=relative_to_first_pose,
    )
    metadata_path = target_root / f"{slug}.metadata.json"
    trajectory_origin = "first_pose" if relative_to_first_pose else "dataset_benchmark_frame"
    pose_normalization = "relative_to_first_pose" if relative_to_first_pose else "preserved"
    metadata_payload = {
        "source": trajectory.source.value,
        "target_frame": trajectory.target_frame,
        "native_frame": trajectory.native_frame,
        "coordinate_status": None if trajectory.coordinate_status is None else trajectory.coordinate_status.value,
        "trajectory_origin": trajectory_origin,
        "pose_normalization": pose_normalization,
    }
    if trajectory.metadata_path is not None:
        source_metadata = json.loads(trajectory.metadata_path.read_text(encoding="utf-8"))
        if isinstance(source_metadata, dict):
            metadata_payload = source_metadata | metadata_payload
    write_json(metadata_path, metadata_payload)
    return trajectory.model_copy(update={"path": normalized_path, "metadata_path": metadata_path})


def _normalize_trajectory_once(
    source: Path,
    target: Path,
    copies: dict[Path, Path],
    *,
    target_frame: str,
    relative_to_first_pose: bool,
) -> Path:
    resolved_source = source.resolve()
    if resolved_source not in copies:
        trajectory = load_tum_trajectory(source, canonicalize_timestamps=True)
        if relative_to_first_pose:
            trajectory = trajectory_relative_to_first_pose(trajectory)
        poses = [
            FrameTransform.from_matrix(
                np.asarray(pose, dtype=np.float64),
                target_frame=target_frame,
                source_frame="camera",
            )
            for pose in trajectory.poses_se3
        ]
        copies[resolved_source] = write_tum_trajectory(
            target,
            poses,
            [float(timestamp_s) for timestamp_s in trajectory.timestamps],
        )
    return copies[resolved_source]


def _trajectory_slug(trajectory: ReferenceTrajectoryRef, *, duplicate_source: bool) -> str:
    slug = trajectory.source.value
    if (
        duplicate_source
        and trajectory.coordinate_status is ReferenceCloudCoordinateStatus.ALIGNED
        and trajectory.path.stem.endswith("_aligned_to_gt")
    ):
        return f"{slug}_aligned_to_gt"
    return slug


def _normalize_reference_clouds(
    clouds: list[ReferenceCloudRef],
    *,
    target_root: Path,
) -> list[ReferenceCloudRef]:
    copies: dict[Path, Path] = {}
    normalized = []
    for cloud in clouds:
        slug = cloud.source.value
        normalized.append(
            cloud.model_copy(
                update={
                    "path": _copy_once(cloud.path, target_root / f"{slug}.ply", copies),
                    "metadata_path": _copy_once(cloud.metadata_path, target_root / f"{slug}.metadata.json", copies),
                }
            )
        )
    return normalized


def _remove_rebased_benchmark_sources(
    *,
    source_inputs: PreparedBenchmarkInputs,
    kept_paths: set[Path],
    entry_root: Path,
) -> None:
    for ref in (
        source_inputs.reference_trajectories + source_inputs.candidate_trajectories + source_inputs.reference_clouds
    ):
        for path in (ref.path, ref.metadata_path):
            _remove_rebased_benchmark_path(path, kept_paths=kept_paths, entry_root=entry_root)


def _benchmark_artifact_paths(refs: list[ReferenceTrajectoryRef | ReferenceCloudRef]) -> set[Path]:
    return {path.resolve() for ref in refs for path in (ref.path, ref.metadata_path) if path is not None}


def _remove_rebased_benchmark_path(path: Path | None, *, kept_paths: set[Path], entry_root: Path) -> None:
    if path is None:
        return
    source = path.resolve()
    try:
        source.relative_to(entry_root.resolve())
    except ValueError:
        return
    if source in kept_paths or not source.is_file():
        return
    source.unlink()
    parent = source.parent
    while parent != entry_root and parent.exists():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _copy_once(source: Path, target: Path, copies: dict[Path, Path]) -> Path:
    resolved_source = source.resolve()
    if resolved_source not in copies:
        copies[resolved_source] = _copy_path(source, target)
    return copies[resolved_source]


def _normalize_advio_assets(assets: AdvioManifestAssets, *, input_root: Path) -> AdvioManifestAssets:
    advio_root = input_root / "advio"
    return assets.model_copy(
        update={
            "calibration_path": _copy_path(assets.calibration_path, advio_root / "calibration.yaml"),
            "fixpoints_csv_path": None,
            "pose_refs": None,
        }
    )


def _normalized_observation_sequence_root(*, root: Path, sequence_count: int, index: int) -> Path:
    del index
    if sequence_count != 1:
        raise RuntimeError("Normalized entries must contain exactly one observation sequence.")
    return root / "observations"


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
    selected_indices, _sampling_payload = _selected_indices_and_sampling_payload(timestamps_ns, frame_selection)
    selected_rows = [
        index.rows[source_index].model_copy(update={"seq": seq}) for seq, source_index in enumerate(selected_indices)
    ]
    selected = index.model_copy(update={"rows": selected_rows, "observation_count": len(selected_rows)})
    output_dir.mkdir(parents=True, exist_ok=True)
    index_path = output_dir / f"{ref.source_id}_{ref.sequence_id}_observations.json"
    write_json(index_path, selected)
    return ref.model_copy(update={"index_path": index_path.resolve(), "observation_count": len(selected_rows)})


class NormalizableDatasetSource(OfflineSequenceSource, BenchmarkInputSource, Protocol):
    """Source that can materialize both normalized run input and benchmark sidecars."""

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        """Materialize benchmark inputs required for a normalized-store entry."""
        ...
