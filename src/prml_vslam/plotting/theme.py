"""Shared Plotly theme helpers for the packaged Streamlit app."""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go

BLUE = "#1368ce"
ORANGE = "#ef6c00"
GREEN = "#0f9d58"
RED = "#c62828"
PURPLE = "#7b1fa2"
GRAY = "#6b7280"
DEFAULT_COLORS = np.asarray((BLUE, ORANGE, GREEN, RED), dtype=object)
AXIS_COLORS = {"x": RED, "y": GREEN, "z": BLUE}
STANDARD_MARGIN = {"l": 24, "r": 16, "t": 72, "b": 24}
LEGEND_MARGIN = {"l": 24, "r": 16, "t": 120, "b": 24}
COMPACT_3D_MARGIN = {"l": 0, "r": 0, "t": 72, "b": 0}
HORIZONTAL_LEGEND = {"orientation": "h", "yanchor": "bottom", "y": 1.08, "x": 0}


def apply_standard_xy_layout(
    figure: go.Figure,
    *,
    title: str,
    xaxis_title: str,
    yaxis_title: str,
    showlegend: bool = True,
) -> go.Figure:
    """Apply the shared 2D layout used across workbench figures."""
    figure.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        margin=LEGEND_MARGIN if showlegend else STANDARD_MARGIN,
        legend=HORIZONTAL_LEGEND if showlegend else None,
        showlegend=showlegend,
    )
    return figure


def apply_standard_3d_layout(
    figure: go.Figure,
    *,
    title: str,
    scene: dict[str, Any],
    showlegend: bool = True,
) -> go.Figure:
    """Apply the shared 3D layout used across workbench figures."""
    figure.update_layout(
        title=title,
        margin=COMPACT_3D_MARGIN,
        legend=HORIZONTAL_LEGEND if showlegend else None,
        showlegend=showlegend,
        scene=scene,
    )
    return figure


__all__ = [
    "AXIS_COLORS",
    "BLUE",
    "DEFAULT_COLORS",
    "GRAY",
    "GREEN",
    "ORANGE",
    "PURPLE",
    "RED",
    "apply_standard_3d_layout",
    "apply_standard_xy_layout",
]
