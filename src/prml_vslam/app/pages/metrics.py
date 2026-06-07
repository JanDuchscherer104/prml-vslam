"""Streamlit page for persisted trajectory benchmark aggregation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st

from prml_vslam.eval.query import RunTrajectoryEvaluation
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow
from prml_vslam.plotting.metrics import (
    build_trajectory_error_box,
    build_trajectory_error_cdf,
    build_trajectory_rmse_bar,
)
from prml_vslam.sources.datasets.contracts import DatasetId

from ..state import save_model_updates
from ..ui import render_page_intro

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render multi-run trajectory metric aggregation from persisted artifacts."""
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Trajectory Metrics",
        body=(
            "Inspect persisted trajectory evaluation manifests across runs. This page never computes evo metrics; "
            "rerun the trajectory evaluation stage when manifests are missing."
        ),
    )
    metrics = context.state.metrics
    query = context.trajectory_evaluation_query
    with st.container(border=True):
        st.subheader("Benchmark Slice")
        datasets = list(DatasetId)
        dataset = st.selectbox(
            "Dataset", datasets, index=datasets.index(metrics.dataset), format_func=lambda item: item.label
        )
        selection = query.resolve_selection(dataset=dataset, preferred_sequence_slug=metrics.sequence_slug)
        if not selection.sequence_slugs:
            _save_state(context, dataset=dataset)
            st.warning(f"No local {dataset.label} sequences were found under `{selection.dataset_root}`.")
            return
        sequence_slug = st.selectbox(
            "Sequence",
            options=selection.sequence_slugs,
            index=selection.sequence_slugs.index(selection.sequence_slug or selection.sequence_slugs[0]),
        )
        selection = query.resolve_selection(dataset=dataset, preferred_sequence_slug=sequence_slug)
        _save_state(context, dataset=dataset, sequence_slug=sequence_slug)
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
    _render_ranked_table(filtered_rows)
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
            "Message": item.load_error or "",
        }
        for item in loaded
    ]
    with st.container(border=True):
        st.subheader("Run Coverage")
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_filters(rows: list[TrajectoryMetricResultRow]) -> list[TrajectoryMetricResultRow]:
    with st.container(border=True):
        st.subheader("Filters")
        columns = st.columns(4, gap="small")
        families = _multi_select(columns[0], "Metric Family", [row.metric_family for row in rows])
        relations = _multi_select(columns[1], "Pose Relation", [row.pose_relation.value for row in rows])
        references = _multi_select(columns[2], "Reference", [row.reference_source for row in rows])
        estimates = _multi_select(columns[3], "Estimate", [row.estimate_source for row in rows])
    return [
        row
        for row in rows
        if row.metric_family in families
        and row.pose_relation.value in relations
        and row.reference_source in references
        and row.estimate_source in estimates
    ]


def _multi_select(column, label: str, values: list[str]) -> list[str]:
    options = sorted(set(values))
    return column.multiselect(label, options=options, default=options)


def _render_ranked_table(rows: list[TrajectoryMetricResultRow]) -> None:
    table_rows = [
        {
            "Run": row.run_id,
            "Sequence": row.sequence_id,
            "Reference": row.reference_source,
            "Estimate": row.estimate_source,
            "Metric": f"{row.metric_family}.{row.pose_relation.name}",
            "Statistic": row.statistic,
            "Value": row.value,
            "Unit": row.unit or "",
            "Matched Pairs": row.matched_pairs,
        }
        for row in sorted(rows, key=lambda item: (item.statistic != "rmse", item.value))
    ]
    with st.container(border=True):
        st.subheader("Ranked Metrics")
        st.dataframe(table_rows, hide_index=True, width="stretch")


def _render_summary_plots(context: AppContext, rows: list[TrajectoryMetricResultRow]) -> None:
    plot_rows = [row for row in rows if row.statistic == "rmse"]
    if plot_rows:
        st.plotly_chart(build_trajectory_rmse_bar(plot_rows), width="stretch")
    cdf_rows = [
        row
        for row in rows
        if row.statistic == "rmse"
        and row.metric_family == "ape"
        and row.pose_relation.name == "translation_part"
        and row.error_series_path is not None
    ]
    if not cdf_rows:
        return
    series_by_label = _load_error_series_by_label(context, cdf_rows)
    figures = st.columns(2, gap="large")
    figures[0].plotly_chart(build_trajectory_error_cdf(series_by_label), width="stretch")
    figures[1].plotly_chart(build_trajectory_error_box(series_by_label), width="stretch")


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


def _save_state(
    context: AppContext,
    *,
    dataset: DatasetId,
    sequence_slug: str | None = None,
) -> None:
    save_model_updates(
        context.store,
        context.state,
        context.state.metrics,
        dataset=dataset,
        sequence_slug=sequence_slug,
    )
