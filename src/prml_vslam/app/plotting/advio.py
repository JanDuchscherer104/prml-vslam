"""Plotly figure builders for the ADVIO dataset page."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from prml_vslam.datasets import AdvioEnvironment, AdvioLocalSceneStatus, AdvioPeopleLevel

_INDOOR_COLOR = "#1368ce"
_OUTDOOR_COLOR = "#ef6c00"
_LOCAL_COLOR = "#0f9d58"
_OFFLINE_COLOR = "#7b1fa2"
_FEATURE_COLOR = "#c62828"
_NEUTRAL_COLOR = "#6b7280"
_CROWD_COLORS = {
    AdvioPeopleLevel.NONE: "#94a3b8",
    AdvioPeopleLevel.LOW: "#0f9d58",
    AdvioPeopleLevel.MODERATE: "#ef6c00",
    AdvioPeopleLevel.HIGH: "#c62828",
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

    figure.update_layout(
        title="Scene Mix by Venue",
        barmode="stack",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
        xaxis_title="Venue",
        yaxis_title="Scenes",
    )
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
            sum(status.full_ready for status in statuses),
        ],
        dtype=np.int64,
    )
    labels = ["Catalog", "Local", "Replay Ready", "Offline Ready", "Full Ready"]
    colors = [_NEUTRAL_COLOR, _LOCAL_COLOR, _INDOOR_COLOR, _OFFLINE_COLOR, _FEATURE_COLOR]
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
    figure.update_layout(
        title="Local Readiness",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
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
    figure.update_layout(
        title="Crowd Density",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
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
    figure.update_layout(
        title="Scene Attributes",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        xaxis_title="Scenes",
        yaxis_title="Attribute",
        showlegend=False,
    )
    figure.update_xaxes(showgrid=True, rangemode="tozero")
    return figure


__all__ = [
    "build_crowd_density_figure",
    "build_local_readiness_figure",
    "build_scene_attribute_figure",
    "build_scene_mix_figure",
]
