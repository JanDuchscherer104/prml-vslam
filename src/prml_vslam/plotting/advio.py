"""Plotly figure builders for the ADVIO dataset page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.sources.datasets.advio import (
    AdvioEnvironment,
    AdvioLocalSceneStatus,
    AdvioPeopleLevel,
    AdvioPoseFrameMode,
    AdvioPoseSource,
)
from prml_vslam.sources.datasets.advio.advio_replay_adapter import serve_loaded_advio_trajectory

from .theme import BLUE, GRAY, GREEN, ORANGE, PURPLE, RED, apply_standard_xy_layout

_INDOOR_COLOR = BLUE
_OUTDOOR_COLOR = ORANGE
_LOCAL_COLOR = GREEN
_OFFLINE_COLOR = PURPLE
_FEATURE_COLOR = RED
_NEUTRAL_COLOR = GRAY
_CROWD_COLORS = {
    AdvioPeopleLevel.NONE: "#94a3b8",
    AdvioPeopleLevel.LOW: GREEN,
    AdvioPeopleLevel.MODERATE: ORANGE,
    AdvioPeopleLevel.HIGH: RED,
}


def build_scene_mix_figure(statuses: list[AdvioLocalSceneStatus]) -> go.Figure:
    """Build a stacked venue/environment overview for the catalog."""
    venues = np.asarray([status.scene.venue for status in statuses], dtype=object)
    environments = np.asarray([status.scene.environment for status in statuses], dtype=object)
    unique_venues, inverse = np.unique(venues, return_inverse=True)
    venue_counts = np.bincount(inverse, minlength=len(unique_venues))
    ordered_venues = [
        venue
        for _, venue in sorted(
            zip(venue_counts.tolist(), unique_venues.tolist(), strict=True),
            key=lambda item: (-item[0], item[1]),
        )
    ]

    figure = go.Figure()
    for environment, color in (
        (AdvioEnvironment.INDOOR, _INDOOR_COLOR),
        (AdvioEnvironment.OUTDOOR, _OUTDOOR_COLOR),
    ):
        counts = [int(np.sum((venues == venue) & (environments == environment))) for venue in ordered_venues]
        figure.add_bar(
            x=ordered_venues,
            y=counts,
            name=environment.label,
            marker_color=color,
        )

    apply_standard_xy_layout(figure, title="Scene Mix by Venue", xaxis_title="Venue", yaxis_title="Scenes")
    figure.update_layout(barmode="stack")
    figure.update_xaxes(tickangle=-30)
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def build_local_readiness_figure(statuses: list[AdvioLocalSceneStatus]) -> go.Figure:
    """Build a high-level local availability summary."""
    total = len(statuses)
    values = np.asarray(
        [
            total,
            sum(status.sequence_dir is not None for status in statuses),
            sum(status.replay_ready for status in statuses),
            sum(status.offline_ready for status in statuses),
        ],
        dtype=np.int64,
    )
    labels = ["Catalog", "Local", "Replay Ready", "Offline Ready"]
    colors = [_NEUTRAL_COLOR, _LOCAL_COLOR, _INDOOR_COLOR, _OFFLINE_COLOR]
    texts = [
        f"{value}" if index == 0 or total == 0 else f"{value} ({(100.0 * value / total):.0f}%)"
        for index, value in enumerate(values.tolist())
    ]

    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=texts,
            textposition="outside",
        )
    )
    apply_standard_xy_layout(
        figure,
        title="Local Readiness",
        xaxis_title="Category",
        yaxis_title="Scenes",
        showlegend=False,
    )
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def build_crowd_density_figure(statuses: list[AdvioLocalSceneStatus]) -> go.Figure:
    """Build a crowd-density composition chart."""
    levels = list(AdvioPeopleLevel)
    values = np.asarray(
        [sum(status.scene.people_level is level for status in statuses) for level in levels],
        dtype=np.int64,
    )
    figure = go.Figure(
        go.Pie(
            labels=[level.label for level in levels],
            values=values,
            hole=0.55,
            sort=False,
            marker={"colors": [_CROWD_COLORS[level] for level in levels]},
        )
    )
    apply_standard_xy_layout(figure, title="Crowd Density", xaxis_title="Category", yaxis_title="Scenes")
    return figure


def build_scene_attribute_figure(statuses: list[AdvioLocalSceneStatus]) -> go.Figure:
    """Build a scene-attribute prevalence chart."""
    labels = ["Stairs", "Escalator", "Elevator", "Vehicles"]
    values = np.asarray(
        [
            sum(status.scene.has_stairs for status in statuses),
            sum(status.scene.has_escalator for status in statuses),
            sum(status.scene.has_elevator for status in statuses),
            sum(status.scene.has_vehicles for status in statuses),
        ],
        dtype=np.int64,
    )
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=_FEATURE_COLOR,
            text=values,
            textposition="outside",
        )
    )
    apply_standard_xy_layout(
        figure,
        title="Scene Attributes",
        xaxis_title="Scenes",
        yaxis_title="Attribute",
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True, rangemode="tozero")
    return figure


def build_advio_comparison_trajectories(
    *,
    ground_truth: PoseTrajectory3D,
    arcore: PoseTrajectory3D,
    arkit: PoseTrajectory3D | None,
    pose_frame_mode: AdvioPoseFrameMode,
) -> list[tuple[str, PoseTrajectory3D]]:
    """Build ADVIO explorer overlays with explicit comparison semantics."""
    trajectories: list[tuple[str, PoseTrajectory3D]] = [("Ground Truth", ground_truth)]
    trajectories.append(
        (
            "ARCore",
            serve_loaded_advio_trajectory(
                trajectory=arcore,
                ground_truth_trajectory=ground_truth,
                pose_source=AdvioPoseSource.ARCORE,
                pose_frame_mode=pose_frame_mode,
            ),
        )
    )
    if arkit is not None:
        trajectories.append(
            (
                "ARKit",
                serve_loaded_advio_trajectory(
                    trajectory=arkit,
                    ground_truth_trajectory=ground_truth,
                    pose_source=AdvioPoseSource.ARKIT,
                    pose_frame_mode=pose_frame_mode,
                ),
            )
        )
    return trajectories


__all__ = [
    "build_advio_comparison_trajectories",
    "build_crowd_density_figure",
    "build_local_readiness_figure",
    "build_scene_attribute_figure",
    "build_scene_mix_figure",
]
