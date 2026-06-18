"""Read-only normalized datastore projections for app and pipeline surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

import pandas as pd

from prml_vslam.sources.datasets.contracts import AdvioPoseSource, DatasetId
from prml_vslam.sources.datasets.normalization import (
    dataset_service,
    normalized_profile_for_dataset,
    normalized_store_for_service,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_store import (
    METADATA_LONG_FILENAME,
    METADATA_LONG_HEADER,
    STATS_LONG_FILENAME,
    STATS_LONG_HEADER,
    NormalizedDatasetEntry,
    load_normalized_entry_metadata_table,
    load_normalized_entry_stats_table,
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
    stats_df: pd.DataFrame
    metadata_df: pd.DataFrame

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

    def entry_frame(self) -> pd.DataFrame:
        """Return one dataframe row per usable normalized entry."""
        return pd.DataFrame.from_records(self.table_rows())

    def filtered_stats_frame(
        self,
        *,
        sequence_ids: list[str] | None = None,
        scopes: list[str] | None = None,
        stats: list[str] | None = None,
    ) -> pd.DataFrame:
        """Return the canonical long stats table after UI-selected categorical filters."""
        frame = self.stats_df
        if frame.empty:
            return frame
        mask = pd.Series(True, index=frame.index)
        if sequence_ids:
            mask &= frame["sequence_id"].isin(sequence_ids)
        if scopes:
            mask &= frame["scope"].isin(scopes)
        if stats:
            mask &= frame["stat"].isin(stats)
        return frame.loc[mask].reset_index(drop=True)

    def observation_summary_frame(self) -> pd.DataFrame:
        """Return compact observation count, duration, and FPS statistics."""
        return _pivot_stats(
            self.stats_df,
            scope="observation_sequence",
            stats=(
                "observation_frame_count",
                "rgb_frame_count",
                "depth_frame_count",
                "observation_duration_s",
                "observation_mean_fps",
            ),
        )

    def trajectory_summary_frame(self) -> pd.DataFrame:
        """Return compact trajectory motion statistics for reference/candidate rows."""
        frame = self.stats_df
        if frame.empty:
            return pd.DataFrame()
        selected = frame.loc[
            frame["scope"].isin(["reference_trajectory", "candidate_trajectory"])
            & frame["stat"].isin(
                [
                    "trajectory_pose_count",
                    "trajectory_duration_s",
                    "trajectory_path_length_m",
                    "trajectory_mean_speed_m_s",
                    "trajectory_mean_curvature_rad_m",
                    "ego_motion_class",
                ]
            )
        ]
        return _pivot_stats(selected, scope=None, stats=())

    def payload_footprint_frame(self) -> pd.DataFrame:
        """Return stored RGB/depth/video footprint by normalized entry."""
        rows: list[dict[str, str | int | float | bool | None]] = []
        for record in self.records:
            observations_root = record.root / "observations"
            rgb_bytes = _sum_payload_bytes(observations_root / "rgb", "*.png")
            depth_bytes = _sum_payload_bytes(observations_root / "depth", "*.png")
            video_bytes = sum(
                path.stat().st_size
                for path in (observations_root / filename for filename in ("rgb.mp4", "rgb.mov", "rgb.m4v"))
                if path.is_file()
            )
            rows.append(
                {
                    "Dataset": record.dataset_id.label,
                    "Sequence": record.sequence_id,
                    "Profile": record.profile_key,
                    "RGB MB": round(rgb_bytes / 1_000_000, 3),
                    "Depth MB": round(depth_bytes / 1_000_000, 3),
                    "Video MB": round(video_bytes / 1_000_000, 3),
                    "Total MB": round((rgb_bytes + depth_bytes + video_bytes) / 1_000_000, 3),
                }
            )
        return pd.DataFrame.from_records(rows)


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
        stats_df=_concat_analysis_tables(
            [load_normalized_entry_stats_table(entry) for entry in entries], columns=STATS_LONG_HEADER
        ),
        metadata_df=_concat_analysis_tables(
            [load_normalized_entry_metadata_table(entry) for entry in entries], columns=METADATA_LONG_HEADER
        ),
    )


def _concat_analysis_tables(tables: list[pd.DataFrame], *, columns: tuple[str, ...]) -> pd.DataFrame:
    if not tables:
        return pd.DataFrame(columns=columns)
    table = pd.concat(tables, ignore_index=True)
    return table if not table.empty else pd.DataFrame(columns=columns)


def _pivot_stats(stats_df: pd.DataFrame, *, scope: str | None, stats: tuple[str, ...]) -> pd.DataFrame:
    if stats_df.empty:
        return pd.DataFrame()
    frame = stats_df
    if scope is not None:
        frame = frame.loc[frame["scope"].eq(scope)]
    if stats:
        frame = frame.loc[frame["stat"].isin(stats)]
    if frame.empty:
        return pd.DataFrame()
    return (
        frame.pivot_table(
            index=["dataset_id", "sequence_id", "profile_key", "source_id", "scope", "subject"],
            columns="stat",
            values="value",
            aggfunc="first",
        )
        .reset_index()
        .rename_axis(columns=None)
    )


def _sum_payload_bytes(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(path.stat().st_size for path in root.glob(pattern) if path.is_file())


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
        profile = normalized_profile_for_dataset(
            dataset_id=dataset_id,
            service=service,
            source_config=source_config,
            include_frame_selection=True,
        )
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
