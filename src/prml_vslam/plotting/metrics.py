"""Plotly figure builders for the metrics page."""

from __future__ import annotations

from collections import defaultdict
from typing import Protocol

import numpy as np
import plotly.graph_objects as go

from prml_vslam.eval.dataset_aggregation import CoverageMatrix, HeatmapData, PerSequenceRow
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow

from .theme import BLUE, DEFAULT_COLORS, apply_standard_xy_layout
from .trajectories import _add_xy_trajectory_trace, _apply_standard_trajectory_xy_layout


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
    labels = [f"{row.run_id}<br>{row.estimate_source}<br>{row.metric_family}.{row.pose_relation.name}" for row in rows]
    figure = go.Figure(go.Bar(x=labels, y=[row.value for row in rows], marker_color=BLUE))
    figure.update_layout(
        title="RMSE by Run and Metric",
        xaxis_title="Run / Estimate / Metric",
        yaxis_title="RMSE",
        margin={"l": 48, "r": 24, "t": 48, "b": 96},
    )
    return figure


def build_trajectory_error_cdf(series_by_label: dict[str, np.ndarray]) -> go.Figure:
    """Build an empirical CDF for one or more persisted error series."""
    figure = go.Figure()
    for label, values in series_by_label.items():
        if values.size == 0:
            continue
        sorted_values = np.sort(values)
        cdf = np.arange(1, sorted_values.size + 1, dtype=np.float64) / float(sorted_values.size)
        figure.add_trace(go.Scatter(x=sorted_values, y=cdf, mode="lines", name=label))
    figure.update_layout(
        title="Absolute Position Error CDF",
        xaxis_title="Error (m)",
        yaxis_title="Cumulative Fraction",
        margin={"l": 48, "r": 24, "t": 48, "b": 48},
    )
    return figure


def build_trajectory_error_box(series_by_label: dict[str, np.ndarray]) -> go.Figure:
    """Build a distribution box plot for one or more persisted error series."""
    figure = go.Figure()
    for label, values in series_by_label.items():
        if values.size == 0:
            continue
        figure.add_trace(go.Box(y=values, name=label, boxmean=True))
    figure.update_layout(
        title="Absolute Position Error Distribution",
        yaxis_title="Error (m)",
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
    """Build a grouped bar chart of metric values by sequence and estimate source."""
    groups: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        source_label = f"{row.estimate_source_base}/{row.coordinate_status}"
        groups[source_label][row.sequence_id] = row.value

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
