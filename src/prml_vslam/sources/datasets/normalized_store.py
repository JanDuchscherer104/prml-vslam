"""Persistent normalized dataset entries for offline dataset-backed sources."""

from __future__ import annotations

import shutil
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, ObservationSequenceIndex, ObservationSequenceRef
from prml_vslam.sources.contracts import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.sources.datasets.normalized_tables import (
    load_depth_array,
    load_timestamps_ns,
    metadata_rows,
    statistics_rows,
    write_long_csv,
)
from prml_vslam.sources.observation_sequence import load_observation_sequence_index
from prml_vslam.sources.protocols import BenchmarkInputSource, OfflineSequenceSource
from prml_vslam.sources.replay import ImageSequenceObservationSource, ObservationStream, ReplayMode
from prml_vslam.utils import BaseData, JsonObject, JsonValue
from prml_vslam.utils.serialization import stable_hash, write_json
from prml_vslam.utils.video_frames import extract_video_frames

ENTRY_FILENAME = "entry.json"
SEQUENCE_MANIFEST_FILENAME = "sequence_manifest.json"
BENCHMARK_INPUTS_FILENAME = "benchmark_inputs.json"
STATS_LONG_FILENAME = "stats_long.csv"
METADATA_LONG_FILENAME = "metadata_long.csv"
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
    stats_long_csv_path: Path | None = None
    metadata_long_csv_path: Path | None = None
    created_at_ns: int = Field(default_factory=time.time_ns)


class NormalizedDatasetStore:
    """Filesystem store for reusable full-frame normalized dataset payloads."""

    def __init__(self, *, dataset_root: Path, dataset_id: DatasetId) -> None:
        self.dataset_root = dataset_root.resolve()
        self.dataset_id = dataset_id
        self.store_root = self.dataset_root / ".normalized"

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
        dataset_arg = "record3d" if profile.dataset_id is DatasetId.RECORD3D else profile.dataset_id.value
        return (
            "Missing normalized dataset entry "
            f"dataset_id={profile.dataset_id.value} sequence_id={profile.sequence_id} "
            f"profile_key={profile.profile_key}. Run: prml-vslam dataset normalize "
            f"--dataset {dataset_arg} --sequence {profile.sequence_id}"
        )

    def create_entry(
        self,
        *,
        profile: NormalizedDatasetProfile,
        sequence_manifest: SequenceManifest,
        benchmark_inputs: PreparedBenchmarkInputs,
    ) -> NormalizedDatasetEntry:
        """Persist one full-frame normalized entry."""
        root = self.entry_root(profile).resolve()
        root.mkdir(parents=True, exist_ok=True)
        benchmark_inputs = self._normalize_benchmark_inputs(benchmark_inputs, root=root)
        sequence_manifest = self._normalize_sequence_manifest(
            sequence_manifest,
            benchmark_inputs=benchmark_inputs,
            input_root=root / "input",
        )
        sequence_manifest_path = root / SEQUENCE_MANIFEST_FILENAME
        benchmark_inputs_path = root / BENCHMARK_INPUTS_FILENAME
        stats_long_csv_path = root / STATS_LONG_FILENAME
        metadata_long_csv_path = root / METADATA_LONG_FILENAME
        write_json(sequence_manifest_path, sequence_manifest)
        write_json(benchmark_inputs_path, benchmark_inputs)
        write_long_csv(
            stats_long_csv_path,
            statistics_rows(
                sequence_manifest=sequence_manifest, benchmark_inputs=benchmark_inputs, profile_key=profile.profile_key
            ),
        )
        write_long_csv(
            metadata_long_csv_path,
            metadata_rows(
                sequence_manifest=sequence_manifest, benchmark_inputs=benchmark_inputs, profile_key=profile.profile_key
            ),
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
            stats_long_csv_path=stats_long_csv_path,
            metadata_long_csv_path=metadata_long_csv_path,
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
        entry_root = self.entry_root(profile)
        return self.create_entry(
            profile=profile,
            sequence_manifest=source.prepare_sequence_manifest(entry_root / "input"),
            benchmark_inputs=source.prepare_benchmark_inputs(entry_root / "benchmark"),
        )

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
            write_json(timestamps_path, {"timestamps_ns": extracted.timestamps_ns})
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


def _validate_entry_paths(entry: NormalizedDatasetEntry) -> None:
    _ensure_under(entry.root, entry.sequence_manifest_path)
    _ensure_under(entry.root, entry.benchmark_inputs_path)
    if entry.stats_long_csv_path is None or entry.metadata_long_csv_path is None:
        raise RuntimeError("Current normalized entries must include stats_long and metadata_long CSV paths.")
    _ensure_existing_under(entry.root, entry.stats_long_csv_path)
    _ensure_existing_under(entry.root, entry.metadata_long_csv_path)


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
        updates["intrinsics_path"] = _write_intrinsics_yaml(first_intrinsics, input_root / "intrinsics.yaml")
    return manifest.model_copy(update=updates)


def _write_intrinsics_yaml(intrinsics: CameraIntrinsics, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        "cameras:",
        "- camera:",
        f"    image_height: {intrinsics.height_px or 0}",
        f"    image_width: {intrinsics.width_px or 0}",
        "    type: pinhole",
        "    intrinsics:",
        f"      data: [{intrinsics.fx:.8g}, {intrinsics.fy:.8g}, {intrinsics.cx:.8g}, {intrinsics.cy:.8g}]",
        "    distortion:",
        "      type: none",
        "      parameters:",
        "        data: []",
        "    T_cam_imu:",
        "      data:",
        "      - [1.0, 0.0, 0.0, 0.0]",
        "      - [0.0, 1.0, 0.0, 0.0]",
        "      - [0.0, 0.0, 1.0, 0.0]",
        "      - [0.0, 0.0, 0.0, 1.0]",
    ]
    target_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return target_path.resolve()


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
