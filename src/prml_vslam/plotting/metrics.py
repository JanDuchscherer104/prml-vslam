"""Plotly figure builders for the metrics page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.eval.contracts import ErrorSeries, TrajectorySeries

from .theme import BLUE, DEFAULT_COLORS, apply_standard_xy_layout


def build_trajectory_figure(series_list: list[TrajectorySeries]) -> go.Figure:
    """Build a compact XY trajectory overlay figure."""
    colors = DEFAULT_COLORS[np.arange(len(series_list), dtype=np.intp) % DEFAULT_COLORS.size]
    figure = go.Figure(
        data=tuple(
            go.Scattergl(
                x=series.positions_xyz[:, 0],
                y=series.positions_xyz[:, 1],
                mode="lines",
                name=series.name,
                line={"width": 2.5, "color": color},
            )
            for series, color in zip(series_list, colors, strict=True)
        )
    )
    apply_standard_xy_layout(figure, title="Trajectory Overlay", xaxis_title="X (m)", yaxis_title="Y (m)")
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
