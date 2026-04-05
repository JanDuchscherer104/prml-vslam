"""Plotly figure builders for the Record3D page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from jaxtyping import Float

from .theme import BLUE, GREEN, RED, apply_standard_3d_layout


def build_live_trajectory_figure(
    positions_xyz: Float[np.ndarray, "num_points 3"],  # noqa: F722
    timestamps_s: Float[np.ndarray, "num_points"] | None = None,  # noqa: F821, F722, UP037
) -> go.Figure:
    """Build a compact 3D ego-trajectory figure for live Record3D poses."""
    figure = go.Figure()
    hover_text = None
    if timestamps_s is not None and len(timestamps_s) == len(positions_xyz):
        hover_text = [f"t={timestamp:.3f}s" for timestamp in timestamps_s]

    figure.add_trace(
        go.Scatter3d(
            x=positions_xyz[:, 0],
            y=positions_xyz[:, 1],
            z=positions_xyz[:, 2],
            mode="lines+markers",
            name="Ego trajectory",
            line={"width": 5, "color": BLUE},
            marker={"size": 3, "color": BLUE},
            text=hover_text,
            hovertemplate="x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<br>%{text}<extra></extra>"
            if hover_text is not None
            else "x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[positions_xyz[0, 0]],
            y=[positions_xyz[0, 1]],
            z=[positions_xyz[0, 2]],
            mode="markers",
            name="Start",
            marker={"size": 5, "color": GREEN},
            hovertemplate="Start<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter3d(
            x=[positions_xyz[-1, 0]],
            y=[positions_xyz[-1, 1]],
            z=[positions_xyz[-1, 2]],
            mode="markers",
            name="Current",
            marker={"size": 6, "color": RED},
            hovertemplate="Current pose<extra></extra>",
        )
    )
    apply_standard_3d_layout(
        figure,
        title="Ego Trajectory",
        scene={
            "xaxis_title": "X (m)",
            "yaxis_title": "Y (m)",
            "zaxis_title": "Z (m)",
            "aspectmode": "data",
        },
    )
    return figure


__all__ = ["build_live_trajectory_figure"]
