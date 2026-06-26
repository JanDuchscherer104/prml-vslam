"""Plotly figure builders for the metrics page."""

from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Protocol

import numpy as np
import plotly.graph_objects as go
from evo.core import metrics
from plotly.subplots import make_subplots

from prml_vslam.eval.contracts import CloudMetricId, DenseCloudEvaluationArtifact
from prml_vslam.eval.dataset_aggregation import CoverageMatrix, HeatmapData, PerSequenceRow
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow

from .theme import BLUE, DEFAULT_COLORS, GRAY, GREEN, ORANGE, PURPLE, RED, apply_standard_xy_layout
from .trajectories import _add_xy_trajectory_trace, _apply_standard_trajectory_xy_layout

_RMSE_METRIC_FACETS = [
    ("ape", metrics.PoseRelation.translation_part, "APE Translation (m)"),
    ("ape", metrics.PoseRelation.rotation_angle_deg, "APE Rotation (deg)"),
    ("rpe", metrics.PoseRelation.translation_part, "RPE Translation (m)"),
    ("rpe", metrics.PoseRelation.rotation_angle_deg, "RPE Rotation (deg)"),
]


class TrajectoryPlotSeries(Protocol):
    """Trajectory payload needed by the metrics plot builders."""

    name: str
    positions_xyz: np.ndarray


class ErrorPlotSeries(Protocol):
    """Error-series payload needed by the metrics plot builders."""

    timestamps_s: np.ndarray
    values: np.ndarray


def build_trajectory_figure(series_list: list[TrajectoryPlotSeries]) -> go.Figure:
    """Build a compact XY trajectory overlay figure."""
    colors = DEFAULT_COLORS[np.arange(len(series_list), dtype=np.intp) % DEFAULT_COLORS.size]
    figure = go.Figure()
    for series, color in zip(series_list, colors, strict=True):
        _add_xy_trajectory_trace(
            figure,
            series.positions_xyz,
            name=series.name,
            line={"width": 2.5, "color": str(color)},
        )
    _apply_standard_trajectory_xy_layout(figure, title="Trajectory Overlay")
    return figure


def build_error_figure(error_series: ErrorPlotSeries) -> go.Figure:
    """Build the per-pair `evo` error profile."""
    figure = go.Figure(
        go.Scatter(
            x=error_series.timestamps_s,
            y=error_series.values,
            mode="lines",
            name="APE",
            line={"width": 2.2, "color": BLUE},
            fill="tozeroy",
            fillcolor="rgba(19, 104, 206, 0.12)",
        )
    )
    apply_standard_xy_layout(
        figure,
        title="Error Profile",
        xaxis_title="Timestamp (s)",
        yaxis_title="Error",
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True)
    return figure


def build_trajectory_rmse_bar(rows: list[TrajectoryMetricResultRow]) -> go.Figure:
    """Build a cross-run RMSE summary for persisted trajectory metric rows."""
    rmse_rows = [row for row in rows if row.statistic == "rmse"]
    facets = [
        (family, relation, title)
        for family, relation, title in _RMSE_METRIC_FACETS
        if any(row.metric_family == family and row.pose_relation is relation for row in rmse_rows)
    ]
    if not facets:
        figure = go.Figure()
        figure.update_layout(
            title="RMSE by Run and Metric",
            margin={"l": 48, "r": 24, "t": 48, "b": 64},
            showlegend=False,
        )
        return figure

    n_cols = 2 if len(facets) == 4 else len(facets)
    n_rows = int(np.ceil(len(facets) / n_cols))
    figure = make_subplots(
        rows=n_rows,
        cols=n_cols,
        subplot_titles=[title for _, _, title in facets],
        shared_yaxes=False,
    )
    identities = sorted({_run_identity(row) for row in rmse_rows})
    colors = {identity: str(DEFAULT_COLORS[index % DEFAULT_COLORS.size]) for index, identity in enumerate(identities)}
    legend_seen: set[str] = set()
    for index, (family, relation, title) in enumerate(facets):
        subplot_row = index // n_cols + 1
        subplot_col = index % n_cols + 1
        for row in rmse_rows:
            if row.metric_family != family or row.pose_relation is not relation:
                continue
            identity = _run_identity(row)
            _, coordinate_status = _estimate_source_parts(row.estimate_source)
            figure.add_trace(
                go.Bar(
                    name=identity,
                    x=[identity],
                    y=[row.value],
                    marker_color=colors[identity],
                    showlegend=identity not in legend_seen,
                    customdata=[
                        [
                            row.run_id,
                            row.estimate_source,
                            row.metric_family,
                            row.pose_relation.name,
                            row.value,
                            row.unit or "",
                            row.matched_pairs,
                            "Sim(3) applied",
                            coordinate_status,
                        ]
                    ],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Estimate: %{customdata[1]}<br>"
                        "Metric: %{customdata[2]}.%{customdata[3]}<br>"
                        "RMSE: %{customdata[4]:.4g} %{customdata[5]}<br>"
                        "Matched pairs: %{customdata[6]}<br>"
                        "Alignment status: %{customdata[7]}<br>"
                        "Coordinate status: %{customdata[8]}<extra></extra>"
                    ),
                ),
                row=subplot_row,
                col=subplot_col,
            )
            legend_seen.add(identity)
        figure.update_xaxes(title_text="Run / Method", row=subplot_row, col=subplot_col)
        figure.update_yaxes(title_text=title, row=subplot_row, col=subplot_col)
    figure.update_layout(
        title="RMSE by Run and Metric",
        barmode="group",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.08, "x": 0},
        margin={"l": 48, "r": 24, "t": 96, "b": 72},
    )
    return figure


def _run_identity(row: TrajectoryMetricResultRow) -> str:
    source_base, coordinate_status = _estimate_source_parts(row.estimate_source)
    if row.run_id == source_base:
        return source_base
    return f"{row.run_id} / {source_base}" if coordinate_status == "raw" else f"{row.run_id} / {row.estimate_source}"


def _estimate_source_parts(estimate_source: str) -> tuple[str, str]:
    source_base, separator, coordinate_status = estimate_source.partition("/")
    return source_base, coordinate_status if separator else "raw"


def build_trajectory_error_cdf(
    series_by_label: dict[str, np.ndarray],
    *,
    title: str = "Error CDF",
    unit: str = "m",
) -> go.Figure:
    """Build an empirical CDF for one or more persisted error series."""
    figure = go.Figure()
    for label, values in series_by_label.items():
        if values.size == 0:
            continue
        sorted_values = np.sort(values)
        cdf = np.arange(1, sorted_values.size + 1, dtype=np.float64) / float(sorted_values.size)
        figure.add_trace(go.Scatter(x=sorted_values, y=cdf, mode="lines", name=label))
    figure.update_layout(
        title=title,
        xaxis_title=f"Error ({unit})",
        yaxis_title="Cumulative Fraction",
        margin={"l": 48, "r": 24, "t": 48, "b": 48},
    )
    return figure


def build_trajectory_error_box(
    series_by_label: dict[str, np.ndarray],
    *,
    title: str = "Error Distribution",
    unit: str = "m",
) -> go.Figure:
    """Build a distribution box plot for one or more persisted error series."""
    figure = go.Figure()
    for label, values in series_by_label.items():
        if values.size == 0:
            continue
        figure.add_trace(go.Box(y=values, name=label, boxmean=True))
    figure.update_layout(
        title=title,
        yaxis_title=f"Error ({unit})",
        margin={"l": 48, "r": 24, "t": 48, "b": 96},
    )
    return figure


def build_dataset_heatmap(data: HeatmapData) -> go.Figure:
    """Build a Plotly heatmap of metric values indexed by sequence × estimate source."""
    figure = go.Figure(
        go.Heatmap(
            z=data.values,
            x=data.estimate_sources,
            y=data.sequence_ids,
            colorscale="RdYlGn_r",
            colorbar={"title": data.metric_name},
            hoverongaps=False,
        )
    )
    figure.update_layout(
        title=data.metric_name,
        xaxis_title="Estimate Source",
        yaxis_title="Sequence",
        margin={"l": 120, "r": 24, "t": 64, "b": 80},
    )
    return figure


def build_grouped_bar_per_sequence(rows: list[PerSequenceRow]) -> go.Figure:
    """Build a grouped bar chart of metric values by sequence and estimate source.

    Multiple runs on the same (sequence, source) cell are averaged so no run
    silently overwrites another.
    """
    raw: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        source_label = f"{row.estimate_source_base}/{row.coordinate_status}"
        raw[source_label][row.sequence_id].append(row.value)
    groups: dict[str, dict[str, float]] = {
        src: {seq_id: statistics.mean(vals) for seq_id, vals in seq_map.items()} for src, seq_map in raw.items()
    }

    all_sequences = sorted({row.sequence_id for row in rows})
    colors = DEFAULT_COLORS[np.arange(len(groups), dtype=np.intp) % DEFAULT_COLORS.size]
    figure = go.Figure()
    for (source_label, seq_map), color in zip(groups.items(), colors, strict=False):
        figure.add_trace(
            go.Bar(
                name=source_label,
                x=all_sequences,
                y=[seq_map.get(seq) for seq in all_sequences],
                marker_color=str(color),
            )
        )
    unit = rows[0].unit if rows else ""
    figure.update_layout(
        title="Metric by Sequence",
        xaxis_title="Sequence",
        yaxis_title=f"Value ({unit})" if unit else "Value",
        barmode="group",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 48, "r": 24, "t": 96, "b": 80},
    )
    return figure


def build_coverage_chart(matrix: CoverageMatrix) -> go.Figure:
    """Build a heatmap showing manifest coverage for each sequence × method cell."""
    method_labels = [m if m is not None else "(unknown)" for m in matrix.methods]
    cell_map = {(cell.sequence_id, cell.method): cell for cell in matrix.cells}
    z_values = [
        [
            1 if cell_map.get((seq_id, method), None) is not None and cell_map[(seq_id, method)].manifest_present else 0
            for method in matrix.methods
        ]
        for seq_id in matrix.sequence_ids
    ]
    figure = go.Figure(
        go.Heatmap(
            z=z_values,
            x=method_labels,
            y=matrix.sequence_ids,
            colorscale=[[0, "#f5f5f5"], [1, BLUE]],
            showscale=False,
            zmin=0,
            zmax=1,
        )
    )
    figure.update_layout(
        title="Evaluation Coverage",
        xaxis_title="Method",
        yaxis_title="Sequence",
        margin={"l": 120, "r": 24, "t": 64, "b": 80},
    )
    return figure


def build_violin_by_method(rows: list[PerSequenceRow]) -> go.Figure:
    """Build a violin plot of metric values grouped by estimate source."""
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        source_label = f"{row.estimate_source_base}/{row.coordinate_status}"
        groups[source_label].append(row.value)

    colors = DEFAULT_COLORS[np.arange(len(groups), dtype=np.intp) % DEFAULT_COLORS.size]
    figure = go.Figure()
    for (source_label, values), color in zip(groups.items(), colors, strict=False):
        figure.add_trace(
            go.Violin(
                y=values,
                name=source_label,
                box_visible=True,
                meanline_visible=True,
                line_color=str(color),
            )
        )
    unit = rows[0].unit if rows else ""
    figure.update_layout(
        title="Value Distribution by Method",
        yaxis_title=f"Value ({unit})" if unit else "Value",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        margin={"l": 48, "r": 24, "t": 96, "b": 48},
        violingap=0.3,
    )
    return figure


def build_cloud_distance_metrics_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build grouped bars for distance-valued point-cloud metrics."""
    metric_specs = (
        (CloudMetricId.ACCURACY, "Accuracy"),
        (CloudMetricId.COMPLETENESS, "Completeness"),
        (CloudMetricId.CHAMFER, "Chamfer"),
    )
    figure = go.Figure()
    colors = (BLUE, ORANGE, GREEN)
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    for (metric_id, label), color in zip(metric_specs, colors, strict=True):
        figure.add_bar(
            x=estimate_labels,
            y=[estimate.metrics.get(metric_id) for estimate in artifact.estimates],
            name=label,
            marker_color=color,
            hovertemplate="%{x}<br>%{fullData.name}: %{y:.4f} m<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Point-Cloud Distance Metrics",
        xaxis_title="Estimate",
        yaxis_title="Distance (m)",
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_cloud_quality_metrics_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build bars for thresholded F1 and ICP fitness scores."""
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    figure = go.Figure()
    figure.add_bar(
        x=estimate_labels,
        y=[estimate.metrics.get(CloudMetricId.F1) for estimate in artifact.estimates],
        name=f"F1 @ {artifact.f1_threshold_m:.2f} m",
        marker_color=PURPLE,
        hovertemplate="%{x}<br>%{fullData.name}: %{y:.3f}<extra></extra>",
    )
    icp_fitness = [estimate.metrics.get(CloudMetricId.ICP_FITNESS) for estimate in artifact.estimates]
    if any(value is not None for value in icp_fitness):
        figure.add_bar(
            x=estimate_labels,
            y=icp_fitness,
            name="ICP fitness",
            marker_color=GREEN,
            hovertemplate="%{x}<br>%{fullData.name}: %{y:.3f}<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Point-Cloud Quality Scores",
        xaxis_title="Estimate",
        yaxis_title="Score",
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(range=[0.0, 1.0], showgrid=True)
    return figure


def build_cloud_point_count_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build a compact point-count comparison for evaluated clouds."""
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    figure = go.Figure(
        go.Bar(
            x=estimate_labels,
            y=[estimate.estimate_point_count for estimate in artifact.estimates],
            name="Estimate points",
            marker_color=BLUE,
            hovertemplate="%{x}<br>Estimate points: %{y:,}<extra></extra>",
        )
    )
    if artifact.estimates:
        figure.add_scatter(
            x=estimate_labels,
            y=[artifact.estimates[0].reference_point_count] * len(estimate_labels),
            mode="lines+markers",
            name="Reference points",
            line={"color": ORANGE, "width": 2.0, "dash": "dot"},
            hovertemplate="Reference points: %{y:,}<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Evaluated Point Counts",
        xaxis_title="Estimate",
        yaxis_title="Points",
    )
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_cloud_icp_impact_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build signed Sim(3) -> ICP metric deltas where positive means better."""
    sim3 = _estimate_metrics_by_kind(artifact, "sim3")
    sim3_icp = _estimate_metrics_by_kind(artifact, "sim3_icp")
    metric_specs = (
        (CloudMetricId.ACCURACY, "Accuracy", False),
        (CloudMetricId.COMPLETENESS, "Completeness", False),
        (CloudMetricId.CHAMFER, "Chamfer", False),
        (CloudMetricId.F1, "F1", True),
    )
    labels: list[str] = []
    signed_impacts: list[float] = []
    customdata: list[list[str | float]] = []
    colors: list[str] = []
    for metric_id, label, higher_is_better in metric_specs:
        if metric_id not in sim3 or metric_id not in sim3_icp:
            continue
        before = sim3[metric_id]
        after = sim3_icp[metric_id]
        raw_delta = after - before
        signed_impact = raw_delta if higher_is_better else -raw_delta
        labels.append(label)
        signed_impacts.append(signed_impact)
        customdata.append([before, after, raw_delta, "higher" if higher_is_better else "lower"])
        colors.append(GREEN if signed_impact >= 0.0 else RED)

    figure = go.Figure(
        go.Bar(
            x=labels,
            y=signed_impacts,
            marker_color=colors,
            customdata=customdata,
            hovertemplate=(
                "%{x}<br>"
                "Sim3: %{customdata[0]:.4g}<br>"
                "Sim3 + ICP: %{customdata[1]:.4g}<br>"
                "Raw delta: %{customdata[2]:+.4g}<br>"
                "Better direction: %{customdata[3]}<br>"
                "Signed impact: %{y:+.4g}<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0.0, line_color=GRAY, line_dash="dot")
    apply_standard_xy_layout(
        figure,
        title="ICP Impact on Point-Cloud Metrics",
        xaxis_title="Metric",
        yaxis_title="Signed impact (positive is better)",
        showlegend=False,
    )
    figure.update_yaxes(showgrid=True, zeroline=True)
    return figure


def build_cloud_accuracy_completeness_xy_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build an accuracy-vs-completeness scatter for dense-cloud estimates."""
    figure = go.Figure()
    points: dict[str, tuple[float, float]] = {}
    for estimate in artifact.estimates:
        accuracy = estimate.metrics.get(CloudMetricId.ACCURACY)
        completeness = estimate.metrics.get(CloudMetricId.COMPLETENESS)
        if accuracy is None or completeness is None:
            continue
        estimate_kind = estimate.estimate_kind.value
        label = _estimate_label(estimate_kind)
        f1 = estimate.metrics.get(CloudMetricId.F1)
        marker_size = 12.0 if f1 is None else 12.0 + 16.0 * max(0.0, min(1.0, f1))
        color = GREEN if estimate_kind == "sim3_icp" else BLUE if estimate_kind == "sim3" else ORANGE
        points[estimate_kind] = (accuracy, completeness)
        figure.add_trace(
            go.Scatter(
                x=[accuracy],
                y=[completeness],
                mode="markers+text",
                name=label,
                text=[label],
                textposition="top center",
                marker={"size": marker_size, "color": color, "line": {"color": "white", "width": 1.5}},
                customdata=[[f1 if f1 is not None else np.nan, estimate.estimate_point_count]],
                hovertemplate=(
                    "%{text}<br>"
                    "Accuracy: %{x:.4f} m<br>"
                    "Completeness: %{y:.4f} m<br>"
                    "F1: %{customdata[0]:.3f}<br>"
                    "Estimate points: %{customdata[1]:,}<extra></extra>"
                ),
            )
        )

    if "sim3" in points and "sim3_icp" in points:
        start_x, start_y = points["sim3"]
        end_x, end_y = points["sim3_icp"]
        figure.add_annotation(
            x=end_x,
            y=end_y,
            ax=start_x,
            ay=start_y,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1.2,
            arrowwidth=2.0,
            arrowcolor=GRAY,
            text="ICP",
        )

    apply_standard_xy_layout(
        figure,
        title="Accuracy vs Completeness (Lower-Left Is Better)",
        xaxis_title="Accuracy: estimate -> reference mean distance (m)",
        yaxis_title="Completeness: reference -> estimate mean distance (m)",
    )
    figure.update_xaxes(rangemode="tozero", showgrid=True)
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def _estimate_metrics_by_kind(
    artifact: DenseCloudEvaluationArtifact,
    estimate_kind: str,
) -> dict[CloudMetricId, float]:
    return next(
        (estimate.metrics for estimate in artifact.estimates if estimate.estimate_kind.value == estimate_kind),
        {},
    )


def _estimate_label(value: str) -> str:
    return {
        "sim3": "Sim3",
        "sim3_icp": "Sim3 + ICP",
        "reconstruction": "Reconstruction",
    }.get(value, value.replace("_", " ").title())
