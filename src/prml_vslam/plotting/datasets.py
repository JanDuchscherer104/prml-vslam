"""Plotly figure builders for normalized dataset analysis tables."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors

from .theme import (
    BLUE,
    DEFAULT_COLORS,
    GREEN,
    ORANGE,
    apply_standard_3d_layout,
    apply_standard_xy_layout,
)


def build_payload_footprint_figure(frame: pd.DataFrame) -> go.Figure:
    """Build a stacked payload-size chart from normalized footprint rows."""
    figure = go.Figure()
    if not frame.empty:
        labels = frame["Sequence"].astype(str) + "<br>" + frame["Profile"].astype(str).str.slice(0, 8)
        for column, color in (("RGB MB", BLUE), ("Depth MB", GREEN), ("Video MB", ORANGE)):
            figure.add_bar(x=labels, y=frame[column], name=column.removesuffix(" MB"), marker_color=color)
    apply_standard_xy_layout(
        figure,
        title="Stored Observation Payload Footprint",
        xaxis_title="Sequence / Profile",
        yaxis_title="Size (MB)",
    )
    figure.update_layout(barmode="stack")
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_observation_metric_figure(
    frame: pd.DataFrame, *, value_column: str, title: str, yaxis_title: str
) -> go.Figure:
    """Build a per-scene observation metric bar chart."""
    figure = go.Figure()
    if not frame.empty and value_column in frame:
        figure.add_bar(
            x=_sequence_labels(frame),
            y=_numeric_column(frame, value_column),
            marker_color=BLUE,
            name=yaxis_title,
        )
    apply_standard_xy_layout(figure, title=title, xaxis_title="Sequence", yaxis_title=yaxis_title, showlegend=False)
    figure.update_xaxes(tickangle=-30)
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_trajectory_metric_figure(
    frame: pd.DataFrame, *, value_column: str, title: str, yaxis_title: str
) -> go.Figure:
    """Build a per-scene trajectory metric bar chart."""
    figure = go.Figure()
    if not frame.empty and value_column in frame:
        subject_series = (
            frame["subject"].astype(str) if "subject" in frame else pd.Series(yaxis_title, index=frame.index)
        )
        for index, subject in enumerate(dict.fromkeys(subject_series)):
            subject_frame = frame.loc[subject_series.eq(subject)]
            sequence_ids = subject_frame["sequence_id"].astype(str)
            figure.add_bar(
                x=sequence_ids,
                y=_numeric_column(subject_frame, value_column),
                marker_color=str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)]),
                name=str(subject),
                hovertemplate=(f"<b>%{{x}}</b><br>Trajectory: {subject}<br>{yaxis_title}: %{{y:.4g}}<extra></extra>"),
            )
    apply_standard_xy_layout(figure, title=title, xaxis_title="Sequence", yaxis_title=yaxis_title, showlegend=True)
    figure.update_layout(barmode="group")
    figure.update_xaxes(tickangle=-20)
    figure.update_yaxes(rangemode="tozero", showgrid=True)
    return figure


def build_reference_cloud_scene_figure(
    *,
    clouds: Sequence[tuple[str, Path]],
    trajectories: Sequence[tuple[str, PoseTrajectory3D]] = (),
    max_points: int = 50_000,
    random_seed: int = 43,
) -> go.Figure:
    """Build a sampled 3D reference-cloud view with optional trajectory overlays."""
    figure = go.Figure()
    for index, (label, path) in enumerate(clouds):
        points_xyz, colors_rgb = load_point_cloud_ply_with_colors(path)
        sampled_points, sampled_colors = _sample_cloud_points(
            points_xyz=points_xyz,
            colors_rgb=colors_rgb,
            max_points=max_points,
            random_seed=random_seed + index,
        )
        marker_color: str | list[str] = str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)])
        if sampled_colors is not None:
            rgb = np.clip(sampled_colors * 255.0, 0.0, 255.0).astype(np.uint8)
            marker_color = [f"rgb({red},{green},{blue})" for red, green, blue in rgb.tolist()]
        figure.add_trace(
            go.Scatter3d(
                x=sampled_points[:, 0],
                y=sampled_points[:, 1],
                z=sampled_points[:, 2],
                mode="markers",
                name=f"{label} ({len(sampled_points):,}/{len(points_xyz):,})",
                marker={"size": 1.4, "color": marker_color, "opacity": 0.55},
            )
        )
    for index, (label, trajectory) in enumerate(trajectories):
        positions = np.asarray(trajectory.positions_xyz, dtype=np.float64)
        if len(positions) == 0:
            continue
        figure.add_trace(
            go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode="lines",
                name=label,
                line={"width": 5, "color": str(DEFAULT_COLORS[(index + len(clouds)) % len(DEFAULT_COLORS)])},
            )
        )
    apply_standard_3d_layout(
        figure,
        title="Reference Cloud",
        scene={
            "xaxis_title": "X (m)",
            "yaxis_title": "Y (m)",
            "zaxis_title": "Z (m)",
            "aspectmode": "data",
        },
    )
    return figure


def _sequence_labels(frame: pd.DataFrame) -> pd.Series:
    labels = frame["sequence_id"].astype(str)
    if "subject" in frame:
        labels = labels + "<br>" + frame["subject"].astype(str)
    return labels


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _sample_cloud_points(
    *,
    points_xyz: np.ndarray,
    colors_rgb: np.ndarray | None,
    max_points: int,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    if max_points <= 0 or len(points_xyz) <= max_points:
        return points_xyz, colors_rgb
    rng = np.random.default_rng(random_seed)
    indices = rng.choice(len(points_xyz), size=max_points, replace=False)
    colors = None if colors_rgb is None else colors_rgb[indices]
    return points_xyz[indices], colors


__all__ = [
    "build_observation_metric_figure",
    "build_payload_footprint_figure",
    "build_reference_cloud_scene_figure",
    "build_trajectory_metric_figure",
]
