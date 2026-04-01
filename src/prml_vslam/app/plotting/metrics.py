"""Plotly builders for trajectory-evaluation views."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from prml_vslam.eval import TrajectoryEvaluationResult

from ..models import TrajectoryPoint


def build_metric_summary_figure(result: TrajectoryEvaluationResult) -> go.Figure:
    """Build a compact bar chart for scalar `evo` metrics."""
    preferred_order = ["rmse", "mean", "median", "std", "min", "max"]
    ordered_names = [name for name in preferred_order if name in result.stats]
    ordered_names.extend(name for name in result.stats if name not in ordered_names)
    values = [result.stats[name] for name in ordered_names]

    figure = go.Figure(
        go.Bar(
            x=ordered_names,
            y=values,
            marker=dict(color="#2563eb", line=dict(color="#1e293b", width=0.8)),
            hovertemplate="<b>%{x}</b><br>%{y:.6f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(247,248,250,1)",
        xaxis=dict(title="", tickangle=-15),
        yaxis=dict(title="Value"),
        font=dict(family="Source Sans Pro, Arial, sans-serif", color="#16202a"),
    )
    return figure


def build_trajectory_overlay_figure(
    *,
    reference_points: list[TrajectoryPoint],
    estimate_points: list[TrajectoryPoint],
    title: str,
) -> go.Figure:
    """Build a two-view trajectory overlay figure for interpretation."""
    figure = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("XY plane", "XZ plane"),
        horizontal_spacing=0.12,
    )

    _add_trajectory_trace(
        figure=figure,
        row=1,
        col=1,
        points=reference_points,
        x_key="x",
        y_key="y",
        name="Reference",
        color="#0f766e",
    )
    _add_trajectory_trace(
        figure=figure,
        row=1,
        col=1,
        points=estimate_points,
        x_key="x",
        y_key="y",
        name="Estimate",
        color="#2563eb",
    )
    _add_trajectory_trace(
        figure=figure,
        row=1,
        col=2,
        points=reference_points,
        x_key="x",
        y_key="z",
        name="Reference",
        color="#0f766e",
        showlegend=False,
    )
    _add_trajectory_trace(
        figure=figure,
        row=1,
        col=2,
        points=estimate_points,
        x_key="x",
        y_key="z",
        name="Estimate",
        color="#2563eb",
        showlegend=False,
    )

    figure.update_xaxes(title_text="X (m)", row=1, col=1)
    figure.update_yaxes(title_text="Y (m)", row=1, col=1, scaleanchor="x")
    figure.update_xaxes(title_text="X (m)", row=1, col=2)
    figure.update_yaxes(title_text="Z (m)", row=1, col=2, scaleanchor="x")
    figure.update_layout(
        title=title,
        height=420,
        margin=dict(l=0, r=0, t=56, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(247,248,250,1)",
        font=dict(family="Source Sans Pro, Arial, sans-serif", color="#16202a"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
    )
    return figure


def _add_trajectory_trace(
    *,
    figure: go.Figure,
    row: int,
    col: int,
    points: list[TrajectoryPoint],
    x_key: str,
    y_key: str,
    name: str,
    color: str,
    showlegend: bool = True,
) -> None:
    xs = [getattr(point, x_key) for point in points]
    ys = [getattr(point, y_key) for point in points]
    timestamps = [point.timestamp_s for point in points]
    figure.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="lines+markers",
            marker=dict(size=5, color=color),
            line=dict(color=color, width=2),
            name=name,
            showlegend=showlegend,
            customdata=timestamps,
            hovertemplate="<b>%{fullData.name}</b><br>t=%{customdata:.3f} s<br>x=%{x:.3f}<br>y=%{y:.3f}<extra></extra>",
        ),
        row=row,
        col=col,
    )


__all__ = ["build_metric_summary_figure", "build_trajectory_overlay_figure"]
