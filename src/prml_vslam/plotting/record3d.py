"""Plotly figure builders for the Record3D page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from jaxtyping import Float

from .theme import BLUE, GREEN, RED
from .trajectories import _add_3d_end_markers, _add_3d_trajectory_trace, _apply_standard_trajectory_3d_layout


def build_live_trajectory_figure(
    positions_xyz: Float[np.ndarray, "num_points 3"],  # noqa: F722
    timestamps_s: Float[np.ndarray, "num_points"] | None = None,  # noqa: F821, F722, UP037
) -> go.Figure:
    """Build a compact 3D ego-trajectory figure for live Record3D poses."""
    figure = go.Figure()
    hover_text = None
    if timestamps_s is not None and len(timestamps_s) == len(positions_xyz):
        hover_text = [f"t={timestamp:.3f}s" for timestamp in timestamps_s]

    _add_3d_trajectory_trace(
        figure,
        positions_xyz,
        name="Ego trajectory",
        mode="lines+markers",
        line={"width": 5, "color": BLUE},
        marker={"size": 3, "color": BLUE},
        text=hover_text,
        hovertemplate="x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<br>%{text}<extra></extra>"
        if hover_text is not None
        else "x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<extra></extra>",
    )
    _add_3d_end_markers(
        figure,
        positions_xyz,
        start_name="Start",
        end_name="Current",
        start_marker={"size": 5, "color": GREEN},
        end_marker={"size": 6, "color": RED},
        start_hovertemplate="Start<extra></extra>",
        end_hovertemplate="Current pose<extra></extra>",
        showlegend=True,
    )
    _apply_standard_trajectory_3d_layout(figure, title="Ego Trajectory")
    return figure


__all__ = ["build_live_trajectory_figure"]
