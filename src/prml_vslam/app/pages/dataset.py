"""ADVIO dataset explorer page."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from ..models import DatasetId, DatasetPageState
from ..plotting import build_advio_asset_figure, build_advio_timeline_figure
from ..ui import render_header, render_key_value_rows, render_path_cards

if TYPE_CHECKING:
    from ..bootstrap import AppContext


def render(context: AppContext) -> None:
    """Render the ADVIO dataset explorer page."""
    render_header(
        title="ADVIO Dataset Explorer",
        kicker="Dataset inspection",
        copy=(
            "Inspect modality coverage, temporal span, and asset footprint before benchmarking or "
            "interpreting evo trajectory metrics."
        ),
    )

    service = context.services.evaluation
    paths = context.services.path_config
    state = context.state

    with st.expander("Configured paths", expanded=False):
        render_path_cards([("ADVIO root", paths.advio_root)])

    sequence_ids = service.list_sequences(DatasetId.ADVIO)
    selected_sequence_id = _resolve_sequence_id(state.dataset.sequence_id, sequence_ids)

    with st.container(border=True):
        dataset_col, sequence_col = st.columns([0.8, 1.2], gap="large")
        dataset_col.selectbox(
            "Dataset",
            options=[DatasetId.ADVIO],
            format_func=lambda item: item.label,
            disabled=True,
        )
        if sequence_ids:
            selected_sequence_id = sequence_col.selectbox(
                "Sequence",
                options=sequence_ids,
                index=sequence_ids.index(selected_sequence_id) if selected_sequence_id is not None else 0,
                format_func=lambda item: f"ADVIO {item:02d}",
            )
        else:
            sequence_col.selectbox("Sequence", options=["No local ADVIO sequences"], disabled=True)
            selected_sequence_id = None

    state.dataset = DatasetPageState(dataset=DatasetId.ADVIO, sequence_id=selected_sequence_id)
    context.store.save(state)

    if not sequence_ids or selected_sequence_id is None:
        st.warning(f"No local ADVIO sequences were found under {paths.advio_root}.")
        return

    try:
        summary = service.summarize_sequence(DatasetId.ADVIO, selected_sequence_id)
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    metric_sequence, metric_timed, metric_assets, metric_duration, metric_size = st.columns(5)
    metric_sequence.metric("Sequence", summary.config.sequence_name)
    metric_timed.metric("Timed streams", summary.timed_modality_count)
    metric_assets.metric("Untimed assets", summary.asset_modality_count)
    metric_duration.metric("Observed span", _format_duration(summary.duration_s))
    metric_size.metric("Tracked footprint", _format_bytes(summary.total_size_bytes))

    timeline_col, asset_col = st.columns([1.35, 0.85], gap="large")
    with timeline_col:
        st.markdown("### Temporal coverage")
        st.plotly_chart(build_advio_timeline_figure(summary), width="stretch", config={"displayModeBar": False})
    with asset_col:
        st.markdown("### Asset footprint")
        st.plotly_chart(build_advio_asset_figure(summary), width="stretch", config={"displayModeBar": False})

    st.markdown("### Modality inventory")
    render_key_value_rows(
        [
            {
                "label": modality.label,
                "family": modality.family,
                "kind": modality.source_kind,
                "samples": modality.sample_count or None,
                "duration_s": round(modality.duration_s, 3) if modality.duration_s is not None else None,
                "rate_hz": round(modality.approx_rate_hz, 2) if modality.approx_rate_hz is not None else None,
                "size": _format_bytes(modality.size_bytes),
                "detail": modality.detail,
                "path": modality.path.as_posix(),
            }
            for modality in (*summary.timed_modalities, *summary.asset_modalities)
        ]
    )


def _resolve_sequence_id(current_value: int | None, sequence_ids: list[int]) -> int | None:
    if current_value in sequence_ids:
        return current_value
    return sequence_ids[0] if sequence_ids else None


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


__all__ = ["render"]
