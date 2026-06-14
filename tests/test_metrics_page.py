"""Tests for metrics page helpers (pure data-transform functions)."""

from __future__ import annotations

import pytest
from evo.core import metrics

from prml_vslam.app.pages.metrics import _build_wide_metric_rows
from prml_vslam.eval.trajectory_contracts import TrajectoryMetricResultRow


def _rmse_row(
    *,
    run_id: str = "run-a",
    reference_source: str = "ground_truth",
    estimate_source: str = "vista/raw",
    metric_family: str = "ape",
    pose_relation: metrics.PoseRelation = metrics.PoseRelation.translation_part,
    value: float = 0.25,
    matched_pairs: int = 50,
) -> TrajectoryMetricResultRow:
    return TrajectoryMetricResultRow(
        run_id=run_id,
        sequence_id="advio-20",
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


# ---------------------------------------------------------------------------
# _build_wide_metric_rows
# ---------------------------------------------------------------------------


def test_build_wide_metric_rows_produces_one_row_per_run_reference_estimate() -> None:
    rows = [
        _rmse_row(metric_family="ape", pose_relation=metrics.PoseRelation.translation_part, value=0.10),
        _rmse_row(metric_family="ape", pose_relation=metrics.PoseRelation.rotation_angle_deg, value=1.5),
        _rmse_row(metric_family="rpe", pose_relation=metrics.PoseRelation.translation_part, value=0.05),
        _rmse_row(metric_family="rpe", pose_relation=metrics.PoseRelation.rotation_angle_deg, value=0.8),
    ]

    result = _build_wide_metric_rows(rows)

    assert len(result) == 1
    row = result[0]
    assert row["Run"] == "run-a"
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

    result = _build_wide_metric_rows(rows)

    assert len(result) == 1
    assert result[0]["APE Trans. RMSE (m)"] == pytest.approx(0.25)
    assert result[0]["APE Rot. RMSE (deg)"] is None
    assert result[0]["RPE Trans. RMSE (m)"] is None
    assert result[0]["RPE Rot. RMSE (deg)"] is None
    assert result[0]["APE Pairs"] == 50
    assert result[0]["RPE Pairs"] is None


def test_build_wide_metric_rows_keeps_separate_rows_for_distinct_run_ids() -> None:
    rows = [
        _rmse_row(run_id="run-a", estimate_source="vista/raw", value=0.10),
        _rmse_row(run_id="run-b", estimate_source="vista/raw", value=0.30),
    ]

    result = _build_wide_metric_rows(rows)

    assert len(result) == 2
    run_ids = {r["Run"] for r in result}
    assert run_ids == {"run-a", "run-b"}


def test_build_wide_metric_rows_splits_estimate_source_into_estimate_and_coord_status() -> None:
    rows = [
        _rmse_row(estimate_source="arcore/source_native"),
        _rmse_row(estimate_source="arcore/aligned"),
    ]

    result = _build_wide_metric_rows(rows)

    assert len(result) == 2
    statuses = {r["Coordinate Status"] for r in result}
    assert statuses == {"source_native", "aligned"}
    assert all(r["Estimate"] == "arcore" for r in result)


def test_build_wide_metric_rows_ignores_non_rmse_statistics() -> None:
    rows = [
        _rmse_row(value=0.25),
        _stat_row(statistic="mean", value=0.20),
        _stat_row(statistic="median", value=0.18),
    ]

    result = _build_wide_metric_rows(rows)

    assert len(result) == 1
    assert result[0]["APE Trans. RMSE (m)"] == pytest.approx(0.25)


def test_build_wide_metric_rows_returns_empty_for_no_rmse_rows() -> None:
    rows = [_stat_row(statistic="mean"), _stat_row(statistic="median")]

    result = _build_wide_metric_rows(rows)

    assert result == []


def test_build_wide_metric_rows_sorts_by_run_reference_estimate_coord() -> None:
    rows = [
        _rmse_row(run_id="run-b", estimate_source="vista/raw"),
        _rmse_row(run_id="run-a", estimate_source="arcore/source_native"),
        _rmse_row(run_id="run-a", estimate_source="arcore/aligned"),
    ]

    result = _build_wide_metric_rows(rows)

    assert len(result) == 3
    assert result[0]["Run"] == "run-a"
    assert result[0]["Coordinate Status"] == "aligned"
    assert result[1]["Coordinate Status"] == "source_native"
    assert result[2]["Run"] == "run-b"
