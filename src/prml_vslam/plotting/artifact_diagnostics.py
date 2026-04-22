"""Plotly builders for persisted artifact diagnostics."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.methods.vista.diagnostics import VistaNativeSlamDiagnostics

from .theme import BLUE, GREEN, ORANGE, PURPLE, RED, apply_standard_xy_layout


def build_native_confidence_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build confidence and valid-pixel-ratio diagnostics over native keyframes."""
    x = diagnostics.keyframe_indices
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=x,
            y=diagnostics.confidence_mean,
            mode="lines",
            name="Mean confidence",
            line={"color": BLUE, "width": 2.4},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=x,
            y=diagnostics.confidence_p90,
            mode="lines",
            name="P90 confidence",
            line={"color": PURPLE, "width": 2.0},
        )
    )
    if diagnostics.confidence_valid_ratio:
        figure.add_trace(
            go.Scatter(
                x=x,
                y=diagnostics.confidence_valid_ratio,
                mode="lines",
                name="Valid ratio",
                yaxis="y2",
                line={"color": GREEN, "width": 2.0},
            )
        )
    apply_standard_xy_layout(
        figure,
        title="Native Confidence",
        xaxis_title="Keyframe index",
        yaxis_title="Confidence",
    )
    figure.update_layout(
        yaxis2={
            "title": "Valid ratio",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
        }
    )
    return figure


def build_native_scale_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build native scale estimates over keyframes."""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=diagnostics.keyframe_indices,
            y=diagnostics.scales,
            mode="lines",
            name="Scale",
            line={"color": ORANGE, "width": 2.4},
        )
    )
    apply_standard_xy_layout(figure, title="Native Scale", xaxis_title="Keyframe index", yaxis_title="Scale")
    return figure


def build_native_intrinsics_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build native intrinsics drift over keyframes."""
    figure = go.Figure()
    for name, values, color in (
        ("fx", diagnostics.fx, BLUE),
        ("fy", diagnostics.fy, GREEN),
        ("cx", diagnostics.cx, ORANGE),
        ("cy", diagnostics.cy, PURPLE),
    ):
        figure.add_trace(
            go.Scatter(
                x=diagnostics.keyframe_indices,
                y=values,
                mode="lines",
                name=name,
                line={"color": color, "width": 2.0},
            )
        )
    apply_standard_xy_layout(
        figure,
        title="Native Intrinsics",
        xaxis_title="Keyframe index",
        yaxis_title="Pixels",
    )
    return figure


def build_intrinsics_residual_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build model-raster estimated-vs-reference intrinsics residuals."""
    if diagnostics.intrinsics_comparison is None:
        raise ValueError("Intrinsics comparison diagnostics are not available.")
    comparison = diagnostics.intrinsics_comparison
    x = diagnostics.keyframe_indices
    figure = go.Figure()
    for name, values, color in (
        ("fx residual", comparison.fx_residual_px, BLUE),
        ("fy residual", comparison.fy_residual_px, GREEN),
        ("cx residual", comparison.cx_residual_px, ORANGE),
        ("cy residual", comparison.cy_residual_px, PURPLE),
    ):
        figure.add_trace(
            go.Scatter(
                x=x,
                y=values,
                mode="lines",
                name=name,
                line={"color": color, "width": 2.0},
            )
        )
    apply_standard_xy_layout(
        figure,
        title="Model-Raster Intrinsics Residuals",
        xaxis_title="Keyframe index",
        yaxis_title="Estimate - reference (px)",
    )
    figure.add_hline(y=0.0, line_dash="dash", line_color="#6b7280")
    return figure


def build_native_timing_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build native trajectory step distance and normalized TUM timestamp spacing."""
    figure = go.Figure()
    if diagnostics.native_step_distance_m:
        figure.add_trace(
            go.Scatter(
                x=diagnostics.keyframe_indices[1:],
                y=diagnostics.native_step_distance_m,
                mode="lines",
                name="Native step distance",
                line={"color": RED, "width": 2.2},
            )
        )
    if diagnostics.slam_sample_intervals_s:
        figure.add_trace(
            go.Scatter(
                x=np.arange(1, len(diagnostics.slam_sample_intervals_s) + 1, dtype=np.int64),
                y=diagnostics.slam_sample_intervals_s,
                mode="lines",
                name="TUM sample interval",
                yaxis="y2",
                line={"color": BLUE, "width": 2.0},
            )
        )
    apply_standard_xy_layout(
        figure,
        title="Trajectory Step And Timing",
        xaxis_title="Sample index",
        yaxis_title="Native step distance (m)",
    )
    figure.update_layout(
        yaxis2={
            "title": "TUM interval (s)",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
        }
    )
    return figure


def build_view_graph_figure(diagnostics: VistaNativeSlamDiagnostics) -> go.Figure:
    """Build view-graph degree and edge-gap diagnostics."""
    if diagnostics.view_graph is None:
        raise ValueError("Native view-graph diagnostics are not available.")
    view_graph = diagnostics.view_graph
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=np.arange(len(view_graph.degree_by_node), dtype=np.int64),
            y=view_graph.degree_by_node,
            name="Node degree",
            marker={"color": BLUE},
        )
    )
    if view_graph.edge_gaps:
        figure.add_trace(
            go.Scatter(
                x=np.arange(len(view_graph.edge_gaps), dtype=np.int64),
                y=view_graph.edge_gaps,
                mode="markers",
                name="Edge frame gap",
                yaxis="y2",
                marker={"color": ORANGE, "size": 5},
            )
        )
    apply_standard_xy_layout(
        figure,
        title="View Graph",
        xaxis_title="Node or edge index",
        yaxis_title="Node degree",
    )
    figure.update_layout(
        yaxis2={
            "title": "Edge frame gap",
            "overlaying": "y",
            "side": "right",
            "rangemode": "tozero",
        }
    )
    return figure


__all__ = [
    "build_native_confidence_figure",
    "build_intrinsics_residual_figure",
    "build_native_intrinsics_figure",
    "build_native_scale_figure",
    "build_native_timing_figure",
    "build_view_graph_figure",
]
