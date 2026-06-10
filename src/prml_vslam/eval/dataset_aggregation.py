"""Pure aggregation functions for dataset-wide trajectory metric review.

No I/O — all functions transform pre-loaded ``DatasetEvaluationSelection``
objects into tables and plot-ready data structures.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from evo.core import metrics

from prml_vslam.eval.query import DatasetEvaluationSelection, DatasetRunCoverage
from prml_vslam.utils import BaseData


@dataclass(frozen=True, slots=True)
class MetricFilter:
    """Selector for a specific metric family / pose-relation / statistic combination."""

    metric_family: Literal["ape", "rpe"] = "ape"
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part
    statistic: str = "rmse"
    delta: float | None = None
    delta_unit: str | None = None


class PerSequenceRow(BaseData):
    """One filtered metric value for a single sequence and estimate source."""

    sequence_id: str
    estimate_source_base: str
    """Base method name extracted from ``estimate_source``, e.g. ``vista``."""

    coordinate_status: str
    """Coordinate status extracted from ``estimate_source``, e.g. ``raw``."""

    method: str | None = None
    """Known benchmark method id inferred from the run artifact path."""

    metric_family: Literal["ape", "rpe"]
    pose_relation: metrics.PoseRelation
    statistic: str
    value: float
    unit: str | None = None
    matched_pairs: int
    delta: float | None = None
    delta_unit: str | None = None


class LeaderboardRow(BaseData):
    """Aggregated metric summary across all sequences for one estimate source."""

    estimate_source_base: str
    coordinate_status: str
    metric_family: Literal["ape", "rpe"]
    pose_relation: metrics.PoseRelation
    statistic: str
    unit: str | None = None
    mean: float
    median: float
    std: float
    n_sequences: int
    """Number of sequences contributing at least one value to this row."""

    n_total_sequences: int
    """Total sequences registered in the dataset (from the sequence registry)."""


@dataclass(slots=True)
class CoverageCell:
    """Coverage state for one (sequence, method) cell in the coverage matrix."""

    sequence_id: str
    method: str | None
    manifest_present: bool
    metric_row_count: int


@dataclass(slots=True)
class CoverageMatrix:
    """Rectangular coverage grid for all sequences × all discovered methods."""

    sequence_ids: list[str]
    methods: list[str | None]
    cells: list[CoverageCell] = field(default_factory=list)


@dataclass(slots=True)
class HeatmapData:
    """Metric values for a heatmap of sequences × estimate sources."""

    sequence_ids: list[str]
    estimate_sources: list[str]
    values: list[list[float | None]]
    metric_name: str


def build_per_sequence_table(
    selection: DatasetEvaluationSelection,
    metric_filter: MetricFilter,
) -> list[PerSequenceRow]:
    """Return one row per metric row matching *metric_filter* across all discovered runs."""
    method_by_run_id: dict[str, str | None] = {c.run_id: c.method for c in selection.coverage}
    result: list[PerSequenceRow] = []
    for row in selection.metric_rows:
        if row.metric_family != metric_filter.metric_family:
            continue
        if row.pose_relation is not metric_filter.pose_relation:
            continue
        if row.statistic != metric_filter.statistic:
            continue
        if metric_filter.delta is not None and row.delta != metric_filter.delta:
            continue
        if metric_filter.delta_unit is not None and row.delta_unit != metric_filter.delta_unit:
            continue
        base, _, status = row.estimate_source.partition("/")
        result.append(
            PerSequenceRow(
                sequence_id=row.sequence_id,
                estimate_source_base=base,
                coordinate_status=status if status else "raw",
                method=method_by_run_id.get(row.run_id),
                metric_family=row.metric_family,
                pose_relation=row.pose_relation,
                statistic=row.statistic,
                value=row.value,
                unit=row.unit,
                matched_pairs=row.matched_pairs,
                delta=row.delta,
                delta_unit=row.delta_unit,
            )
        )
    return result


def build_leaderboard(
    rows: list[PerSequenceRow],
    n_total_sequences: int,
) -> list[LeaderboardRow]:
    """Aggregate per-sequence rows into a leaderboard ranked by mean value."""
    GroupKey = tuple[str, str, str, metrics.PoseRelation, str]
    groups: dict[GroupKey, list[float]] = defaultdict(list)
    units: dict[GroupKey, str | None] = {}

    for row in rows:
        key: GroupKey = (
            row.estimate_source_base,
            row.coordinate_status,
            row.metric_family,
            row.pose_relation,
            row.statistic,
        )
        groups[key].append(row.value)
        units[key] = row.unit

    result: list[LeaderboardRow] = []
    for key, values in groups.items():
        estimate_source_base, coordinate_status, metric_family, pose_relation, statistic = key
        result.append(
            LeaderboardRow(
                estimate_source_base=estimate_source_base,
                coordinate_status=coordinate_status,
                metric_family=metric_family,
                pose_relation=pose_relation,
                statistic=statistic,
                unit=units[key],
                mean=statistics.mean(values),
                median=statistics.median(values),
                std=statistics.stdev(values) if len(values) > 1 else 0.0,
                n_sequences=len(values),
                n_total_sequences=n_total_sequences,
            )
        )
    result.sort(key=lambda r: r.mean)
    return result


def build_coverage_matrix(selection: DatasetEvaluationSelection) -> CoverageMatrix:
    """Build a coverage grid for all sequences × discovered methods."""
    all_methods: list[str | None] = sorted(
        {c.method for c in selection.coverage},
        key=lambda m: m or "",
    )
    cell_map: dict[tuple[str, str | None], DatasetRunCoverage] = {}
    for cov in selection.coverage:
        key = (cov.sequence_id, cov.method)
        existing = cell_map.get(key)
        if existing is None or cov.manifest_present:
            cell_map[key] = cov

    cells = [
        CoverageCell(
            sequence_id=seq_id,
            method=method,
            manifest_present=cell_map[(seq_id, method)].manifest_present if (seq_id, method) in cell_map else False,
            metric_row_count=cell_map[(seq_id, method)].metric_row_count if (seq_id, method) in cell_map else 0,
        )
        for seq_id in selection.all_sequence_ids
        for method in all_methods
    ]
    return CoverageMatrix(
        sequence_ids=list(selection.all_sequence_ids),
        methods=all_methods,
        cells=cells,
    )


def build_heatmap_data(
    rows: list[PerSequenceRow],
    all_sequence_ids: list[str],
    metric_name: str = "APE RMSE (m)",
) -> HeatmapData:
    """Build a heatmap matrix of values indexed by sequence × estimate source."""
    estimate_sources = sorted({f"{r.estimate_source_base}/{r.coordinate_status}" for r in rows})
    value_map: dict[tuple[str, str], float] = {
        (r.sequence_id, f"{r.estimate_source_base}/{r.coordinate_status}"): r.value for r in rows
    }
    values: list[list[float | None]] = [
        [value_map.get((seq_id, src)) for src in estimate_sources] for seq_id in all_sequence_ids
    ]
    return HeatmapData(
        sequence_ids=list(all_sequence_ids),
        estimate_sources=estimate_sources,
        values=values,
        metric_name=metric_name,
    )


__all__ = [
    "CoverageCell",
    "CoverageMatrix",
    "HeatmapData",
    "LeaderboardRow",
    "MetricFilter",
    "PerSequenceRow",
    "build_coverage_matrix",
    "build_heatmap_data",
    "build_leaderboard",
    "build_per_sequence_table",
]
