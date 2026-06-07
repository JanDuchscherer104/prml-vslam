"""Plotly figure builders for the metrics page."""

from __future__ import annotations

from typing import Protocol

import numpy as np
import plotly.graph_objects as go

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
