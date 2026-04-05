"""Plotly figure builders for pipeline-demo-specific visualizations."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.eval.contracts import ErrorSeries, TrajectorySeries

from .theme import BLUE, GRAY
from .trajectories import _add_3d_trajectory_trace, _apply_standard_trajectory_3d_layout


def build_evo_ape_colormap_figure(
    *,
    reference: TrajectorySeries,
    estimate: TrajectorySeries,
    error_series: ErrorSeries,
) -> go.Figure:
    """Build a 3D trajectory overlay with `evo` APE shown as a color map."""
    matched_pairs = min(len(estimate.positions_xyz), len(error_series.values))
    if matched_pairs == 0:
        raise ValueError("Expected at least one matched pose/error pair for evo APE plotting.")

    estimate_positions_xyz = estimate.positions_xyz[:matched_pairs]
    error_values = np.asarray(error_series.values[:matched_pairs], dtype=np.float64)
    color_min = float(error_values.min())
    color_max = float(error_values.max())
    if color_min == color_max:
        color_max = color_min + 1e-6

    figure = go.Figure()
    _add_3d_trajectory_trace(
        figure,
        reference.positions_xyz,
        name="Reference",
        line={"width": 4, "color": GRAY, "dash": "dash"},
        hovertemplate="Reference<br>x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<extra></extra>",
    )
    _add_3d_trajectory_trace(
        figure,
        estimate_positions_xyz,
        name="Estimate",
        line={"width": 3, "color": BLUE},
        opacity=0.35,
        hovertemplate="Estimate<br>x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<extra></extra>",
    )
    figure.add_trace(
        go.Scatter3d(
            x=estimate_positions_xyz[:, 0],
            y=estimate_positions_xyz[:, 1],
            z=estimate_positions_xyz[:, 2],
            mode="markers",
            name="APE (m)",
            marker={
                "size": 4,
                "color": error_values,
                "colorscale": "Turbo",
                "cmin": color_min,
                "cmax": color_max,
                "colorbar": {"title": "APE (m)"},
            },
            hovertemplate=("APE=%{marker.color:.4f} m<br>x=%{x:.3f} m<br>y=%{y:.3f} m<br>z=%{z:.3f} m<extra></extra>"),
        )
    )
    _apply_standard_trajectory_3d_layout(figure, title="Evo APE Trajectory Colormap")
    return figure


__all__ = ["build_evo_ape_colormap_figure"]
