"""Tests for dataset-wide Plotly figure builders."""

from __future__ import annotations

import plotly.graph_objects as go
from evo.core import metrics

from prml_vslam.eval.dataset_aggregation import (
    CoverageCell,
    CoverageMatrix,
    PerSequenceRow,
    build_heatmap_data,
)
from prml_vslam.plotting.metrics import (
    build_coverage_chart,
    build_dataset_heatmap,
    build_grouped_bar_per_sequence,
    build_violin_by_method,
)


def _per_sequence_rows(
    *,
    sequences: list[str],
    sources: list[tuple[str, str]],
    base_value: float = 0.3,
) -> list[PerSequenceRow]:
    rows = []
    for i, seq_id in enumerate(sequences):
        for j, (base, status) in enumerate(sources):
            rows.append(
                PerSequenceRow(
                    sequence_id=seq_id,
                    estimate_source_base=base,
                    coordinate_status=status,
                    metric_family="ape",
                    pose_relation=metrics.PoseRelation.translation_part,
                    statistic="rmse",
                    value=base_value + i * 0.1 + j * 0.05,
                    unit="m",
                    matched_pairs=10,
                )
            )
    return rows


def _coverage_matrix(
    *,
    sequences: list[str],
    methods: list[str | None],
    present_pairs: set[tuple[str, str | None]] | None = None,
) -> CoverageMatrix:
    if present_pairs is None:
        present_pairs = {(seq, m) for seq in sequences for m in methods}
    cells = [
        CoverageCell(
            sequence_id=seq,
            method=m,
            manifest_present=(seq, m) in present_pairs,
            metric_row_count=5 if (seq, m) in present_pairs else 0,
        )
        for seq in sequences
        for m in methods
    ]
    return CoverageMatrix(sequence_ids=sequences, methods=methods, cells=cells)


# ---------------------------------------------------------------------------
# build_dataset_heatmap
# ---------------------------------------------------------------------------


def test_build_dataset_heatmap_returns_figure_with_heatmap_trace() -> None:
    rows = _per_sequence_rows(
        sequences=["advio-01", "advio-02"], sources=[("vista", "raw"), ("arcore", "source_native")]
    )
    heatmap_data = build_heatmap_data(rows, ["advio-01", "advio-02"], metric_name="APE RMSE (m)")

    figure = build_dataset_heatmap(heatmap_data)

    assert isinstance(figure, go.Figure)
    assert len(figure.data) == 1
    assert isinstance(figure.data[0], go.Heatmap)
    assert list(figure.data[0].y) == ["advio-01", "advio-02"]
    assert "arcore/source_native" in list(figure.data[0].x)


def test_build_dataset_heatmap_title_uses_metric_name() -> None:
    rows = _per_sequence_rows(sequences=["advio-01"], sources=[("vista", "raw")])
    heatmap_data = build_heatmap_data(rows, ["advio-01"], metric_name="Custom Metric")

    figure = build_dataset_heatmap(heatmap_data)

    assert figure.layout.title.text == "Custom Metric"


# ---------------------------------------------------------------------------
# build_grouped_bar_per_sequence
# ---------------------------------------------------------------------------


def test_build_grouped_bar_per_sequence_returns_one_bar_trace_per_source() -> None:
    rows = _per_sequence_rows(
        sequences=["advio-01", "advio-02"],
        sources=[("vista", "raw"), ("arcore", "source_native")],
    )

    figure = build_grouped_bar_per_sequence(rows)

    assert isinstance(figure, go.Figure)
    trace_names = [trace.name for trace in figure.data]
    assert "vista/raw" in trace_names
    assert "arcore/source_native" in trace_names
    assert figure.layout.barmode == "group"


def test_build_grouped_bar_per_sequence_x_axis_contains_all_sequences() -> None:
    rows = _per_sequence_rows(sequences=["seq-a", "seq-b", "seq-c"], sources=[("vista", "raw")])

    figure = build_grouped_bar_per_sequence(rows)

    bar_x = list(figure.data[0].x)
    assert "seq-a" in bar_x
    assert "seq-b" in bar_x
    assert "seq-c" in bar_x


# ---------------------------------------------------------------------------
# build_coverage_chart
# ---------------------------------------------------------------------------


def test_build_coverage_chart_returns_heatmap_figure() -> None:
    matrix = _coverage_matrix(
        sequences=["advio-01", "advio-02"],
        methods=["vista", "arcore"],
    )

    figure = build_coverage_chart(matrix)

    assert isinstance(figure, go.Figure)
    assert isinstance(figure.data[0], go.Heatmap)
    assert list(figure.data[0].y) == ["advio-01", "advio-02"]
    assert "vista" in list(figure.data[0].x)


def test_build_coverage_chart_missing_entries_show_as_zero() -> None:
    matrix = _coverage_matrix(
        sequences=["advio-01", "advio-02"],
        methods=["vista"],
        present_pairs={("advio-01", "vista")},  # advio-02 missing
    )

    figure = build_coverage_chart(matrix)
    z = figure.data[0].z

    assert z[0][0] == 1  # advio-01 / vista present
    assert z[1][0] == 0  # advio-02 / vista missing


# ---------------------------------------------------------------------------
# build_violin_by_method
# ---------------------------------------------------------------------------


def test_build_violin_by_method_returns_one_violin_per_source() -> None:
    rows = _per_sequence_rows(
        sequences=["advio-01", "advio-02", "advio-03"],
        sources=[("vista", "raw"), ("arcore", "source_native")],
    )

    figure = build_violin_by_method(rows)

    assert isinstance(figure, go.Figure)
    trace_names = [trace.name for trace in figure.data]
    assert "vista/raw" in trace_names
    assert "arcore/source_native" in trace_names
    assert all(isinstance(t, go.Violin) for t in figure.data)
