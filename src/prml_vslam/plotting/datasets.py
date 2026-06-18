"""Plotly figure builders for normalized dataset analysis tables."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .theme import BLUE, GREEN, ORANGE, apply_standard_xy_layout


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


__all__ = ["build_payload_footprint_figure"]
