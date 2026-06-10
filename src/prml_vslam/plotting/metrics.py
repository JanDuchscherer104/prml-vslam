"""Plotly figure builders for the metrics page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.eval.contracts import CloudMetricId, DenseCloudEvaluationArtifact, ErrorSeries, TrajectorySeries

from .theme import BLUE, DEFAULT_COLORS, GREEN, ORANGE, PURPLE, apply_standard_xy_layout
from .trajectories import _add_xy_trajectory_trace, _apply_standard_trajectory_xy_layout


def build_trajectory_figure(series_list: list[TrajectorySeries]) -> go.Figure:
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


def build_cloud_distance_metrics_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build grouped bars for distance-valued point-cloud metrics."""
    metric_specs = (
        (CloudMetricId.ACCURACY, "Accuracy"),
        (CloudMetricId.COMPLETENESS, "Completeness"),
        (CloudMetricId.CHAMFER, "Chamfer"),
    )
    figure = go.Figure()
    colors = (BLUE, ORANGE, GREEN)
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    for (metric_id, label), color in zip(metric_specs, colors, strict=True):
        figure.add_bar(
            x=estimate_labels,
            y=[estimate.metrics.get(metric_id) for estimate in artifact.estimates],
            name=label,
            marker_color=color,
            hovertemplate="%{x}<br>%{fullData.name}: %{y:.4f} m<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Point-Cloud Distance Metrics",
        xaxis_title="Estimate",
        yaxis_title="Distance (m)",
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_cloud_quality_metrics_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build bars for thresholded F1 and ICP fitness scores."""
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    figure = go.Figure()
    figure.add_bar(
        x=estimate_labels,
        y=[estimate.metrics.get(CloudMetricId.F1) for estimate in artifact.estimates],
        name=f"F1 @ {artifact.f1_threshold_m:.2f} m",
        marker_color=PURPLE,
        hovertemplate="%{x}<br>%{fullData.name}: %{y:.3f}<extra></extra>",
    )
    icp_fitness = [estimate.metrics.get(CloudMetricId.ICP_FITNESS) for estimate in artifact.estimates]
    if any(value is not None for value in icp_fitness):
        figure.add_bar(
            x=estimate_labels,
            y=icp_fitness,
            name="ICP fitness",
            marker_color=GREEN,
            hovertemplate="%{x}<br>%{fullData.name}: %{y:.3f}<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Point-Cloud Quality Scores",
        xaxis_title="Estimate",
        yaxis_title="Score",
    )
    figure.update_layout(barmode="group")
    figure.update_yaxes(range=[0.0, 1.0], showgrid=True)
    return figure


def build_cloud_point_count_figure(artifact: DenseCloudEvaluationArtifact) -> go.Figure:
    """Build a compact point-count comparison for evaluated clouds."""
    estimate_labels = [_estimate_label(estimate.estimate_kind.value) for estimate in artifact.estimates]
    figure = go.Figure(
        go.Bar(
            x=estimate_labels,
            y=[estimate.estimate_point_count for estimate in artifact.estimates],
            name="Estimate points",
            marker_color=BLUE,
            hovertemplate="%{x}<br>Estimate points: %{y:,}<extra></extra>",
        )
    )
    if artifact.estimates:
        figure.add_scatter(
            x=estimate_labels,
            y=[artifact.estimates[0].reference_point_count] * len(estimate_labels),
            mode="lines+markers",
            name="Reference points",
            line={"color": ORANGE, "width": 2.0, "dash": "dot"},
            hovertemplate="Reference points: %{y:,}<extra></extra>",
        )
    apply_standard_xy_layout(
        figure,
        title="Evaluated Point Counts",
        xaxis_title="Estimate",
        yaxis_title="Points",
    )
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def _estimate_label(value: str) -> str:
    return {
        "sim3": "Sim3",
        "sim3_icp": "Sim3 + ICP",
        "reconstruction": "Reconstruction",
    }.get(value, value.replace("_", " ").title())
