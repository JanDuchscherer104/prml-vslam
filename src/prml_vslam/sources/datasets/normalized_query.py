"""Read-only normalized datastore projections for app and pipeline surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from prml_vslam.sources.datasets.contracts import AdvioPoseSource, DatasetId
from prml_vslam.sources.datasets.normalization import (
    dataset_service,
    normalized_profile_for_dataset,
    normalized_store_for_service,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_store import (
    METADATA_LONG_FILENAME,
    STATS_LONG_FILENAME,
    NormalizedDatasetEntry,
    load_normalized_entry_metadata,
    load_normalized_entry_stats,
    normalized_entry_analysis_summary,
)
from prml_vslam.utils import BaseData, PathConfig


class _SceneLookup(Protocol):
    def scene(self, sequence_id: str) -> object: ...


class NormalizedSequenceRecord(BaseData):
    """One normalized sequence/profile row projected from the datastore."""

    dataset_id: DatasetId
    sequence_id: str
    sequence_label: str
    source_id: str
    profile_key: str
    root: Path
    is_default_profile: bool
    stats_row_count: int
    metadata_row_count: int
    advio_pose_source: AdvioPoseSource | None = None


class NormalizedDatasetQuery(BaseData):
    """Tolerant read-only normalized datastore snapshot for one dataset."""

    dataset_id: DatasetId
    records: list[NormalizedSequenceRecord]
    issues: list[dict[str, str | int | float | bool | None]]
    stats_rows: list[dict[str, str | int | float | bool | None]]
    metadata_rows: list[dict[str, str | int | float | bool | None]]

    @property
    def sequence_ids(self) -> set[str]:
        return {record.sequence_id for record in self.records}

    @property
    def default_profile_sequence_ids(self) -> set[str]:
        return {record.sequence_id for record in self.records if record.is_default_profile}

    @property
    def profile_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.records:
            counts[record.sequence_id] = counts.get(record.sequence_id, 0) + 1
        return counts

    @property
    def default_records(self) -> list[NormalizedSequenceRecord]:
        return [record for record in self.records if record.is_default_profile]

    def records_for_sequence(self, sequence_id: str) -> list[NormalizedSequenceRecord]:
        return [record for record in self.records if record.sequence_id == sequence_id]

    def table_rows(self) -> list[dict[str, str | int | float | bool | None]]:
        counts = self.profile_counts
        return [
            {
                "Dataset": record.dataset_id.label,
                "Sequence": record.sequence_id,
                "Scene": record.sequence_label,
                "Source": record.source_id,
                "Profile": record.profile_key,
                "Default Profile": record.is_default_profile,
                "Profiles": counts[record.sequence_id],
                "Stats Rows": record.stats_row_count,
                "Metadata Rows": record.metadata_row_count,
                "Root": record.root.as_posix(),
            }
            for record in self.records
        ]


def query_normalized_dataset(dataset_id: DatasetId, path_config: PathConfig) -> NormalizedDatasetQuery:
    """Return a tolerant normalized-store snapshot for one dataset."""
    service = dataset_service(dataset_id, path_config)
    store = normalized_store_for_service(dataset_id, path_config)
    entries = store.summary(strict=False)
    default_keys = _default_profile_keys(dataset_id=dataset_id, path_config=path_config, entries=entries)
    records = [
        _record_from_entry(entry, sequence_label=_sequence_label(service, entry.sequence_id), default_keys=default_keys)
        for entry in entries
    ]
    return NormalizedDatasetQuery(
        dataset_id=dataset_id,
        records=records,
        issues=[issue.model_dump(mode="json") for issue in store.issues()],
        stats_rows=[row for entry in entries for row in load_normalized_entry_stats(entry)],
        metadata_rows=[row for entry in entries for row in load_normalized_entry_metadata(entry)],
    )


def normalized_query_fingerprint(path_config: PathConfig, dataset_id: DatasetId) -> tuple[tuple[str, int, int], ...]:
    """Return a Streamlit cache token for normalized entry and analysis files."""
    store_root = path_config.resolve_normalized_datastore_dir(dataset_id.value)
    if not store_root.exists():
        return ()
    paths = sorted(
        path
        for pattern in (
            "*/*/entry.json",
            "*/*/sequence_manifest.json",
            "*/*/benchmark_inputs.json",
            f"*/*/{STATS_LONG_FILENAME}",
            f"*/*/{METADATA_LONG_FILENAME}",
        )
        for path in store_root.glob(pattern)
    )
    return tuple(
        (path.relative_to(store_root).as_posix(), path.stat().st_mtime_ns, path.stat().st_size) for path in paths
    )


def normalized_sequence_options(dataset_id: DatasetId, path_config: PathConfig) -> list[NormalizedSequenceRecord]:
    """Return default-profile sequence records for selector controls."""
    return query_normalized_dataset(dataset_id, path_config).default_records


def resolve_normalized_advio_sequence_id(
    *, sequence_slug: str, path_config: PathConfig
) -> tuple[int | None, str | None]:
    """Resolve an ADVIO slug only if a matching normalized default-profile entry exists."""
    suffix = sequence_slug.split("-", maxsplit=1)[1] if sequence_slug.startswith("advio-") else sequence_slug
    sequence_id = int(suffix) if suffix.isdigit() else None
    if sequence_id is None:
        return None, f"ADVIO sequence '{sequence_slug}' is not a valid ADVIO sequence id."
    query = query_normalized_dataset(DatasetId.ADVIO, path_config)
    canonical = f"advio-{sequence_id:02d}"
    if canonical not in query.default_profile_sequence_ids:
        return None, f"ADVIO sequence '{canonical}' is missing from the normalized datastore."
    return sequence_id, None


def normalized_advio_pose_sources(
    records: Iterable[NormalizedSequenceRecord], *, sequence_id: str
) -> list[AdvioPoseSource]:
    """Return ADVIO pose providers backed by normalized entries for one sequence."""
    providers = [
        record.advio_pose_source
        for record in records
        if record.sequence_id == sequence_id and record.advio_pose_source is not None
    ]
    unique = list(dict.fromkeys(providers))
    return unique or [AdvioPoseSource.GROUND_TRUTH]


def _record_from_entry(
    entry: NormalizedDatasetEntry,
    *,
    sequence_label: str,
    default_keys: set[tuple[str, str]],
) -> NormalizedSequenceRecord:
    analysis = normalized_entry_analysis_summary(entry)
    return NormalizedSequenceRecord(
        dataset_id=entry.dataset_id,
        sequence_id=entry.sequence_id,
        sequence_label=sequence_label,
        source_id=entry.source_id,
        profile_key=entry.profile_key,
        root=entry.root,
        is_default_profile=(entry.sequence_id, entry.profile_key) in default_keys,
        stats_row_count=int(analysis["stats_long_row_count"]),
        metadata_row_count=int(analysis["metadata_long_row_count"]),
        advio_pose_source=_advio_pose_source(entry),
    )


def _default_profile_keys(
    *,
    dataset_id: DatasetId,
    path_config: PathConfig,
    entries: list[NormalizedDatasetEntry],
) -> set[tuple[str, str]]:
    service = dataset_service(dataset_id, path_config)
    keys: set[tuple[str, str]] = set()
    for entry in entries:
        source_config = source_config_for_normalization(dataset_id=dataset_id, sequence_id=entry.sequence_id)
        profile = normalized_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source_config)
        if entry.profile_key == profile.profile_key:
            keys.add((entry.sequence_id, entry.profile_key))
    return keys


def _sequence_label(service: _SceneLookup, sequence_id: str) -> str:
    try:
        scene = service.scene(sequence_id)
    except (AttributeError, KeyError, RuntimeError, ValueError):
        return sequence_id
    return str(getattr(scene, "display_name", sequence_id))


def _advio_pose_source(entry: NormalizedDatasetEntry) -> AdvioPoseSource | None:
    if entry.dataset_id is not DatasetId.ADVIO:
        return None
    source_profile = entry.profile.get("source_profile", {})
    serving = source_profile.get("dataset_serving", {}) if isinstance(source_profile, dict) else {}
    pose_source = serving.get("pose_source") if isinstance(serving, dict) else None
    try:
        return AdvioPoseSource(pose_source) if pose_source is not None else AdvioPoseSource.GROUND_TRUTH
    except ValueError:
        return AdvioPoseSource.GROUND_TRUTH
