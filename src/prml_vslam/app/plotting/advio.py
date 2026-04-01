"""Plotly builders for ADVIO dataset inspection views."""

from __future__ import annotations

import plotly.graph_objects as go

from prml_vslam.datasets import AdvioSequenceSummary


def build_advio_timeline_figure(summary: AdvioSequenceSummary) -> go.Figure:
    """Build a Plotly timeline for timestamped ADVIO modalities."""
    modalities = list(reversed(summary.timed_modalities))
    if not modalities:
        figure = go.Figure()
        figure.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=12, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="No timestamped modalities found.", x=0.5, y=0.5, showarrow=False)],
        )
        return figure

    figure = go.Figure()
    for modality in modalities:
        start_s = modality.start_s or 0.0
        duration_s = modality.duration_s if modality.duration_s is not None and modality.duration_s > 0 else 0.015
        figure.add_trace(
            go.Bar(
                x=[duration_s],
                y=[modality.label],
                base=[start_s],
                orientation="h",
                marker=dict(
                    color=_dataset_family_color(modality.family),
                    line=dict(color="rgba(15,23,42,0.22)", width=1.0),
                ),
                customdata=[
                    [
                        modality.family,
                        modality.sample_count,
                        _format_duration(modality.duration_s),
                        f"{modality.approx_rate_hz:.2f} Hz" if modality.approx_rate_hz is not None else "n/a",
                        modality.path.as_posix(),
                        modality.detail or "",
                        modality.start_s if modality.start_s is not None else float("nan"),
                        modality.end_s if modality.end_s is not None else float("nan"),
                    ]
                ],
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Family: %{customdata[0]}<br>"
                    "Samples: %{customdata[1]}<br>"
                    "Start: %{customdata[6]:.3f} s<br>"
                    "End: %{customdata[7]:.3f} s<br>"
                    "Span: %{customdata[2]}<br>"
                    "Approx. rate: %{customdata[3]}<br>"
                    "Note: %{customdata[5]}<br>"
                    "Path: %{customdata[4]}<extra></extra>"
                ),
                showlegend=False,
            )
        )

    figure.update_layout(
        height=max(420, 44 * len(modalities)),
        margin=dict(l=0, r=12, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(247,248,250,1)",
        bargap=0.28,
        xaxis=dict(title="Observed time span (s)", gridcolor="rgba(15,23,42,0.08)", zeroline=False),
        yaxis=dict(title="", automargin=True),
        font=dict(family="Source Sans Pro, Arial, sans-serif", color="#16202a"),
    )
    return figure


def build_advio_asset_figure(summary: AdvioSequenceSummary) -> go.Figure:
    """Build a Plotly treemap for untimed ADVIO assets."""
    if not summary.asset_modalities:
        figure = go.Figure()
        figure.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=12, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[dict(text="No untimed assets found.", x=0.5, y=0.5, showarrow=False)],
        )
        return figure

    labels = ["ADVIO assets"]
    parents = [""]
    values = [max(summary.total_size_bytes, 1)]
    colors = ["#dbe4ea"]
    hovertexts = [f"Tracked footprint: {_format_bytes(summary.total_size_bytes)}"]

    family_totals: dict[str, int] = {}
    for modality in summary.asset_modalities:
        family_totals.setdefault(modality.family, 0)
        family_totals[modality.family] += max(modality.size_bytes, 1)

    for family, size_bytes in family_totals.items():
        labels.append(family.replace("_", " ").title())
        parents.append("ADVIO assets")
        values.append(max(size_bytes, 1))
        colors.append(_dataset_family_color(family))
        hovertexts.append(f"{family} · {_format_bytes(size_bytes)}")

    for modality in summary.asset_modalities:
        labels.append(modality.label)
        parents.append(modality.family.replace("_", " ").title())
        values.append(max(modality.size_bytes, 1))
        colors.append(_dataset_family_color(modality.family))
        count_detail = f"{modality.sample_count} snapshots" if modality.sample_count > 0 else "untimed asset"
        hovertexts.append(
            f"{modality.detail or ''}<br>{count_detail}<br>{_format_bytes(modality.size_bytes)}<br>{modality.path.as_posix()}"
        )

    figure = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            marker=dict(colors=colors),
            textinfo="label+value",
            texttemplate="%{label}<br>%{value}",
            hovertext=hovertexts,
            hovertemplate="%{hovertext}<extra></extra>",
        )
    )
    figure.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=12, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Source Sans Pro, Arial, sans-serif", color="#16202a"),
    )
    return figure


def _dataset_family_color(family: str) -> str:
    palette = {
        "video": "#2563eb",
        "imu": "#0f766e",
        "environment": "#0891b2",
        "baseline": "#7c3aed",
        "reference": "#d97706",
        "geometry": "#dc2626",
        "calibration": "#475569",
    }
    return palette.get(family, "#475569")


def _format_duration(duration_s: float | None) -> str:
    if duration_s is None:
        return "n/a"
    if duration_s < 1.0:
        return f"{duration_s * 1000:.0f} ms"
    if duration_s < 60.0:
        return f"{duration_s:.2f} s"
    minutes, seconds = divmod(duration_s, 60.0)
    return f"{int(minutes)}m {seconds:04.1f}s"


def _format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    units = ["KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    unit = "B"
    for unit in units:
        value /= 1024.0
        if value < 1024.0:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} {unit}"


__all__ = ["build_advio_asset_figure", "build_advio_timeline_figure"]
