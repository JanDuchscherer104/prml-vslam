"""Plotly and SVG builders for final-slide dataset summaries."""

from __future__ import annotations

from collections.abc import Sequence
from xml.sax.saxutils import escape

import numpy as np
import plotly.graph_objects as go
from evo.core.trajectory import PoseTrajectory3D
from plotly.subplots import make_subplots

from prml_vslam.sources.datasets.summary import DatasetObservationSummary

_DATASET_COLORS = {
    "advio": "#2F6FED",
    "tum_rgbd": "#2C9A68",
    "record3d": "#F28E2B",
}
_AXIS_COLOR = "#D8DEE9"
_TEXT_COLOR = "#172033"
_MUTED_TEXT = "#5C667A"
_SUMMARY_CHART_VARIANTS = {
    "clean": {
        "title": "Normalized Dataset Summary",
        "subtitle": "One preferred normalized profile per sequence; durations are observation durations.",
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "gridcolor": "#DDE4EF",
        "font_color": _TEXT_COLOR,
        "title_color": _TEXT_COLOR,
        "axis_color": "#364152",
        "bar_opacity": 0.96,
        "bar_line": "#FFFFFF",
    },
    "presentation": {
        "title": "Normalized Dataset Summary",
        "subtitle": "ADVIO, TUM RGB-D, and Record3D coverage in the normalized datastore.",
        "paper_bgcolor": "#F8FAFC",
        "plot_bgcolor": "#F8FAFC",
        "gridcolor": "#CBD5E1",
        "font_color": "#111827",
        "title_color": "#111827",
        "axis_color": "#1F2937",
        "bar_opacity": 1.0,
        "bar_line": "#F8FAFC",
    },
    "minimal": {
        "title": "Dataset Coverage",
        "subtitle": "Sequence count, total observation duration, and mean observation duration.",
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FFFFFF",
        "gridcolor": "#EEF2F7",
        "font_color": "#111827",
        "title_color": "#111827",
        "axis_color": "#374151",
        "bar_opacity": 0.92,
        "bar_line": "#FFFFFF",
    },
    "contrast": {
        "title": "Normalized Dataset Coverage",
        "subtitle": "Static comparison from normalized datastore observation summaries.",
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#F3F6FA",
        "gridcolor": "#BFCCDA",
        "font_color": "#0F172A",
        "title_color": "#0F172A",
        "axis_color": "#0F172A",
        "bar_opacity": 1.0,
        "bar_line": "#FFFFFF",
    },
    "wide": {
        "title": "Normalized Dataset Summary",
        "subtitle": "Counts and durations use one preferred normalized profile per sequence.",
        "paper_bgcolor": "#FFFFFF",
        "plot_bgcolor": "#FAFBFD",
        "gridcolor": "#E2E8F0",
        "font_color": "#182033",
        "title_color": "#182033",
        "axis_color": "#2D3748",
        "bar_opacity": 0.98,
        "bar_line": "#FFFFFF",
    },
}


def dataset_summary_chart_variants() -> tuple[str, ...]:
    """Return the available visual variants for the summary bar chart."""
    return tuple(_SUMMARY_CHART_VARIANTS)


def build_dataset_summary_bar_svg(
    summaries: Sequence[DatasetObservationSummary],
    *,
    width: int = 1320,
    height: int = 610,
    variant: str = "clean",
) -> str:
    """Build a static SVG bar chart for sequence counts and durations."""
    if variant not in _SUMMARY_CHART_VARIANTS:
        variants = ", ".join(dataset_summary_chart_variants())
        raise ValueError(f"Unknown dataset summary chart variant '{variant}'. Expected one of: {variants}.")
    style = _SUMMARY_CHART_VARIANTS[variant]
    metrics = (
        (
            "Sequences",
            "count",
            [float(row.sequence_count) for row in summaries],
            [f"{row.sequence_count}" for row in summaries],
        ),
        (
            "Total duration",
            "min",
            [row.total_duration_s / 60.0 for row in summaries],
            [f"{row.total_duration_s / 60.0:.1f}" for row in summaries],
        ),
        (
            "Avg. duration",
            "s",
            [row.average_duration_s for row in summaries],
            [f"{row.average_duration_s:.1f}" for row in summaries],
        ),
    )
    labels = [row.dataset_label for row in summaries]
    colors = [_DATASET_COLORS.get(row.dataset_id.value, "#6B7280") for row in summaries]
    plot_top = 118.0
    plot_bottom = height - 126.0
    panel_gap = 40.0
    panel_width = (width - 112.0 - panel_gap * 2.0) / 3.0
    parts = [
        _svg_open(width, height),
        f'<rect width="{width}" height="{height}" fill="{style["paper_bgcolor"]}"/>',
        _text(56, 48, str(style["title"]), size=28, fill=str(style["title_color"]), weight="700"),
        _text(56, 78, str(style["subtitle"]), size=16, fill=_MUTED_TEXT, weight="500"),
    ]
    for metric_index, (title, unit, values, value_labels) in enumerate(metrics):
        panel_left = 56.0 + metric_index * (panel_width + panel_gap)
        parts.extend(
            _dataset_summary_svg_panel(
                labels=labels,
                colors=colors,
                title=title,
                unit=unit,
                values=values,
                value_labels=value_labels,
                x=panel_left,
                y=plot_top,
                width=panel_width,
                height=plot_bottom - plot_top,
                style=style,
            )
        )
    parts.append("</svg>")
    return "\n".join(parts)


def build_dataset_summary_bar_figure(
    summaries: Sequence[DatasetObservationSummary],
    *,
    width: int = 1320,
    height: int = 610,
    variant: str = "clean",
) -> go.Figure:
    """Build a faceted Plotly bar chart for sequence counts and durations."""
    if variant not in _SUMMARY_CHART_VARIANTS:
        variants = ", ".join(dataset_summary_chart_variants())
        raise ValueError(f"Unknown dataset summary chart variant '{variant}'. Expected one of: {variants}.")
    style = _SUMMARY_CHART_VARIANTS[variant]
    metrics = (
        (
            "Sequences",
            "count",
            [float(row.sequence_count) for row in summaries],
            [f"{row.sequence_count}" for row in summaries],
        ),
        (
            "Total duration",
            "min",
            [row.total_duration_s / 60.0 for row in summaries],
            [f"{row.total_duration_s / 60.0:.1f}" for row in summaries],
        ),
        (
            "Avg. duration",
            "s",
            [row.average_duration_s for row in summaries],
            [f"{row.average_duration_s:.1f}" for row in summaries],
        ),
    )
    dataset_labels = [row.dataset_label for row in summaries]
    marker_colors = [_DATASET_COLORS.get(row.dataset_id.value, "#6B7280") for row in summaries]
    figure = make_subplots(
        rows=1,
        cols=len(metrics),
        subplot_titles=[title for title, *_ in metrics],
        horizontal_spacing=0.075,
    )
    for index, (_title, _unit, values, labels) in enumerate(metrics, start=1):
        figure.add_trace(
            go.Bar(
                x=dataset_labels,
                y=values,
                text=labels,
                textposition="inside",
                insidetextanchor="middle",
                textangle=0,
                textfont={"size": 32, "color": "#FFFFFF", "family": "Arial, sans-serif"},
                marker={
                    "color": marker_colors,
                    "opacity": style["bar_opacity"],
                    "line": {"color": style["bar_line"], "width": 2},
                },
                cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>",
                showlegend=False,
            ),
            row=1,
            col=index,
        )
        max_value = max(values, default=0.0)
        figure.update_yaxes(
            range=[0, max_value * 1.18 if max_value > 0 else 1.0],
            showgrid=True,
            gridcolor=style["gridcolor"],
            zeroline=False,
            title_text=_unit,
            title_font={"size": 22, "color": style["axis_color"]},
            tickfont={"size": 18, "color": style["axis_color"]},
            row=1,
            col=index,
        )
        figure.update_xaxes(
            tickfont={"size": 28, "color": style["axis_color"]},
            tickangle=45,
            showline=False,
            row=1,
            col=index,
        )
    figure.update_annotations(font={"size": 30, "color": style["title_color"], "family": "Arial, sans-serif"}, y=1.02)
    figure.update_layout(
        width=width,
        height=height,
        paper_bgcolor=style["paper_bgcolor"],
        plot_bgcolor=style["plot_bgcolor"],
        font={"family": "Arial, sans-serif", "color": style["font_color"]},
        margin={"l": 76, "r": 34, "t": 76, "b": 132},
        bargap=0.24,
        uniformtext={"minsize": 24, "mode": "show"},
        title=None,
    )
    return figure


def build_reference_data_svg(
    *,
    title: str,
    trajectories: Sequence[tuple[str, PoseTrajectory3D]],
    clouds: Sequence[tuple[str, np.ndarray, np.ndarray | None]] = (),
    plane_axes: tuple[int, int] = (0, 1),
    width: int = 820,
    height: int = 540,
    max_cloud_points: int = 3500,
    random_seed: int = 17,
) -> str:
    """Build a compact 2D SVG view of reference clouds and trajectories."""
    projected_clouds = [
        (
            label,
            _sample_points(np.asarray(points_xyz, dtype=np.float64), max_points=max_cloud_points, seed=random_seed + i),
            None
            if colors_rgb is None
            else _sample_points(
                np.asarray(colors_rgb, dtype=np.float64), max_points=max_cloud_points, seed=random_seed + i
            ),
        )
        for i, (label, points_xyz, colors_rgb) in enumerate(clouds)
    ]
    projected_trajectories = [
        (label, np.asarray(trajectory.positions_xyz, dtype=np.float64)) for label, trajectory in trajectories
    ]
    xy_arrays = [points[:, plane_axes] for _label, points, _colors in projected_clouds if len(points) > 0] + [
        positions[:, plane_axes] for _label, positions in projected_trajectories if len(positions) > 0
    ]
    transform = _view_transform(xy_arrays, width=width, height=height)
    parts = [
        _svg_open(width, height),
        f'<rect width="{width}" height="{height}" rx="18" fill="#FFFFFF"/>',
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="17" fill="none" stroke="#D8DEE9"/>',
        _text(28, 34, title, size=24, weight="700"),
    ]
    for _label, points, colors in projected_clouds:
        if len(points) == 0:
            continue
        xy = transform(points[:, plane_axes])
        for index, (x, y) in enumerate(xy):
            color = "#A9B7C8" if colors is None else _rgb_hex(colors[index])
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.25" fill="{color}" fill-opacity="0.42"/>')
    for index, (label, positions) in enumerate(projected_trajectories):
        if len(positions) == 0:
            continue
        xy = transform(positions[:, plane_axes])
        color = _trajectory_color(index)
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in xy)
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="4.2" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        parts.append(
            f'<circle cx="{xy[0, 0]:.2f}" cy="{xy[0, 1]:.2f}" r="5" fill="#FFFFFF" stroke="{color}" stroke-width="3"/>'
        )
        parts.append(f'<circle cx="{xy[-1, 0]:.2f}" cy="{xy[-1, 1]:.2f}" r="5" fill="{color}"/>')
        parts.append(_legend_item(28, height - 30 - 24 * index, color, label))
    axis_a, axis_b = (("X", "Y", "Z")[axis] for axis in plane_axes)
    parts.append(_text(width - 28, height - 24, f"{axis_a}/{axis_b} view", size=14, fill=_MUTED_TEXT, anchor="end"))
    parts.append("</svg>")
    return "\n".join(parts)


def _dataset_summary_svg_panel(
    *,
    labels: Sequence[str],
    colors: Sequence[str],
    title: str,
    unit: str,
    values: Sequence[float],
    value_labels: Sequence[str],
    x: float,
    y: float,
    width: float,
    height: float,
    style: dict[str, str | float],
) -> list[str]:
    max_value = max(values, default=0.0)
    scale = height / (max_value * 1.18 if max_value > 0.0 else 1.0)
    bar_count = max(len(values), 1)
    slot_width = width / bar_count
    bar_width = min(76.0, slot_width * 0.62)
    baseline = y + height
    parts = [
        f'<rect x="{x:.2f}" y="{y - 26:.2f}" width="{width:.2f}" height="{height + 78:.2f}" '
        f'fill="{style["plot_bgcolor"]}"/>',
        _text(x + width / 2.0, y - 48.0, title, size=24, fill=str(style["title_color"]), weight="700", anchor="middle"),
        _text(x + width - 4.0, y - 14.0, unit, size=15, fill=str(style["axis_color"]), anchor="end"),
        f'<line x1="{x:.2f}" y1="{baseline:.2f}" x2="{x + width:.2f}" y2="{baseline:.2f}" '
        f'stroke="{style["gridcolor"]}" stroke-width="2"/>',
    ]
    for index, (label, color, value, value_label) in enumerate(zip(labels, colors, values, value_labels, strict=True)):
        center_x = x + slot_width * (index + 0.5)
        bar_height = max(value * scale, 2.0)
        bar_x = center_x - bar_width / 2.0
        bar_y = baseline - bar_height
        parts.extend(
            (
                f'<rect x="{bar_x:.2f}" y="{bar_y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" '
                f'rx="4" fill="{color}" fill-opacity="{style["bar_opacity"]}" '
                f'stroke="{style["bar_line"]}" stroke-width="2"/>',
                _text(
                    center_x,
                    bar_y + min(34.0, bar_height * 0.55),
                    value_label,
                    size=21,
                    fill="#FFFFFF",
                    anchor="middle",
                ),
                _text(center_x, baseline + 34.0, label, size=18, fill=str(style["axis_color"]), anchor="middle"),
            )
        )
    return parts


def _view_transform(xy_arrays: Sequence[np.ndarray], *, width: int, height: int):
    if not xy_arrays:
        xy_arrays = [np.asarray([[0.0, 0.0], [1.0, 1.0]], dtype=np.float64)]
    points = np.concatenate(xy_arrays, axis=0)
    mins = np.nanmin(points, axis=0)
    maxs = np.nanmax(points, axis=0)
    span = np.maximum(maxs - mins, 1e-9)
    left, top, right, bottom = 42.0, 62.0, width - 42.0, height - 58.0
    scale = min((right - left) / span[0], (bottom - top) / span[1]) * 0.92
    center = (mins + maxs) / 2.0
    target = np.asarray([(left + right) / 2.0, (top + bottom) / 2.0], dtype=np.float64)

    def transform(xy: np.ndarray) -> np.ndarray:
        projected = (xy - center) * scale
        projected[:, 1] *= -1.0
        return projected + target

    return transform


def _sample_points(points: np.ndarray, *, max_points: int, seed: int) -> np.ndarray:
    if max_points <= 0 or len(points) <= max_points:
        return points
    rng = np.random.default_rng(seed)
    return points[rng.choice(len(points), size=max_points, replace=False)]


def _trajectory_color(index: int) -> str:
    return ("#D64F3A", "#2F6FED", "#2C9A68")[index % 3]


def _rgb_hex(color: np.ndarray) -> str:
    clipped = np.clip(color, 0.0, 1.0)
    red, green, blue = (clipped * 255.0).astype(np.uint8).tolist()
    return f"#{red:02X}{green:02X}{blue:02X}"


def _legend_item(x: float, y: float, color: str, label: str) -> str:
    return "\n".join(
        (
            f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{x + 26:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="4" stroke-linecap="round"/>',
            _text(x + 34, y + 5, label, size=14, fill=_MUTED_TEXT),
        )
    )


def _svg_open(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
    )


def _text(
    x: float,
    y: float,
    value: str,
    *,
    size: int,
    fill: str = _TEXT_COLOR,
    weight: str = "500",
    anchor: str = "start",
) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="Inter, Arial, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">'
        f"{escape(value)}</text>"
    )


__all__ = [
    "build_dataset_summary_bar_figure",
    "build_dataset_summary_bar_svg",
    "build_reference_data_svg",
    "dataset_summary_chart_variants",
]
