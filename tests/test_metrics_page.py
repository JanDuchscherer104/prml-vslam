"""Tests for metrics page helpers (pure data-transform functions)."""

from __future__ import annotations

from pathlib import Path

import pytest
from evo.core import metrics

from prml_vslam.eval.dataset_aggregation import build_wide_metric_rows
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow

_AGGREGATE_SEQUENCE_LABEL = "All sequences"


def _rmse_row(
    *,
    run_id: str = "run-a",
    sequence_id: str = "advio-20",
    reference_source: str = "ground_truth",
    estimate_source: str = "vista/raw",
    metric_family: str = "ape",
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part,
    value: float = 0.25,
    matched_pairs: int = 50,
) -> TrajectoryMetricResultRow:
    return TrajectoryMetricResultRow(
        run_id=run_id,
        sequence_id=sequence_id,
        reference_source=reference_source,
        estimate_source=estimate_source,
        metric_family=metric_family,
        pose_relation=pose_relation,
        statistic="rmse",
        value=value,
        unit="m",
        matched_pairs=matched_pairs,
    )


def _stat_row(
    *,
    statistic: str = "mean",
    value: float = 0.2,
) -> TrajectoryMetricResultRow:
    return TrajectoryMetricResultRow(
        run_id="run-a",
        sequence_id="advio-20",
        reference_source="ground_truth",
        estimate_source="vista/raw",
        metric_family="ape",
        pose_relation=metrics.PoseRelation.translation_part,
        statistic=statistic,
        value=value,
        unit="m",
        matched_pairs=50,
    )


def _sequence_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["Sequence"] != _AGGREGATE_SEQUENCE_LABEL]


def _aggregate_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row["Sequence"] == _AGGREGATE_SEQUENCE_LABEL]


# ---------------------------------------------------------------------------
# build_wide_metric_rows
# ---------------------------------------------------------------------------


def test_build_wide_metric_rows_produces_one_row_per_run_reference_estimate() -> None:
    rows = [
        _rmse_row(metric_family="ape", pose_relation=metrics.PoseRelation.translation_part, value=0.10),
        _rmse_row(metric_family="ape", pose_relation=metrics.PoseRelation.rotation_angle_deg, value=1.5),
        _rmse_row(metric_family="rpe", pose_relation=metrics.PoseRelation.translation_part, value=0.05),
        _rmse_row(metric_family="rpe", pose_relation=metrics.PoseRelation.rotation_angle_deg, value=0.8),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 1
    assert len(_aggregate_rows(result)) == 1
    row = _sequence_rows(result)[0]
    assert row["Run"] == "run-a"
    assert row["Sequence"] == "advio-20"
    assert row["Reference"] == "ground_truth"
    assert row["Estimate"] == "vista"
    assert row["Coordinate Status"] == "raw"
    assert row["APE Trans. RMSE (m)"] == pytest.approx(0.10, abs=1e-4)
    assert row["APE Rot. RMSE (deg)"] == pytest.approx(1.5, abs=1e-4)
    assert row["RPE Trans. RMSE (m)"] == pytest.approx(0.05, abs=1e-4)
    assert row["RPE Rot. RMSE (deg)"] == pytest.approx(0.8, abs=1e-4)
    assert row["APE Pairs"] == 50
    assert row["RPE Pairs"] == 50


def test_build_wide_metric_rows_leaves_none_for_missing_metrics() -> None:
    rows = [_rmse_row(metric_family="ape", pose_relation=metrics.PoseRelation.translation_part, value=0.25)]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 1
    row = _sequence_rows(result)[0]
    assert row["APE Trans. RMSE (m)"] == pytest.approx(0.25)
    assert row["APE Rot. RMSE (deg)"] is None
    assert row["RPE Trans. RMSE (m)"] is None
    assert row["RPE Rot. RMSE (deg)"] is None
    assert row["APE Pairs"] == 50
    assert row["RPE Pairs"] is None


def test_build_wide_metric_rows_keeps_separate_rows_for_distinct_run_ids() -> None:
    rows = [
        _rmse_row(run_id="run-a", estimate_source="vista/raw", value=0.10),
        _rmse_row(run_id="run-b", estimate_source="vista/raw", value=0.30),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 2
    assert len(_aggregate_rows(result)) == 2
    run_ids = {r["Run"] for r in _sequence_rows(result)}
    assert run_ids == {"run-a", "run-b"}


def test_build_wide_metric_rows_keeps_same_run_id_separate_across_sequences() -> None:
    rows = [
        _rmse_row(run_id="vista", sequence_id="advio-20", estimate_source="vista/raw", value=0.10),
        _rmse_row(run_id="vista", sequence_id="advio-21", estimate_source="vista/raw", value=0.30),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 2
    assert len(_aggregate_rows(result)) == 1
    assert {r["Sequence"] for r in _sequence_rows(result)} == {"advio-20", "advio-21"}
    assert [r["APE Trans. RMSE (m)"] for r in _sequence_rows(result)] == [
        pytest.approx(0.10),
        pytest.approx(0.30),
    ]


def test_build_wide_metric_rows_splits_estimate_source_into_estimate_and_coord_status() -> None:
    rows = [
        _rmse_row(estimate_source="arcore/source_native"),
        _rmse_row(estimate_source="arcore/aligned"),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 2
    assert len(_aggregate_rows(result)) == 2
    statuses = {r["Coordinate Status"] for r in _sequence_rows(result)}
    assert statuses == {"source_native", "aligned"}
    assert all(r["Estimate"] == "arcore" for r in _sequence_rows(result))


def test_build_wide_metric_rows_ignores_non_rmse_statistics() -> None:
    rows = [
        _rmse_row(value=0.25),
        _stat_row(statistic="mean", value=0.20),
        _stat_row(statistic="median", value=0.18),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 1
    assert _sequence_rows(result)[0]["APE Trans. RMSE (m)"] == pytest.approx(0.25)


def test_build_wide_metric_rows_returns_empty_for_no_rmse_rows() -> None:
    rows = [_stat_row(statistic="mean"), _stat_row(statistic="median")]

    result = build_wide_metric_rows(rows)

    assert result == []


def test_build_wide_metric_rows_sorts_by_sequence_run_reference_estimate_coord() -> None:
    rows = [
        _rmse_row(sequence_id="advio-21", run_id="run-b", estimate_source="vista/raw"),
        _rmse_row(sequence_id="advio-20", run_id="run-a", estimate_source="arcore/source_native"),
        _rmse_row(sequence_id="advio-20", run_id="run-a", estimate_source="arcore/aligned"),
    ]

    result = build_wide_metric_rows(rows)
    rows = _sequence_rows(result)

    assert len(rows) == 3
    assert rows[0]["Sequence"] == "advio-20"
    assert rows[0]["Run"] == "run-a"
    assert rows[0]["Coordinate Status"] == "aligned"
    assert rows[1]["Coordinate Status"] == "source_native"
    assert rows[2]["Sequence"] == "advio-21"
    assert rows[2]["Run"] == "run-b"


def test_build_wide_metric_rows_adds_pooled_all_sequences_row() -> None:
    rows = [
        _rmse_row(
            sequence_id="advio-20",
            metric_family="ape",
            pose_relation=metrics.PoseRelation.translation_part,
            value=0.10,
            matched_pairs=100,
        ),
        _rmse_row(
            sequence_id="advio-21",
            metric_family="ape",
            pose_relation=metrics.PoseRelation.translation_part,
            value=0.30,
            matched_pairs=300,
        ),
        _rmse_row(
            sequence_id="advio-20",
            metric_family="rpe",
            pose_relation=metrics.PoseRelation.translation_part,
            value=0.20,
            matched_pairs=10,
        ),
        _rmse_row(
            sequence_id="advio-21",
            metric_family="rpe",
            pose_relation=metrics.PoseRelation.translation_part,
            value=0.40,
            matched_pairs=30,
        ),
    ]

    result = build_wide_metric_rows(rows)

    assert len(_sequence_rows(result)) == 2
    aggregate = _aggregate_rows(result)[0]
    assert aggregate["Run"] == "run-a"
    assert aggregate["Reference"] == "ground_truth"
    assert aggregate["Estimate"] == "vista"
    assert aggregate["Coordinate Status"] == "raw"
    assert aggregate["APE Trans. RMSE (m)"] == pytest.approx(0.2646, abs=1e-4)
    assert aggregate["RPE Trans. RMSE (m)"] == pytest.approx(0.3606, abs=1e-4)
    assert aggregate["APE Pairs"] == 400
    assert aggregate["RPE Pairs"] == 40


def test_build_wide_metric_rows_aggregate_leaves_missing_metrics_empty() -> None:
    rows = [
        _rmse_row(sequence_id="advio-20", metric_family="ape", value=0.10, matched_pairs=100),
        _rmse_row(sequence_id="advio-21", metric_family="ape", value=0.30, matched_pairs=300),
    ]

    result = build_wide_metric_rows(rows)

    aggregate = _aggregate_rows(result)[0]
    assert aggregate["APE Trans. RMSE (m)"] == pytest.approx(0.2646, abs=1e-4)
    assert aggregate["APE Pairs"] == 400
    assert aggregate["RPE Trans. RMSE (m)"] is None
    assert aggregate["RPE Rot. RMSE (deg)"] is None
    assert aggregate["RPE Pairs"] is None


def test_metrics_page_does_not_render_recompute_button() -> None:
    source = (Path(__file__).parents[1] / "src" / "prml_vslam" / "app" / "pages" / "metrics.py").read_text(
        encoding="utf-8"
    )

    assert "st.button" not in source
    assert "_render_recompute_button" not in source


def test_metrics_page_uses_available_persisted_metric_keys() -> None:
    source = (Path(__file__).parents[1] / "src" / "prml_vslam" / "app" / "pages" / "metrics.py").read_text(
        encoding="utf-8"
    )

    assert "_PRIMARY_METRIC_OPTIONS" not in source
    assert "available_metric_keys(dataset_selection.metric_rows)" in source
