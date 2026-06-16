"""Streamlit page for persisted trajectory benchmark aggregation."""

from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import streamlit as st
from evo.core import metrics

from prml_vslam.eval.dataset_aggregation import (
    MetricFilter,
    build_coverage_matrix,
    build_heatmap_data,
    build_leaderboard,
    build_per_sequence_table,
)
from prml_vslam.eval.query import RunTrajectoryEvaluation, TrajectoryEvaluationQueryService
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

_PRIMARY_METRIC_OPTIONS = [
    ("ape", metrics.PoseRelation.translation_part, "rmse"),
    ("ape", metrics.PoseRelation.rotation_angle_deg, "rmse"),
    ("rpe", metrics.PoseRelation.translation_part, "rmse"),
    ("rpe", metrics.PoseRelation.rotation_angle_deg, "rmse"),
]
_PRIMARY_METRIC_LABELS = {
    ("ape", metrics.PoseRelation.translation_part, "rmse"): "APE Translation RMSE (m)",
    ("ape", metrics.PoseRelation.rotation_angle_deg, "rmse"): "APE Rotation RMSE (deg)",
    ("rpe", metrics.PoseRelation.translation_part, "rmse"): "RPE Translation RMSE (m)",
    ("rpe", metrics.PoseRelation.rotation_angle_deg, "rmse"): "RPE Rotation RMSE (deg)",
}
_PRIMARY_METRIC_UNITS = {
    ("ape", metrics.PoseRelation.translation_part, "rmse"): "APE RMSE (m)",
    ("ape", metrics.PoseRelation.rotation_angle_deg, "rmse"): "APE Rotation RMSE (deg)",
    ("rpe", metrics.PoseRelation.translation_part, "rmse"): "RPE RMSE (m)",
    ("rpe", metrics.PoseRelation.rotation_angle_deg, "rmse"): "RPE Rotation RMSE (deg)",
}


def render(context: AppContext) -> None:
    """Render multi-run trajectory metric aggregation from persisted artifacts."""
    render_page_intro(
        eyebrow="Benchmark Review",
        title="Trajectory Metrics",
        body=(
            "Inspect persisted trajectory evaluation manifests across runs. "
            "Use **Recompute Metrics** to regenerate manifests from existing artifact data."
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
    _render_recompute_button(query, selection.runs)
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
            "Message": item.load_error or "",
        }
        for item in loaded
    ]
    with st.container(border=True):
        st.subheader("Run Coverage")
        st.dataframe(rows, hide_index=True, width="stretch")


def _render_recompute_button(
    query: TrajectoryEvaluationQueryService,
    runs: list,
    *,
    label: str = "Recompute Metrics",
) -> None:
    if st.button(label, icon=":material/refresh:"):
        if not runs:
            st.info("No runs to recompute.")
            return
        errors: list[str] = []
        n = len(runs)
        progress = st.progress(0.0, text="Starting…")
        for i, run in enumerate(runs):
            progress.progress((i + 0.5) / n, text=f"Recomputing {run.label}…")
            try:
                query.recompute_run_evaluation(run)
            except Exception as exc:
                errors.append(f"{run.label}: {exc}")
        progress.progress(1.0, text="Done.")
        for err in errors:
            st.warning(err)
        st.rerun()


def _render_filters(rows: list[TrajectoryMetricResultRow]) -> list[TrajectoryMetricResultRow]:
    with st.container(border=True):
        st.subheader("Filters")
        columns = st.columns(2, gap="small")
        references = _multi_select(columns[0], "Reference", [row.reference_source for row in rows])
        estimates = _multi_select(columns[1], "Estimate", [row.estimate_source.split("/")[0] for row in rows])
    return [
        row for row in rows if row.reference_source in references and row.estimate_source.split("/")[0] in estimates
    ]


def _multi_select(column, label: str, values: list[str]) -> list[str]:
    options = sorted(set(values))
    return column.multiselect(label, options=options, default=options)


def _render_wide_metric_table(rows: list[TrajectoryMetricResultRow]) -> None:
    table_rows = _build_wide_metric_rows(rows)
    with st.container(border=True):
        st.subheader("Metrics")
        st.dataframe(table_rows, hide_index=True, width="stretch")


def _build_wide_metric_rows(rows: list[TrajectoryMetricResultRow]) -> list[dict]:
    """Pivot long-format RMSE rows into one wide row per sequence/run/reference/estimate/status."""
    rmse_rows = [r for r in rows if r.statistic == "rmse"]
    groups: dict[tuple[str, str, str, str, str], dict] = {}
    aggregate_groups: dict[tuple[str, str, str, str], dict] = {}
    family_sequence_pairs: dict[tuple[str, str, str, str, str, str], int] = {}
    for row in rmse_rows:
        source, _, coord = row.estimate_source.partition("/")
        key = (row.sequence_id, row.run_id, row.reference_source, source, coord)
        aggregate_key = (row.run_id, row.reference_source, source, coord)
        if key not in groups:
            groups[key] = {
                "Sequence": row.sequence_id,
                "Run": row.run_id,
                "Reference": row.reference_source,
                "Estimate": source,
                "Coordinate Status": coord,
                "APE Trans. RMSE (m)": None,
                "APE Rot. RMSE (deg)": None,
                "RPE Trans. RMSE (m)": None,
                "RPE Rot. RMSE (deg)": None,
                "APE Pairs": None,
                "RPE Pairs": None,
            }
        if aggregate_key not in aggregate_groups:
            aggregate_groups[aggregate_key] = {
                "Sequence": "All sequences",
                "Run": row.run_id,
                "Reference": row.reference_source,
                "Estimate": source,
                "Coordinate Status": coord,
                "APE Trans. RMSE (m)": None,
                "APE Rot. RMSE (deg)": None,
                "RPE Trans. RMSE (m)": None,
                "RPE Rot. RMSE (deg)": None,
                "APE Pairs": None,
                "RPE Pairs": None,
                "_ape_trans": [],
                "_ape_rot": [],
                "_rpe_trans": [],
                "_rpe_rot": [],
            }
        pose = row.pose_relation.name
        family = row.metric_family
        if family == "ape" and pose == "translation_part":
            groups[key]["APE Trans. RMSE (m)"] = round(row.value, 4)
            groups[key]["APE Pairs"] = row.matched_pairs
            aggregate_groups[aggregate_key]["_ape_trans"].append((row.value, row.matched_pairs))
        elif family == "ape" and pose == "rotation_angle_deg":
            groups[key]["APE Rot. RMSE (deg)"] = round(row.value, 4)
            groups[key]["APE Pairs"] = row.matched_pairs
            aggregate_groups[aggregate_key]["_ape_rot"].append((row.value, row.matched_pairs))
        elif family == "rpe" and pose == "translation_part":
            groups[key]["RPE Trans. RMSE (m)"] = round(row.value, 4)
            groups[key]["RPE Pairs"] = row.matched_pairs
            aggregate_groups[aggregate_key]["_rpe_trans"].append((row.value, row.matched_pairs))
        elif family == "rpe" and pose == "rotation_angle_deg":
            groups[key]["RPE Rot. RMSE (deg)"] = round(row.value, 4)
            groups[key]["RPE Pairs"] = row.matched_pairs
            aggregate_groups[aggregate_key]["_rpe_rot"].append((row.value, row.matched_pairs))
        family_sequence_key = (*aggregate_key, row.metric_family, row.sequence_id)
        family_sequence_pairs[family_sequence_key] = max(
            family_sequence_pairs.get(family_sequence_key, 0),
            row.matched_pairs,
        )

    aggregate_rows = []
    for aggregate_key, aggregate_row in aggregate_groups.items():
        run_id, reference, source, coord = aggregate_key
        aggregate_row["APE Trans. RMSE (m)"] = _pooled_rmse(aggregate_row.pop("_ape_trans"))
        aggregate_row["APE Rot. RMSE (deg)"] = _pooled_rmse(aggregate_row.pop("_ape_rot"))
        aggregate_row["RPE Trans. RMSE (m)"] = _pooled_rmse(aggregate_row.pop("_rpe_trans"))
        aggregate_row["RPE Rot. RMSE (deg)"] = _pooled_rmse(aggregate_row.pop("_rpe_rot"))
        aggregate_row["APE Pairs"] = _sum_family_pairs(
            family_sequence_pairs,
            run_id=run_id,
            reference=reference,
            source=source,
            coord=coord,
            family="ape",
        )
        aggregate_row["RPE Pairs"] = _sum_family_pairs(
            family_sequence_pairs,
            run_id=run_id,
            reference=reference,
            source=source,
            coord=coord,
            family="rpe",
        )
        aggregate_rows.append(aggregate_row)

    table_rows = [*groups.values(), *aggregate_rows]
    return sorted(
        table_rows,
        key=lambda r: (
            r["Run"],
            r["Reference"],
            r["Estimate"],
            r["Coordinate Status"],
            r["Sequence"] == "All sequences",
            r["Sequence"],
        ),
    )


def _pooled_rmse(values_and_pairs: list[tuple[float, int]]) -> float | None:
    total_pairs = sum(pairs for _, pairs in values_and_pairs)
    if total_pairs <= 0:
        return None
    pooled = math.sqrt(sum(pairs * value**2 for value, pairs in values_and_pairs) / total_pairs)
    return round(pooled, 4)


def _sum_family_pairs(
    family_sequence_pairs: dict[tuple[str, str, str, str, str, str], int],
    *,
    run_id: str,
    reference: str,
    source: str,
    coord: str,
    family: str,
) -> int | None:
    total = sum(
        pairs
        for (item_run, item_reference, item_source, item_coord, item_family, _), pairs in family_sequence_pairs.items()
        if (item_run, item_reference, item_source, item_coord, item_family)
        == (run_id, reference, source, coord, family)
    )
    return total or None


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

    runs = query.discover_dataset_runs(dataset)
    _render_recompute_button(query, runs, label="Recompute All Dataset Metrics")

    with st.spinner("Loading dataset evaluation…"):
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

    metric_keys = _PRIMARY_METRIC_OPTIONS
    current_key = _decode_primary_metric(page_state.dataset_primary_metric)
    metric_index = metric_keys.index(current_key) if current_key in metric_keys else 0

    with st.container(border=True):
        st.subheader("Primary Metric")
        selected_metric = st.selectbox(
            "Metric",
            options=metric_keys,
            index=metric_index,
            format_func=lambda k: _PRIMARY_METRIC_LABELS.get(k, str(k)),
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
        _render_wide_metric_table(dataset_selection.metric_rows)

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
            metric_name=_PRIMARY_METRIC_UNITS.get(selected_metric, "RMSE"),
        )
        with st.container(border=True):
            st.subheader("Sequence Heatmap")
            st.plotly_chart(build_dataset_heatmap(heatmap_data), width="stretch")

        col_bar, col_violin = st.columns(2, gap="large")
        col_bar.plotly_chart(_plot_grouped_bar(per_seq_rows), width="stretch")
        col_violin.plotly_chart(build_violin_by_method(per_seq_rows), width="stretch")
    else:
        st.info("No metric rows match the selected primary metric. Try selecting a different metric.")


def _encode_primary_metric(key: tuple) -> str:
    family, pose_relation, statistic = key
    return f"{family}/{pose_relation.name}/{statistic}"


def _decode_primary_metric(encoded: str) -> tuple | None:
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
