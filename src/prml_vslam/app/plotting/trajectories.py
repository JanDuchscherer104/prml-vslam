"""Reusable trajectory plotting helpers for dataset and evaluation pages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
import plotly.graph_objects as go

from prml_vslam.interfaces import SE3Pose, TimedPoseTrajectory

_DEFAULT_COLORS = np.asarray(("#1368ce", "#ef6c00", "#0f9d58", "#c62828"), dtype=object)
_AXIS_COLORS = {
    "x": "#c62828",
    "y": "#0f9d58",
    "z": "#1368ce",
}


def build_bev_trajectory_figure(
    trajectories: Sequence[tuple[str, TimedPoseTrajectory]],
    *,
    title: str = "BEV Trajectory Overlay",
) -> go.Figure:
    """Build a bird's-eye trajectory overlay for one or more trajectories."""
    builder = TrajectoryPlotBuilder(mode="bev", title=title)
    for index, (name, trajectory) in enumerate(trajectories):
        builder.add_trajectory(trajectory, name=name, color=str(_DEFAULT_COLORS[index % len(_DEFAULT_COLORS)]))
    return builder.finalize()


def build_3d_trajectory_figure(
    trajectories: Sequence[tuple[str, TimedPoseTrajectory]],
    *,
    title: str = "3D Trajectory Overlay",
    pose_axes_name: str | None = None,
    pose_axis_stride: int = 30,
) -> go.Figure:
    """Build a 3D trajectory overlay and optional sampled pose axes."""
    builder = TrajectoryPlotBuilder(mode="3d", title=title)
    for index, (name, trajectory) in enumerate(trajectories):
        color = str(_DEFAULT_COLORS[index % len(_DEFAULT_COLORS)])
        builder.add_trajectory(trajectory, name=name, color=color)
        if pose_axes_name == name:
            builder.add_pose_axes(trajectory, stride=pose_axis_stride, axis_length_m=0.15)
    return builder.finalize()


def build_speed_profile_figure(
    trajectories: Sequence[tuple[str, TimedPoseTrajectory]],
    *,
    title: str = "Translational Speed",
) -> go.Figure:
    """Build a per-trajectory speed-over-time figure."""
    figure = go.Figure()
    for index, (name, trajectory) in enumerate(trajectories):
        timestamps_s, speeds_mps = _trajectory_speed_profile(trajectory)
        if len(timestamps_s) == 0:
            continue
        figure.add_trace(
            go.Scattergl(
                x=timestamps_s,
                y=speeds_mps,
                mode="lines",
                name=name,
                line={"width": 2.2, "color": str(_DEFAULT_COLORS[index % len(_DEFAULT_COLORS)])},
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="Timestamp (s)",
        yaxis_title="Speed (m/s)",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def build_height_profile_figure(
    trajectories: Sequence[tuple[str, TimedPoseTrajectory]],
    *,
    title: str = "Height Profile",
) -> go.Figure:
    """Build a Z-over-time profile for one or more trajectories."""
    figure = go.Figure()
    for index, (name, trajectory) in enumerate(trajectories):
        figure.add_trace(
            go.Scattergl(
                x=trajectory.timestamps_s,
                y=trajectory.positions_xyz[:, 2],
                mode="lines",
                name=name,
                line={"width": 2.2, "color": str(_DEFAULT_COLORS[index % len(_DEFAULT_COLORS)])},
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="Timestamp (s)",
        yaxis_title="Z (m)",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True)
    return figure


def build_sample_interval_figure(
    series: Sequence[tuple[str, np.ndarray]],
    *,
    title: str = "Sampling Intervals",
) -> go.Figure:
    """Build a per-series timestamp-spacing profile in milliseconds."""
    figure = go.Figure()
    for index, (name, timestamps_s) in enumerate(series):
        intervals_ms = _sample_intervals_ms(timestamps_s)
        if len(intervals_ms) == 0:
            continue
        figure.add_trace(
            go.Scattergl(
                x=np.arange(1, len(intervals_ms) + 1, dtype=np.int64),
                y=intervals_ms,
                mode="lines",
                name=name,
                line={"width": 2.0, "color": str(_DEFAULT_COLORS[index % len(_DEFAULT_COLORS)])},
            )
        )
    figure.update_layout(
        title=title,
        xaxis_title="Sample Index",
        yaxis_title="Delta t (ms)",
        margin={"l": 24, "r": 16, "t": 44, "b": 24},
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def trajectory_length_m(trajectory: TimedPoseTrajectory) -> float:
    """Return the total path length in metres."""
    if len(trajectory.positions_xyz) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(trajectory.positions_xyz, axis=0), axis=1).sum())


class TrajectoryPlotBuilder:
    """Lightweight builder for BEV and 3D trajectory views."""

    def __init__(self, *, mode: Literal["bev", "3d"], title: str) -> None:
        self.mode = mode
        self.title = title
        self.figure = go.Figure()

    def add_trajectory(
        self,
        trajectory: TimedPoseTrajectory,
        *,
        name: str,
        color: str,
    ) -> TrajectoryPlotBuilder:
        """Add one trajectory trace with start and end markers."""
        positions = trajectory.positions_xyz
        if len(positions) == 0:
            return self

        if self.mode == "bev":
            self.figure.add_trace(
                go.Scattergl(
                    x=positions[:, 0],
                    y=positions[:, 1],
                    mode="lines",
                    name=name,
                    line={"width": 2.8, "color": color},
                )
            )
            self.figure.add_trace(
                go.Scattergl(
                    x=[positions[0, 0]],
                    y=[positions[0, 1]],
                    mode="markers",
                    name=f"{name} start",
                    marker={"size": 7, "color": color, "symbol": "circle"},
                    showlegend=False,
                )
            )
            self.figure.add_trace(
                go.Scattergl(
                    x=[positions[-1, 0]],
                    y=[positions[-1, 1]],
                    mode="markers",
                    name=f"{name} end",
                    marker={"size": 8, "color": color, "symbol": "x"},
                    showlegend=False,
                )
            )
        else:
            self.figure.add_trace(
                go.Scatter3d(
                    x=positions[:, 0],
                    y=positions[:, 1],
                    z=positions[:, 2],
                    mode="lines",
                    name=name,
                    line={"width": 5, "color": color},
                )
            )
            self.figure.add_trace(
                go.Scatter3d(
                    x=[positions[0, 0]],
                    y=[positions[0, 1]],
                    z=[positions[0, 2]],
                    mode="markers",
                    name=f"{name} start",
                    marker={"size": 4, "color": color, "symbol": "circle"},
                    showlegend=False,
                )
            )
            self.figure.add_trace(
                go.Scatter3d(
                    x=[positions[-1, 0]],
                    y=[positions[-1, 1]],
                    z=[positions[-1, 2]],
                    mode="markers",
                    name=f"{name} end",
                    marker={"size": 5, "color": color, "symbol": "diamond"},
                    showlegend=False,
                )
            )
        return self

    def add_pose_axes(
        self,
        trajectory: TimedPoseTrajectory,
        *,
        stride: int,
        axis_length_m: float,
    ) -> TrajectoryPlotBuilder:
        """Add sampled local pose axes for a 3D trajectory."""
        if self.mode != "3d" or len(trajectory.positions_xyz) == 0:
            return self

        indices = np.arange(0, len(trajectory.positions_xyz), max(stride, 1), dtype=np.int64)
        if indices[-1] != len(trajectory.positions_xyz) - 1:
            indices = np.concatenate([indices, np.array([len(trajectory.positions_xyz) - 1], dtype=np.int64)])

        axis_segments = {axis_name: [] for axis_name in _AXIS_COLORS}
        basis = {
            "x": np.array([axis_length_m, 0.0, 0.0], dtype=np.float64),
            "y": np.array([0.0, axis_length_m, 0.0], dtype=np.float64),
            "z": np.array([0.0, 0.0, axis_length_m], dtype=np.float64),
        }

        for index in indices.tolist():
            pose = SE3Pose(
                qx=float(trajectory.quaternions_xyzw[index, 0]),
                qy=float(trajectory.quaternions_xyzw[index, 1]),
                qz=float(trajectory.quaternions_xyzw[index, 2]),
                qw=float(trajectory.quaternions_xyzw[index, 3]),
                tx=float(trajectory.positions_xyz[index, 0]),
                ty=float(trajectory.positions_xyz[index, 1]),
                tz=float(trajectory.positions_xyz[index, 2]),
            )
            transform = pose.as_matrix()
            origin = transform[:3, 3]
            rotation = transform[:3, :3]
            for axis_name, axis_vector in basis.items():
                endpoint = origin + rotation @ axis_vector
                axis_segments[axis_name].append(np.vstack([origin, endpoint, np.full(3, np.nan, dtype=np.float64)]))

        for axis_name, segments in axis_segments.items():
            if not segments:
                continue
            flattened = np.concatenate(segments, axis=0)
            self.figure.add_trace(
                go.Scatter3d(
                    x=flattened[:, 0],
                    y=flattened[:, 1],
                    z=flattened[:, 2],
                    mode="lines",
                    name=f"{axis_name.upper()} axis",
                    line={"width": 2, "color": _AXIS_COLORS[axis_name]},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        return self

    def finalize(self) -> go.Figure:
        """Finalize the figure layout and return it."""
        if self.mode == "bev":
            self.figure.update_layout(
                title=self.title,
                margin={"l": 24, "r": 16, "t": 44, "b": 24},
                legend={"orientation": "h", "y": 1.12, "x": 0},
                xaxis_title="X (m)",
                yaxis_title="Y (m)",
            )
            self.figure.update_xaxes(showgrid=True)
            self.figure.update_yaxes(showgrid=True, scaleanchor="x", scaleratio=1)
        else:
            self.figure.update_layout(
                title=self.title,
                margin={"l": 0, "r": 0, "t": 44, "b": 0},
                legend={"orientation": "h", "y": 1.02, "x": 0},
                scene={
                    "xaxis_title": "X (m)",
                    "yaxis_title": "Y (m)",
                    "zaxis_title": "Z (m)",
                    "aspectmode": "data",
                },
            )
        return self.figure


def _trajectory_speed_profile(trajectory: TimedPoseTrajectory) -> tuple[np.ndarray, np.ndarray]:
    if len(trajectory.timestamps_s) < 2:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    delta_t_s = np.diff(trajectory.timestamps_s)
    finite_mask = delta_t_s > 0.0
    if not np.any(finite_mask):
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)
    delta_position_m = np.linalg.norm(np.diff(trajectory.positions_xyz, axis=0), axis=1)
    timestamps_s = trajectory.timestamps_s[1:][finite_mask]
    speeds_mps = delta_position_m[finite_mask] / delta_t_s[finite_mask]
    return timestamps_s, speeds_mps


def _sample_intervals_ms(timestamps_s: np.ndarray) -> np.ndarray:
    if len(timestamps_s) < 2:
        return np.empty(0, dtype=np.float64)
    delta_t_s = np.diff(np.asarray(timestamps_s, dtype=np.float64))
    return delta_t_s[delta_t_s >= 0.0] * 1e3


__all__ = [
    "TrajectoryPlotBuilder",
    "build_3d_trajectory_figure",
    "build_bev_trajectory_figure",
    "build_height_profile_figure",
    "build_sample_interval_figure",
    "build_speed_profile_figure",
    "trajectory_length_m",
]
