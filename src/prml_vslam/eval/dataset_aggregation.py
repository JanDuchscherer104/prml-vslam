"""Pure aggregation functions for dataset-wide trajectory metric review.

No I/O — all functions transform pre-loaded ``DatasetEvaluationSelection``
objects into tables and plot-ready data structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np
import pandas as pd
from evo.core import metrics

from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow
from prml_vslam.utils import BaseData

if TYPE_CHECKING:
    from prml_vslam.eval.query import DatasetEvaluationSelection

WideMetricRow = dict[str, str | float | int | None]
MetricKey = tuple[str, metrics.PoseRelation, str]

_METRIC_ROW_COLUMNS = list(TrajectoryMetricResultRow.model_fields)
_METRIC_COLUMNS = {
    ("ape", "translation_part"): "APE Trans. RMSE (m)",
    ("ape", "rotation_angle_deg"): "APE Rot. RMSE (deg)",
    ("rpe", "translation_part"): "RPE Trans. RMSE (m)",
    ("rpe", "rotation_angle_deg"): "RPE Rot. RMSE (deg)",
}
_PAIR_COLUMNS = {"ape": "APE Pairs", "rpe": "RPE Pairs"}


@dataclass(frozen=True, slots=True)
class MetricFilter:
    """Selector for a specific metric family / pose-relation / statistic combination."""

    metric_family: Literal["ape", "rpe"] = "ape"
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part
    statistic: str = "rmse"
    delta: float | None = None
    delta_unit: str | None = None


class PerSequenceRow(BaseData):
    """One filtered metric value for a single sequence, run, and estimate source."""

    sequence_id: str
    run_id: str
    """Stable run identifier — preserved so duplicate runs on the same sequence are distinguishable."""

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


def metric_rows_to_frame(rows: list[TrajectoryMetricResultRow]) -> pd.DataFrame:
    """Convert typed metric rows into the canonical long-form table."""
    return pd.DataFrame.from_records(
        (row.model_dump(mode="json") for row in rows),
        columns=_METRIC_ROW_COLUMNS,
    )


def metric_frame_to_rows(frame: pd.DataFrame) -> list[TrajectoryMetricResultRow]:
    """Validate a metric table back into typed long-form rows."""
    if frame.empty:
        return []
    table = frame.reindex(columns=_METRIC_ROW_COLUMNS).assign(
        pose_relation=lambda df: df["pose_relation"].map(_pose_relation_value),
        unit=lambda df: df["unit"].replace("", None),
        delta_unit=lambda df: df["delta_unit"].replace("", None),
        error_series_path=lambda df: df["error_series_path"].replace("", None),
    )
    return [TrajectoryMetricResultRow.model_validate(record) for record in _clean_records(table)]


def available_metric_keys(rows: list[TrajectoryMetricResultRow]) -> list[MetricKey]:
    """Return available metric selectors with RMSE defaults first."""
    frame = _metric_frame_with_pose_names(rows)
    if frame.empty:
        return []
    keys = (
        frame[["metric_family", "pose_relation_name", "statistic"]]
        .drop_duplicates()
        .assign(sort_stat=lambda df: df["statistic"].ne("rmse"))
        .sort_values(["sort_stat", "metric_family", "pose_relation_name", "statistic"])
    )
    return [
        (str(row.metric_family), metrics.PoseRelation[str(row.pose_relation_name)], str(row.statistic))
        for row in keys.itertuples(index=False)
    ]


def filter_metric_rows(
    rows: list[TrajectoryMetricResultRow],
    *,
    references: list[str] | None = None,
    estimates: list[str] | None = None,
) -> list[TrajectoryMetricResultRow]:
    """Filter metric rows by page-selected reference and estimate labels."""
    frame = _metric_frame_with_estimate_parts(rows)
    if frame.empty:
        return []
    filtered = frame.loc[
        frame["reference_source"].isin(references if references is not None else frame["reference_source"])
        & frame["estimate_source_base"].isin(estimates if estimates is not None else frame["estimate_source_base"])
    ]
    return metric_frame_to_rows(filtered)


def build_per_sequence_table(
    selection: DatasetEvaluationSelection,
    metric_filter: MetricFilter,
) -> list[PerSequenceRow]:
    """Return one row per metric row matching *metric_filter* across all discovered runs."""
    frame = _metric_frame_with_estimate_parts(selection.metric_rows)
    if frame.empty:
        return []
    mask = (
        frame["metric_family"].eq(metric_filter.metric_family)
        & frame["pose_relation_name"].eq(metric_filter.pose_relation.name)
        & frame["statistic"].eq(metric_filter.statistic)
    )
    if metric_filter.delta is not None:
        mask &= frame["delta"].eq(metric_filter.delta)
    if metric_filter.delta_unit is not None:
        mask &= frame["delta_unit"].eq(metric_filter.delta_unit)
    coverage = pd.DataFrame.from_records(
        (coverage.model_dump(mode="python") for coverage in selection.coverage),
        columns=["run_id", "method"],
    ).drop_duplicates("run_id")
    table = (
        frame.loc[mask]
        .merge(coverage, on="run_id", how="left")
        .assign(
            pose_relation=lambda df: df["pose_relation_name"].map(metrics.PoseRelation.__getitem__),
            method=lambda df: df["method"].replace({np.nan: None}),
        )
    )
    return [
        PerSequenceRow.model_validate(record) for record in _clean_records(table[list(PerSequenceRow.model_fields)])
    ]


def build_leaderboard(
    rows: list[PerSequenceRow],
    n_total_sequences: int,
) -> list[LeaderboardRow]:
    """Aggregate per-sequence rows into a leaderboard ranked by mean value.

    Multiple runs on the same sequence are averaged first so each sequence
    contributes exactly one value per source/metric combination.
    """
    frame = _per_sequence_rows_to_frame(rows)
    if frame.empty:
        return []
    group_cols = ["estimate_source_base", "coordinate_status", "metric_family", "pose_relation_name", "statistic"]
    summary = (
        frame.groupby(["sequence_id", *group_cols], dropna=False, as_index=False)
        .agg(value=("value", "mean"), unit=("unit", "first"))
        .groupby(group_cols, dropna=False, as_index=False)
        .agg(
            mean=("value", "mean"),
            median=("value", "median"),
            std=("value", lambda s: float(s.std(ddof=1)) if len(s) > 1 else 0.0),
            n_sequences=("value", "count"),
            unit=("unit", "first"),
        )
        .sort_values("mean")
    )
    records = summary.assign(
        pose_relation=lambda df: df["pose_relation_name"].map(metrics.PoseRelation.__getitem__),
        n_total_sequences=n_total_sequences,
    ).drop(columns="pose_relation_name")
    return [LeaderboardRow.model_validate(record) for record in _clean_records(records)]


def build_coverage_matrix(selection: DatasetEvaluationSelection) -> CoverageMatrix:
    """Build a coverage grid for all sequences × discovered methods."""
    coverage = pd.DataFrame.from_records(
        (item.model_dump(mode="python") for item in selection.coverage),
        columns=["sequence_id", "method", "manifest_present", "metric_row_count"],
    )
    methods = sorted(coverage["method"].drop_duplicates().tolist(), key=lambda method: method or "")
    if coverage.empty or not methods:
        cells: list[CoverageCell] = []
    else:
        cells_frame = (
            coverage.sort_values("manifest_present")
            .drop_duplicates(["sequence_id", "method"], keep="last")
            .set_index(["sequence_id", "method"])
            .reindex(pd.MultiIndex.from_product([selection.all_sequence_ids, methods], names=["sequence_id", "method"]))
            .reset_index()
            .assign(
                manifest_present=lambda df: df["manifest_present"]
                .where(df["manifest_present"].notna(), False)
                .astype(bool),
                metric_row_count=lambda df: df["metric_row_count"].where(df["metric_row_count"].notna(), 0).astype(int),
            )
        )
        cells = [CoverageCell(**record) for record in _clean_records(cells_frame)]
    return CoverageMatrix(
        sequence_ids=list(selection.all_sequence_ids),
        methods=methods,
        cells=cells,
    )


def build_heatmap_data(
    rows: list[PerSequenceRow],
    all_sequence_ids: list[str],
    metric_name: str = "APE RMSE (m)",
) -> HeatmapData:
    """Build a heatmap matrix of values indexed by sequence × estimate source.

    Multiple runs on the same (sequence, source) cell are averaged so no run
    silently overwrites another.
    """
    frame = _per_sequence_rows_to_frame(rows)
    if frame.empty:
        estimate_sources: list[str] = []
        values: list[list[float | None]] = [[] for _ in all_sequence_ids]
    else:
        pivot = (
            frame.assign(estimate_source=lambda df: df["estimate_source_base"] + "/" + df["coordinate_status"])
            .pivot_table(index="sequence_id", columns="estimate_source", values="value", aggfunc="mean")
            .reindex(index=all_sequence_ids)
            .sort_index(axis=1)
        )
        estimate_sources = [str(col) for col in pivot.columns]
        values = pivot.replace({np.nan: None}).values.tolist()
    return HeatmapData(
        sequence_ids=list(all_sequence_ids),
        estimate_sources=estimate_sources,
        values=values,
        metric_name=metric_name,
    )


def build_wide_metric_rows(rows: list[TrajectoryMetricResultRow], *, statistic: str = "rmse") -> list[WideMetricRow]:
    """Pivot long-format metric rows into one wide row per sequence/run/reference/estimate/status."""
    value_labels = _wide_metric_columns_for(statistic)
    frame = (
        _metric_frame_with_estimate_parts(rows)
        .loc[lambda df: df["statistic"].eq(statistic)]
        .assign(
            metric_column=lambda df: pd.Series(
                zip(df["metric_family"], df["pose_relation_name"], strict=False), index=df.index
            ).map(value_labels)
        )
        .dropna(subset=["metric_column"])
    )
    if frame.empty:
        return []
    index_cols = ["sequence_id", "run_id", "reference_source", "estimate_source_base", "coordinate_status"]
    value_cols = list(value_labels.values())
    sequence_rows = (
        frame.pivot_table(index=index_cols, columns="metric_column", values="value", aggfunc="mean")
        .reindex(columns=value_cols)
        .round(4)
        .join(
            frame.assign(pair_column=lambda df: df["metric_family"].map(_PAIR_COLUMNS))
            .pivot_table(index=index_cols, columns="pair_column", values="matched_pairs", aggfunc="max")
            .reindex(columns=list(_PAIR_COLUMNS.values()))
        )
        .reset_index()
        .rename(columns=_WIDE_RENAME)
    )
    table = pd.concat(
        [sequence_rows, _build_rmse_aggregate_rows(frame, value_cols) if statistic == "rmse" else pd.DataFrame()],
        ignore_index=True,
    )
    return _wide_frame_to_rows(table, statistic=statistic)


_WIDE_RENAME = {
    "sequence_id": "Sequence",
    "run_id": "Run",
    "reference_source": "Reference",
    "estimate_source_base": "Estimate",
    "coordinate_status": "Coordinate Status",
}


def _build_rmse_aggregate_rows(frame: pd.DataFrame, value_cols: list[str]) -> pd.DataFrame:
    index_cols = ["run_id", "reference_source", "estimate_source_base", "coordinate_status"]
    pooled = (
        frame.assign(weighted_square=lambda df: df["matched_pairs"] * df["value"].pow(2))
        .groupby([*index_cols, "metric_column"], as_index=False)
        .agg(weighted_square=("weighted_square", "sum"), matched_pairs=("matched_pairs", "sum"))
        .assign(value=lambda df: np.sqrt(df["weighted_square"] / df["matched_pairs"]).round(4))
        .pivot_table(index=index_cols, columns="metric_column", values="value", aggfunc="first")
        .reindex(columns=value_cols)
    )
    pairs = (
        frame.assign(pair_column=lambda df: df["metric_family"].map(_PAIR_COLUMNS))
        .groupby([*index_cols, "metric_family", "sequence_id"], as_index=False)
        .agg(matched_pairs=("matched_pairs", "max"))
        .groupby([*index_cols, "metric_family"], as_index=False)
        .agg(matched_pairs=("matched_pairs", "sum"))
        .assign(pair_column=lambda df: df["metric_family"].map(_PAIR_COLUMNS))
        .pivot_table(index=index_cols, columns="pair_column", values="matched_pairs", aggfunc="first")
        .reindex(columns=list(_PAIR_COLUMNS.values()))
    )
    return pooled.join(pairs).reset_index().rename(columns=_WIDE_RENAME).assign(Sequence="All sequences")


def _wide_frame_to_rows(frame: pd.DataFrame, *, statistic: str) -> list[WideMetricRow]:
    columns = [
        "Sequence",
        "Run",
        "Reference",
        "Estimate",
        "Coordinate Status",
        *_wide_metric_columns_for(statistic).values(),
        *list(_PAIR_COLUMNS.values()),
    ]
    table = (
        frame.reindex(columns=columns)
        .assign(_aggregate=lambda df: df["Sequence"].eq("All sequences"))
        .sort_values(["Run", "Reference", "Estimate", "Coordinate Status", "_aggregate", "Sequence"], kind="stable")
        .drop(columns="_aggregate")
    )
    return _clean_records(table)


def _metric_frame_with_pose_names(rows: list[TrajectoryMetricResultRow]) -> pd.DataFrame:
    return metric_rows_to_frame(rows).assign(pose_relation_name=lambda df: df["pose_relation"].map(_pose_relation_name))


def _metric_frame_with_estimate_parts(rows: list[TrajectoryMetricResultRow]) -> pd.DataFrame:
    frame = _metric_frame_with_pose_names(rows)
    if frame.empty:
        return frame.assign(estimate_source_base=pd.Series(dtype=str), coordinate_status=pd.Series(dtype=str))
    estimate_parts = frame["estimate_source"].str.split("/", n=1, expand=True)
    return frame.assign(
        estimate_source_base=estimate_parts[0],
        coordinate_status=estimate_parts[1].fillna("raw") if 1 in estimate_parts else "raw",
    )


def _per_sequence_rows_to_frame(rows: list[PerSequenceRow]) -> pd.DataFrame:
    return pd.DataFrame.from_records(
        {
            **row.model_dump(mode="json"),
            "pose_relation_name": row.pose_relation.name,
        }
        for row in rows
    )


def _clean_records(frame: pd.DataFrame) -> list[dict]:
    return frame.astype("object").where(lambda df: pd.notna(df), None).to_dict("records")


def _pose_relation_name(value: str | metrics.PoseRelation) -> str:
    if isinstance(value, metrics.PoseRelation):
        return value.name
    text = str(value)
    if text in metrics.PoseRelation.__members__:
        return text
    return next((relation.name for relation in metrics.PoseRelation if relation.value == text), text)


def _pose_relation_value(value: str | metrics.PoseRelation) -> str:
    name = _pose_relation_name(value)
    return metrics.PoseRelation[name].value if name in metrics.PoseRelation.__members__ else str(value)


def _wide_metric_columns_for(statistic: str) -> dict[tuple[str, str], str]:
    if statistic == "rmse":
        return dict(_METRIC_COLUMNS)
    stat_label = statistic.replace("_", " ").title()
    return {key: label.replace("RMSE", stat_label) for key, label in _METRIC_COLUMNS.items()}


__all__ = [
    "CoverageCell",
    "CoverageMatrix",
    "HeatmapData",
    "LeaderboardRow",
    "MetricFilter",
    "MetricKey",
    "PerSequenceRow",
    "WideMetricRow",
    "available_metric_keys",
    "build_coverage_matrix",
    "build_heatmap_data",
    "build_leaderboard",
    "build_per_sequence_table",
    "build_wide_metric_rows",
    "filter_metric_rows",
    "metric_frame_to_rows",
    "metric_rows_to_frame",
]
