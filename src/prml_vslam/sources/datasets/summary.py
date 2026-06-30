"""Dataset-level summaries derived from normalized datastore statistics."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery, query_normalized_dataset
from prml_vslam.utils import BaseData, PathConfig


class DatasetObservationSummary(BaseData):
    """Aggregate observation duration statistics for one normalized dataset."""

    dataset_id: DatasetId
    dataset_label: str
    sequence_count: int
    total_duration_s: float
    average_duration_s: float


def summarize_dataset_observations(
    query: NormalizedDatasetQuery,
    *,
    strict: bool = False,
) -> DatasetObservationSummary:
    """Summarize one normalized dataset using one preferred profile per sequence.

    Args:
        query: Normalized datastore query snapshot.
        strict: Whether missing observation statistics for a preferred sequence
            should fail instead of being skipped.

    Returns:
        Dataset-level observation duration summary.

    Raises:
        RuntimeError: If ``strict`` is set and a preferred sequence/profile has
            no observation statistics.
    """
    observation = query.observation_summary_frame()
    durations_s: list[float] = []
    missing: list[str] = []
    for record in query.scene_sequence_records():
        row = _preferred_observation_row(
            observation,
            sequence_id=record.sequence_id,
            profile_key=record.profile_key,
        )
        if row is None:
            missing.append(f"{record.sequence_id}/{record.profile_key}")
            continue
        durations_s.append(float(pd.to_numeric(row["observation_duration_s"], errors="coerce")))
    if strict and missing:
        raise RuntimeError(
            f"Missing observation statistics for {query.dataset_id.label} normalized sequence(s): {', '.join(missing)}"
        )
    total_duration_s = float(sum(durations_s))
    sequence_count = len(durations_s)
    return DatasetObservationSummary(
        dataset_id=query.dataset_id,
        dataset_label=query.dataset_id.label,
        sequence_count=sequence_count,
        total_duration_s=total_duration_s,
        average_duration_s=0.0 if sequence_count == 0 else total_duration_s / sequence_count,
    )


def build_dataset_observation_summaries(
    path_config: PathConfig,
    *,
    dataset_ids: Sequence[DatasetId] = (DatasetId.ADVIO, DatasetId.TUM_RGBD, DatasetId.RECORD3D),
    strict: bool = False,
) -> list[DatasetObservationSummary]:
    """Build observation summaries for the requested normalized datasets."""
    return [
        summarize_dataset_observations(query_normalized_dataset(dataset_id, path_config), strict=strict)
        for dataset_id in dataset_ids
    ]


def _preferred_observation_row(
    frame: pd.DataFrame,
    *,
    sequence_id: str,
    profile_key: str,
) -> pd.Series | None:
    if frame.empty:
        return None
    selected = frame.loc[
        frame["sequence_id"].astype(str).eq(sequence_id) & frame["profile_key"].astype(str).eq(profile_key)
    ]
    if selected.empty:
        return None
    return selected.iloc[0]


__all__ = [
    "DatasetObservationSummary",
    "build_dataset_observation_summaries",
    "summarize_dataset_observations",
]
