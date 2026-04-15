"""Plotly figure builders for pipeline-demo-specific visualizations."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.eval.contracts import ErrorSeries, TrajectorySeries
from prml_vslam.utils.image_utils import normalize_grayscale_image

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


def pointmap_preview_image(pointmap: np.ndarray | None) -> np.ndarray | None:
    """Return a renderable preview image for one pointmap-like preview artifact."""
    if pointmap is None:
        return None
    preview_array = np.asarray(pointmap)
    if preview_array.size == 0:
        return None
    if preview_array.ndim == 2:
        return normalize_grayscale_image(np.asarray(preview_array, dtype=np.float32))
    if preview_array.ndim != 3:
        return None
    if preview_array.shape[-1] == 1:
        return normalize_grayscale_image(np.asarray(preview_array[..., 0], dtype=np.float32))
    if preview_array.shape[-1] in {3, 4} and (
        np.issubdtype(preview_array.dtype, np.integer)
        or (np.isfinite(preview_array).all() and np.nanmin(preview_array) >= 0.0 and np.nanmax(preview_array) <= 1.0)
    ):
        return np.asarray(preview_array)
    magnitude = np.linalg.norm(np.asarray(preview_array, dtype=np.float32), axis=-1)
    return normalize_grayscale_image(magnitude)


def preview_image_from_update(update: object) -> np.ndarray | None:
    """Return the retained preview image for one streaming SLAM update-like object."""
    if update is None:
        return None
    preview_rgb = getattr(update, "preview_rgb", None)
    if preview_rgb is not None and np.asarray(preview_rgb).size > 0:
        return np.asarray(preview_rgb)
    return pointmap_preview_image(getattr(update, "pointmap", None))


__all__ = ["build_evo_ape_colormap_figure", "pointmap_preview_image", "preview_image_from_update"]
