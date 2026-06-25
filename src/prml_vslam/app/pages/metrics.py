"""Streamlit page for persisted trajectory benchmark aggregation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from evo.core import metrics

from prml_vslam.eval.dataset_aggregation import (
    MetricFilter,
    MetricKey,
    available_metric_keys,
    build_coverage_matrix,
    build_heatmap_data,
    build_leaderboard,
    build_per_sequence_table,
    build_wide_metric_rows,
    filter_metric_rows,
)
from prml_vslam.eval.query import RunTrajectoryEvaluation
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow
from prml_vslam.plotting.metrics import (
    build_coverage_chart,
    build_dataset_heatmap,
    build_trajectory_error_box,
    build_trajectory_error_cdf,
    build_trajectory_rmse_bar,
    build_violin_by_method,
)
from prml_vslam.plotting.metrics import build_grouped_bar_per_sequence as _plot_grouped_bar
from prml_vslam.sources.datasets.contracts import DatasetId

from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext

_SCOPE_OPTIONS = ["sequence", "dataset"]
_SCOPE_LABELS = {"sequence": "Single Sequence", "dataset": "Dataset Overview"}

_DEFAULT_PRIMARY_METRIC = ("ape", metrics.PoseRelation.translation_part, "rmse")


def render(context: AppContext) -> None:
    """Render multi-run trajectory metric aggregation from persisted artifacts."""
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Trajectory Metrics",
        body=(
            "Inspect persisted trajectory evaluation manifests across runs. "
            "Regenerate missing or stale metrics through the trajectory evaluation repair command."
        ),
    )
    page_state = context.state.metrics
    query = context.trajectory_evaluation_query
    with st.container(border=True):
        st.subheader("Benchmark Slice")
        col_dataset, col_scope = st.columns([3, 2], gap="small")
        datasets = list(DatasetId)
        dataset = col_dataset.selectbox(
            "Dataset", datasets, index=datasets.index(page_state.dataset), format_func=lambda item: item.label
        )
        scope_index = _SCOPE_OPTIONS.index(page_state.scope) if page_state.scope in _SCOPE_OPTIONS else 0
        scope = col_scope.selectbox(
            "View",
            options=_SCOPE_OPTIONS,
            index=scope_index,
            format_func=lambda s: _SCOPE_LABELS.get(s, s),
        )

    if scope == "dataset":
        _save_state(context, dataset=dataset, scope=scope)
        _render_dataset_summary(context, dataset)
        return

    with st.container(border=True):
        selection = query.resolve_selection(dataset=dataset, preferred_sequence_slug=page_state.sequence_slug)
        if not selection.sequence_slugs:
            _save_state(context, dataset=dataset, scope=scope)
            st.warning(f"No local {dataset.label} sequences were found under `{selection.dataset_root}`.")
            return
        sequence_slug = st.selectbox(
            "Sequence",
            options=selection.sequence_slugs,
            index=selection.sequence_slugs.index(selection.sequence_slug or selection.sequence_slugs[0]),
        )
        selection = query.resolve_selection(dataset=dataset, preferred_sequence_slug=sequence_slug)
        _save_state(context, dataset=dataset, sequence_slug=sequence_slug, scope=scope)
        if not selection.runs:
            st.info(f"No benchmark runs with `slam/trajectory.tum` were found under `{selection.artifacts_root}`.")
            return

    loaded = [query.load_run_evaluation(run) for run in selection.runs]
    _render_run_status(loaded)
    metric_rows = [row for loaded_run in loaded for row in loaded_run.metric_rows]
    if not metric_rows:
        st.info("No persisted trajectory metric rows are available for this sequence yet.")
        return

    filtered_rows = _render_filters(metric_rows)
    if not filtered_rows:
        st.warning("No metric rows match the selected filters.")
        return
    _render_wide_metric_table(filtered_rows)
    _render_summary_plots(context, filtered_rows)


def _render_run_status(loaded: list[RunTrajectoryEvaluation]) -> None:
    rows = [
        {
            "Run": item.run.label,
            "Artifact Root": item.run.artifact_root.as_posix(),
            "Manifest": "missing"
            if item.manifest is None and item.load_error is None
            else "error"
            if item.load_error is not None
            else "loaded",
            "Metric Rows": len(item.metric_rows),
            "Skipped Metrics": item.skipped_metric_count,
            "Sim(3) Skips": _sim3_alignment_skip_count(item),
            "Message": item.load_error or "",
        }
        for item in loaded
    ]
    with st.container(border=True):
        st.subheader("Run Coverage")
        st.dataframe(rows, hide_index=True, width="stretch")


def _sim3_alignment_skip_count(item: RunTrajectoryEvaluation) -> int:
    if item.manifest is None:
        return 0
    return sum(1 for record in item.manifest.skipped_metrics if "Sim(3) alignment" in record.reason)


def _render_filters(rows: list[TrajectoryMetricResultRow]) -> list[TrajectoryMetricResultRow]:
    with st.container(border=True):
        st.subheader("Filters")
        columns = st.columns(2, gap="small")
        references = _multi_select(columns[0], "Reference", [row.reference_source for row in rows])
        estimates = _multi_select(columns[1], "Estimate", [row.estimate_source.split("/")[0] for row in rows])
    return filter_metric_rows(rows, references=references, estimates=estimates)


def _multi_select(column, label: str, values: list[str]) -> list[str]:
    options = sorted(set(values))
    return column.multiselect(label, options=options, default=options)


def _render_wide_metric_table(rows: list[TrajectoryMetricResultRow], *, statistic: str = "rmse") -> None:
    table_rows = build_wide_metric_rows(rows, statistic=statistic)
    with st.container(border=True):
        st.subheader("Metrics")
        st.dataframe(table_rows, hide_index=True, width="stretch")


_PLOT_METRIC_SPECS = [
    ("ape", "translation_part", "APE Translation", "m"),
    ("ape", "rotation_angle_deg", "APE Rotation", "deg"),
    ("rpe", "translation_part", "RPE Translation", "m"),
    ("rpe", "rotation_angle_deg", "RPE Rotation", "deg"),
]


def _render_summary_plots(context: AppContext, rows: list[TrajectoryMetricResultRow]) -> None:
    plot_rows = [row for row in rows if row.statistic == "rmse"]
    if plot_rows:
        st.plotly_chart(build_trajectory_rmse_bar(plot_rows), width="stretch")
    for family, pose_name, label, unit in _PLOT_METRIC_SPECS:
        group_rows = [
            row
            for row in rows
            if row.statistic == "rmse"
            and row.metric_family == family
            and row.pose_relation.name == pose_name
            and row.error_series_path is not None
        ]
        if not group_rows:
            continue
        series_by_label = _load_error_series_by_label(context, group_rows)
        if not any(v.size > 0 for v in series_by_label.values()):
            continue
        col_cdf, col_box = st.columns(2, gap="large")
        col_cdf.plotly_chart(
            build_trajectory_error_cdf(series_by_label, title=f"{label} CDF", unit=unit), width="stretch"
        )
        col_box.plotly_chart(
            build_trajectory_error_box(series_by_label, title=f"{label} Distribution", unit=unit), width="stretch"
        )


def _load_error_series_by_label(context: AppContext, rows: list[TrajectoryMetricResultRow]) -> dict[str, np.ndarray]:
    series_by_label: dict[str, np.ndarray] = {}
    for row in rows:
        series_by_label[f"{row.run_id} / {row.estimate_source}"] = _load_error_values(context, row.error_series_path)
    return series_by_label


def _load_error_values(context: AppContext, path: Path | None) -> np.ndarray:
    if path is None:
        return np.empty(0, dtype=np.float64)
    try:
        return context.trajectory_evaluation_query.load_error_series_values(path)
    except (OSError, ValueError, KeyError) as exc:
        st.warning(f"Could not load error series `{path}`: {exc}")
        return np.empty(0, dtype=np.float64)


def _render_dataset_summary(context: AppContext, dataset: DatasetId) -> None:
    """Render the dataset-wide benchmark summary view."""
    query = context.trajectory_evaluation_query
    page_state = context.state.metrics

    with st.spinner("Loading dataset evaluation..."):
        dataset_selection = query.load_dataset_evaluation(dataset)

    if not dataset_selection.metric_rows:
        st.info(
            f"No persisted metric rows were found for {dataset.label}. "
            "Run the trajectory evaluation stage to populate metrics."
        )
        coverage_matrix = build_coverage_matrix(dataset_selection)
        if coverage_matrix.cells:
            with st.container(border=True):
                st.subheader("Run Coverage")
                st.plotly_chart(build_coverage_chart(coverage_matrix), width="stretch")
        return

    total_skipped = sum(c.skipped_metric_count for c in dataset_selection.coverage)
    if total_skipped > 0:
        affected = sum(1 for c in dataset_selection.coverage if c.skipped_metric_count > 0)
        st.warning(
            f"{total_skipped} non-primary metric calculation(s) were skipped across {affected} run(s). "
            "Short trajectories or insufficient pose-pair counts are the usual cause. "
            "Switch to **Single Sequence** view and inspect the Skipped Metrics column for details."
        )
    sim3_skips = sum(c.sim3_alignment_skip_count for c in dataset_selection.coverage)
    if sim3_skips > 0:
        st.warning(f"{sim3_skips} metric calculation(s) were skipped because Sim(3) alignment failed.")

    metric_keys = available_metric_keys(dataset_selection.metric_rows)
    if not metric_keys:
        st.info("No metric rows are available for the selected dataset.")
        return
    current_key = _decode_primary_metric(page_state.dataset_primary_metric)
    default_key = _DEFAULT_PRIMARY_METRIC if _DEFAULT_PRIMARY_METRIC in metric_keys else metric_keys[0]
    metric_index = metric_keys.index(current_key) if current_key in metric_keys else metric_keys.index(default_key)

    with st.container(border=True):
        st.subheader("Primary Metric")
        selected_metric = st.selectbox(
            "Metric",
            options=metric_keys,
            index=metric_index,
            format_func=_metric_label,
        )
        _save_state(
            context,
            dataset=dataset,
            scope="dataset",
            dataset_primary_metric=_encode_primary_metric(selected_metric),
        )

    family, pose_relation, statistic = selected_metric
    metric_filter = MetricFilter(metric_family=family, pose_relation=pose_relation, statistic=statistic)
    per_seq_rows = build_per_sequence_table(dataset_selection, metric_filter)
    n_total = len(dataset_selection.all_sequence_ids)

    coverage_matrix = build_coverage_matrix(dataset_selection)
    with st.container(border=True):
        st.subheader("Coverage")
        st.plotly_chart(build_coverage_chart(coverage_matrix), width="stretch")

    if dataset_selection.metric_rows:
        _render_wide_metric_table(dataset_selection.metric_rows, statistic=statistic)

    if per_seq_rows:
        leaderboard = build_leaderboard(per_seq_rows, n_total_sequences=n_total)
        with st.container(border=True):
            st.subheader("Leaderboard")
            st.dataframe(
                [
                    {
                        "Method": r.estimate_source_base,
                        "Coordinate Status": r.coordinate_status,
                        "Metric": f"{r.metric_family}.{r.pose_relation.name}",
                        "Mean": round(r.mean, 4),
                        "Median": round(r.median, 4),
                        "Std": round(r.std, 4),
                        "Unit": r.unit or "",
                        "Sequences": f"{r.n_sequences}/{r.n_total_sequences}",
                    }
                    for r in leaderboard
                ],
                hide_index=True,
                width="stretch",
            )

        heatmap_data = build_heatmap_data(
            per_seq_rows,
            dataset_selection.all_sequence_ids,
            metric_name=_metric_label(selected_metric),
        )
        with st.container(border=True):
            st.subheader("Sequence Heatmap")
            st.plotly_chart(build_dataset_heatmap(heatmap_data), width="stretch")

        col_bar, col_violin = st.columns(2, gap="large")
        col_bar.plotly_chart(_plot_grouped_bar(per_seq_rows), width="stretch")
        col_violin.plotly_chart(build_violin_by_method(per_seq_rows), width="stretch")
    else:
        st.info("No metric rows match the selected primary metric. Try selecting a different metric.")


def _metric_label(key: MetricKey) -> str:
    family, pose_relation, statistic = key
    pose_label = "Translation" if pose_relation is metrics.PoseRelation.translation_part else "Rotation"
    unit = "m" if pose_relation is metrics.PoseRelation.translation_part else "deg"
    return f"{family.upper()} {pose_label} {statistic.upper()} ({unit})"


def _encode_primary_metric(key: MetricKey) -> str:
    family, pose_relation, statistic = key
    return f"{family}/{pose_relation.name}/{statistic}"


def _decode_primary_metric(encoded: str) -> MetricKey | None:
    parts = encoded.split("/")
    if len(parts) != 3:
        return None
    family, pose_relation_name, statistic = parts
    if pose_relation_name not in metrics.PoseRelation.__members__:
        return None
    return (family, metrics.PoseRelation[pose_relation_name], statistic)


def _save_state(
    context: AppContext,
    *,
    dataset: DatasetId,
    sequence_slug: str | None = None,
    scope: str = "sequence",
    dataset_primary_metric: str | None = None,
) -> None:
    updates: dict = {"dataset": dataset, "scope": scope, "sequence_slug": sequence_slug}
    if dataset_primary_metric is not None:
        updates["dataset_primary_metric"] = dataset_primary_metric
    save_model_updates(
        context.store,
        context.state,
        context.state.metrics,
        **updates,
    )
