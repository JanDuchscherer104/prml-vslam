"""Reusable trajectory plotting helpers for dataset and evaluation pages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
import plotly.graph_objects as go
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.interfaces import FrameTransform

from .theme import AXIS_COLORS, DEFAULT_COLORS, apply_standard_3d_layout, apply_standard_xy_layout


def build_bev_trajectory_figure(
    trajectories: Sequence[tuple[str, PoseTrajectory3D]],
    *,
    title: str = "BEV Trajectory Overlay",
) -> go.Figure:
    """Build a bird's-eye trajectory overlay for one or more trajectories."""
    builder = TrajectoryPlotBuilder(mode="bev", title=title)
    for index, (name, trajectory) in enumerate(trajectories):
        builder.add_trajectory(trajectory, name=name, color=str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)]))
    return builder.finalize()


def build_3d_trajectory_figure(
    trajectories: Sequence[tuple[str, PoseTrajectory3D]],
    *,
    title: str = "3D Trajectory Overlay",
    pose_axes_name: str | None = None,
    pose_axis_stride: int = 30,
) -> go.Figure:
    """Build a 3D trajectory overlay and optional sampled pose axes."""
    builder = TrajectoryPlotBuilder(mode="3d", title=title)
    for index, (name, trajectory) in enumerate(trajectories):
        color = str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)])
        builder.add_trajectory(trajectory, name=name, color=color)
        if pose_axes_name == name:
            builder.add_pose_axes(trajectory, stride=pose_axis_stride, axis_length_m=0.15)
    return builder.finalize()


def build_speed_profile_figure(
    trajectories: Sequence[tuple[str, PoseTrajectory3D]],
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
                line={"width": 2.2, "color": str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)])},
            )
        )
    apply_standard_xy_layout(figure, title=title, xaxis_title="Timestamp (s)", yaxis_title="Speed (m/s)")
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def build_height_profile_figure(
    trajectories: Sequence[tuple[str, PoseTrajectory3D]],
    *,
    title: str = "Height Profile",
) -> go.Figure:
    """Build a Z-over-time profile for one or more trajectories."""
    figure = go.Figure()
    for index, (name, trajectory) in enumerate(trajectories):
        timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
        figure.add_trace(
            go.Scattergl(
                x=timestamps_s,
                y=trajectory.positions_xyz[:, 2],
                mode="lines",
                name=name,
                line={"width": 2.2, "color": str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)])},
            )
        )
    apply_standard_xy_layout(figure, title=title, xaxis_title="Timestamp (s)", yaxis_title="Z (m)")
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
                line={"width": 2.0, "color": str(DEFAULT_COLORS[index % len(DEFAULT_COLORS)])},
            )
        )
    apply_standard_xy_layout(figure, title=title, xaxis_title="Sample Index", yaxis_title="Delta t (ms)")
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, rangemode="tozero")
    return figure


def trajectory_length_m(trajectory: PoseTrajectory3D) -> float:
    """Return the total path length in metres."""
    if len(trajectory.positions_xyz) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(trajectory.positions_xyz, axis=0), axis=1).sum())


def _add_xy_trajectory_trace(
    figure: go.Figure,
    positions_xyz: np.ndarray,
    *,
    name: str,
    line: dict[str, object],
    mode: str = "lines",
    marker: dict[str, object] | None = None,
    hovertemplate: str | None = None,
    showlegend: bool = True,
) -> None:
    if len(positions_xyz) == 0:
        return
    figure.add_trace(
        go.Scattergl(
            x=positions_xyz[:, 0],
            y=positions_xyz[:, 1],
            mode=mode,
            name=name,
            line=line,
            marker=marker,
            hovertemplate=hovertemplate,
            showlegend=showlegend,
        )
    )


def _add_3d_trajectory_trace(
    figure: go.Figure,
    positions_xyz: np.ndarray,
    *,
    name: str,
    line: dict[str, object] | None = None,
    mode: str = "lines",
    marker: dict[str, object] | None = None,
    text: Sequence[str] | None = None,
    hovertemplate: str | None = None,
    opacity: float | None = None,
    showlegend: bool = True,
) -> None:
    if len(positions_xyz) == 0:
        return
    figure.add_trace(
        go.Scatter3d(
            x=positions_xyz[:, 0],
            y=positions_xyz[:, 1],
            z=positions_xyz[:, 2],
            mode=mode,
            name=name,
            line=line,
            marker=marker,
            text=text,
            hovertemplate=hovertemplate,
            opacity=opacity,
            showlegend=showlegend,
        )
    )


def _add_xy_end_markers(figure: go.Figure, positions_xyz: np.ndarray, *, name: str, color: str) -> None:
    if len(positions_xyz) == 0:
        return
    _add_xy_trajectory_trace(
        figure,
        positions_xyz[[0]],
        name=f"{name} start",
        mode="markers",
        line={},
        marker={"size": 7, "color": color, "symbol": "circle"},
        showlegend=False,
    )
    _add_xy_trajectory_trace(
        figure,
        positions_xyz[[-1]],
        name=f"{name} end",
        mode="markers",
        line={},
        marker={"size": 8, "color": color, "symbol": "x"},
        showlegend=False,
    )


def _add_3d_end_markers(
    figure: go.Figure,
    positions_xyz: np.ndarray,
    *,
    start_name: str,
    end_name: str,
    start_marker: dict[str, object],
    end_marker: dict[str, object],
    start_hovertemplate: str | None = None,
    end_hovertemplate: str | None = None,
    showlegend: bool = False,
) -> None:
    if len(positions_xyz) == 0:
        return
    _add_3d_trajectory_trace(
        figure,
        positions_xyz[[0]],
        name=start_name,
        mode="markers",
        marker=start_marker,
        hovertemplate=start_hovertemplate,
        showlegend=showlegend,
    )
    _add_3d_trajectory_trace(
        figure,
        positions_xyz[[-1]],
        name=end_name,
        mode="markers",
        marker=end_marker,
        hovertemplate=end_hovertemplate,
        showlegend=showlegend,
    )


def _apply_standard_trajectory_xy_layout(figure: go.Figure, *, title: str) -> go.Figure:
    apply_standard_xy_layout(figure, title=title, xaxis_title="X (m)", yaxis_title="Y (m)")
    figure.update_xaxes(showgrid=True)
    figure.update_yaxes(showgrid=True, scaleanchor="x", scaleratio=1)
    return figure


def _apply_standard_trajectory_3d_layout(figure: go.Figure, *, title: str) -> go.Figure:
    apply_standard_3d_layout(
        figure,
        title=title,
        scene={
            "xaxis_title": "X (m)",
            "yaxis_title": "Y (m)",
            "zaxis_title": "Z (m)",
            "aspectmode": "data",
        },
    )
    return figure


class TrajectoryPlotBuilder:
    """Lightweight builder for BEV and 3D trajectory views."""

    def __init__(self, *, mode: Literal["bev", "3d"], title: str) -> None:
        self.mode = mode
        self.title = title
        self.figure = go.Figure()

    def add_trajectory(
        self,
        trajectory: PoseTrajectory3D,
        *,
        name: str,
        color: str,
    ) -> TrajectoryPlotBuilder:
        """Add one trajectory trace with start and end markers."""
        positions = trajectory.positions_xyz
        if len(positions) == 0:
            return self

        if self.mode == "bev":
            _add_xy_trajectory_trace(
                self.figure,
                positions,
                name=name,
                line={"width": 2.8, "color": color},
            )
            _add_xy_end_markers(self.figure, positions, name=name, color=color)
        else:
            _add_3d_trajectory_trace(
                self.figure,
                positions,
                name=name,
                line={"width": 5, "color": color},
            )
            _add_3d_end_markers(
                self.figure,
                positions,
                start_name=f"{name} start",
                end_name=f"{name} end",
                start_marker={"size": 4, "color": color, "symbol": "circle"},
                end_marker={"size": 5, "color": color, "symbol": "diamond"},
            )
        return self

    def add_pose_axes(
        self,
        trajectory: PoseTrajectory3D,
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

        axis_segments = {axis_name: [] for axis_name in AXIS_COLORS}
        basis = {
            "x": np.array([axis_length_m, 0.0, 0.0], dtype=np.float64),
            "y": np.array([0.0, axis_length_m, 0.0], dtype=np.float64),
            "z": np.array([0.0, 0.0, axis_length_m], dtype=np.float64),
        }

        for index in indices.tolist():
            pose = FrameTransform.from_matrix(np.asarray(trajectory.poses_se3[index], dtype=np.float64))
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
                    line={"width": 2, "color": AXIS_COLORS[axis_name]},
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        return self

    def finalize(self) -> go.Figure:
        """Finalize the figure layout and return it."""
        if self.mode == "bev":
            _apply_standard_trajectory_xy_layout(self.figure, title=self.title)
        else:
            _apply_standard_trajectory_3d_layout(self.figure, title=self.title)
        return self.figure


def _trajectory_speed_profile(trajectory: PoseTrajectory3D) -> tuple[np.ndarray, np.ndarray]:
    timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    if len(timestamps_s) < 2:
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)

    delta_t_s = np.diff(timestamps_s)
    finite_mask = delta_t_s > 0.0
    if not np.any(finite_mask):
        return np.empty(0, dtype=np.float64), np.empty(0, dtype=np.float64)
    delta_position_m = np.linalg.norm(np.diff(trajectory.positions_xyz, axis=0), axis=1)
    return timestamps_s[1:][finite_mask], delta_position_m[finite_mask] / delta_t_s[finite_mask]


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
