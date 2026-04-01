"""Plotly figure builders for the metrics page."""

from __future__ import annotations

import plotly.graph_objects as go

from ..models import ErrorSeries, TrajectorySeries


def build_trajectory_figure(series_list: list[TrajectorySeries]) -> go.Figure:
    """Build a compact XY trajectory overlay figure."""
    figure = go.Figure()
    palette = ("#1368ce", "#ef6c00", "#0f9d58", "#c62828")
    for index, series in enumerate(series_list):
        figure.add_trace(
            go.Scatter(
                x=series.positions_xyz[:, 0],
                y=series.positions_xyz[:, 1],
                mode="lines",
                name=series.name,
                line={"width": 2.5, "color": palette[index % len(palette)]},
            )
        )
    figure.update_layout(
        title="Trajectory Overlay",
        xaxis_title="X (m)",
        yaxis_title="Y (m)",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, scaleanchor="x", scaleratio=1)
    return figure


def build_error_figure(error_series: ErrorSeries) -> go.Figure:
    """Build the per-pair `evo` error profile."""
    figure = go.Figure(
        go.Scatter(
            x=error_series.timestamps_s,
            y=error_series.values,
            mode="lines",
            name="APE",
            line={"width": 2.2, "color": "#1368ce"},
            fill="tozeroy",
            fillcolor="rgba(19, 104, 206, 0.12)",
        )
    )
    figure.update_layout(
        title="Error Profile",
        xaxis_title="Timestamp (s)",
        yaxis_title="Error",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True)
    return figure
