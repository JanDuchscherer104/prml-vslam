"""Tests for pure dataset-wide aggregation functions."""

from __future__ import annotations

from pathlib import Path

import pytest
from evo.core import metrics

from prml_vslam.eval.dataset_aggregation import (
    MetricFilter,
    build_coverage_matrix,
    build_heatmap_data,
    build_leaderboard,
    build_per_sequence_table,
)
from prml_vslam.eval.query import DatasetEvaluationSelection, DatasetRunCoverage
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow
from prml_vslam.sources.datasets.contracts import DatasetId


def _make_metric_row(
    *,
    run_id: str,
    sequence_id: str,
    estimate_source: str,
    metric_family: str = "ape",
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part,
    statistic: str = "rmse",
    value: float = 0.5,
    matched_pairs: int = 10,
    unit: str = "m",
) -> TrajectoryMetricResultRow:
    return TrajectoryMetricResultRow(
        run_id=run_id,
        sequence_id=sequence_id,
        reference_source="ground_truth",
        estimate_source=estimate_source,
        metric_family=metric_family,
        pose_relation=pose_relation,
        statistic=statistic,
        value=value,
        unit=unit,
        matched_pairs=matched_pairs,
    )


def _make_coverage(
    *,
    sequence_id: str,
    run_id: str,
    method: str | None = "vista",
    metric_row_count: int = 5,
    manifest_present: bool = True,
) -> DatasetRunCoverage:
    return DatasetRunCoverage(
        sequence_id=sequence_id,
        run_id=run_id,
        artifact_root=Path(f"/artifacts/{sequence_id}/{method}"),
        method=method,
        manifest_present=manifest_present,
        metric_row_count=metric_row_count,
    )


def _make_selection(
    *,
    all_sequence_ids: list[str],
    coverage: list[DatasetRunCoverage],
    metric_rows: list[TrajectoryMetricResultRow],
) -> DatasetEvaluationSelection:
    return DatasetEvaluationSelection(
        dataset=DatasetId.ADVIO,
        all_sequence_ids=all_sequence_ids,
        coverage=coverage,
        metric_rows=metric_rows,
    )


# ---------------------------------------------------------------------------
# build_per_sequence_table
# ---------------------------------------------------------------------------


def test_build_per_sequence_table_filters_by_family_and_pose_relation() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02"],
        coverage=[_make_coverage(sequence_id="advio-01", run_id="run-01")],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw", value=0.3),
            _make_metric_row(
                run_id="run-01",
                sequence_id="advio-01",
                estimate_source="vista/raw",
                metric_family="ape",
                pose_relation=metrics.PoseRelation.rotation_angle_deg,
                value=5.0,
                unit="deg",
            ),
            _make_metric_row(
                run_id="run-01",
                sequence_id="advio-01",
                estimate_source="vista/raw",
                metric_family="rpe",
                pose_relation=metrics.PoseRelation.translation_part,
                value=0.1,
                unit="m",
            ),
        ],
    )

    rows = build_per_sequence_table(
        selection, MetricFilter(metric_family="ape", pose_relation=metrics.PoseRelation.translation_part)
    )

    assert len(rows) == 1
    assert rows[0].sequence_id == "advio-01"
    assert rows[0].value == pytest.approx(0.3)
    assert rows[0].estimate_source_base == "vista"
    assert rows[0].coordinate_status == "raw"
    assert rows[0].metric_family == "ape"


def test_build_per_sequence_table_splits_estimate_source() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01"],
        coverage=[_make_coverage(sequence_id="advio-01", run_id="run-01")],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="arcore/source_native"),
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="arcore/aligned"),
        ],
    )

    rows = build_per_sequence_table(selection, MetricFilter())

    bases = {r.estimate_source_base for r in rows}
    statuses = {r.coordinate_status for r in rows}
    assert bases == {"arcore"}
    assert statuses == {"source_native", "aligned"}


def test_build_per_sequence_table_returns_empty_when_no_match() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01"],
        coverage=[],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw", metric_family="ape"),
        ],
    )

    rows = build_per_sequence_table(selection, MetricFilter(metric_family="rpe"))

    assert rows == []


def test_build_per_sequence_table_attaches_method_from_coverage() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01"],
        coverage=[_make_coverage(sequence_id="advio-01", run_id="run-01", method="vista")],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw"),
        ],
    )

    rows = build_per_sequence_table(selection, MetricFilter())

    assert rows[0].method == "vista"


# ---------------------------------------------------------------------------
# build_leaderboard
# ---------------------------------------------------------------------------


def test_build_leaderboard_ranks_by_mean_ascending() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02"],
        coverage=[
            _make_coverage(sequence_id="advio-01", run_id="run-01", method="vista"),
            _make_coverage(sequence_id="advio-02", run_id="run-02", method="arcore"),
        ],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw", value=0.2),
            _make_metric_row(
                run_id="run-02", sequence_id="advio-02", estimate_source="arcore/source_native", value=0.8
            ),
        ],
    )
    rows = build_per_sequence_table(selection, MetricFilter())
    leaderboard = build_leaderboard(rows, n_total_sequences=2)

    assert len(leaderboard) == 2
    assert leaderboard[0].estimate_source_base == "vista"
    assert leaderboard[0].mean == pytest.approx(0.2)
    assert leaderboard[1].estimate_source_base == "arcore"
    assert leaderboard[1].mean == pytest.approx(0.8)


def test_build_leaderboard_aggregates_multiple_sequences_per_source() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02"],
        coverage=[
            _make_coverage(sequence_id="advio-01", run_id="run-01", method="vista"),
            _make_coverage(sequence_id="advio-02", run_id="run-02", method="vista"),
        ],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw", value=0.2),
            _make_metric_row(run_id="run-02", sequence_id="advio-02", estimate_source="vista/raw", value=0.4),
        ],
    )
    rows = build_per_sequence_table(selection, MetricFilter())
    leaderboard = build_leaderboard(rows, n_total_sequences=3)

    assert len(leaderboard) == 1
    assert leaderboard[0].mean == pytest.approx(0.3)
    assert leaderboard[0].median == pytest.approx(0.3)
    assert leaderboard[0].n_sequences == 2
    assert leaderboard[0].n_total_sequences == 3


# ---------------------------------------------------------------------------
# build_coverage_matrix
# ---------------------------------------------------------------------------


def test_build_coverage_matrix_includes_all_sequences_even_without_runs() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02", "advio-03"],
        coverage=[
            _make_coverage(sequence_id="advio-01", run_id="run-01", method="vista"),
        ],
        metric_rows=[],
    )

    matrix = build_coverage_matrix(selection)

    assert set(matrix.sequence_ids) == {"advio-01", "advio-02", "advio-03"}
    assert "vista" in matrix.methods


def test_build_coverage_matrix_cell_reflects_manifest_presence() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02"],
        coverage=[
            _make_coverage(sequence_id="advio-01", run_id="run-01", method="vista", manifest_present=True),
            _make_coverage(sequence_id="advio-02", run_id="run-02", method="vista", manifest_present=False),
        ],
        metric_rows=[],
    )

    matrix = build_coverage_matrix(selection)
    cell_map = {(c.sequence_id, c.method): c for c in matrix.cells}

    assert cell_map[("advio-01", "vista")].manifest_present is True
    assert cell_map[("advio-02", "vista")].manifest_present is False
    assert cell_map[("advio-01", "vista")].metric_row_count == 5


# ---------------------------------------------------------------------------
# build_heatmap_data
# ---------------------------------------------------------------------------


def test_build_heatmap_data_fills_matrix_with_none_for_missing_entries() -> None:
    selection = _make_selection(
        all_sequence_ids=["advio-01", "advio-02"],
        coverage=[_make_coverage(sequence_id="advio-01", run_id="run-01", method="vista")],
        metric_rows=[
            _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw", value=0.5),
        ],
    )
    rows = build_per_sequence_table(selection, MetricFilter())
    heatmap = build_heatmap_data(rows, ["advio-01", "advio-02"])

    assert heatmap.sequence_ids == ["advio-01", "advio-02"]
    assert "vista/raw" in heatmap.estimate_sources
    src_index = heatmap.estimate_sources.index("vista/raw")
    assert heatmap.values[0][src_index] == pytest.approx(0.5)
    assert heatmap.values[1][src_index] is None


def test_build_heatmap_data_uses_provided_metric_name() -> None:
    rows = build_per_sequence_table(
        _make_selection(
            all_sequence_ids=["advio-01"],
            coverage=[_make_coverage(sequence_id="advio-01", run_id="run-01")],
            metric_rows=[
                _make_metric_row(run_id="run-01", sequence_id="advio-01", estimate_source="vista/raw"),
            ],
        ),
        MetricFilter(),
    )
    heatmap = build_heatmap_data(rows, ["advio-01"], metric_name="APE RMSE (m)")

    assert heatmap.metric_name == "APE RMSE (m)"
