"""Tests for the metrics-first Streamlit app."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from prml_vslam.app import bootstrap
from prml_vslam.app.models import DatasetId, EvaluationControls
from prml_vslam.app.services import MetricsAppService
from prml_vslam.utils.path_config import PathConfig

pytest.importorskip("evo")


def _write_tum(path: Path, rows: list[tuple[float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{t:.1f} {x:.3f} {y:.3f} {z:.3f} 0 0 0 1" for t, x, y, z in rows) + "\n",
        encoding="utf-8",
    )


def _build_path_config(tmp_path: Path) -> PathConfig:
    sequence_root = tmp_path / "data" / "advio" / "advio-15" / "ground-truth"
    run_root = tmp_path / "artifacts" / "advio-15" / "vista_slam" / "slam"
    _write_tum(
        sequence_root / "ground_truth.tum",
        [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0), (0.2, 2.0, 1.0, 0.0)],
    )
    _write_tum(
        run_root / "trajectory.tum",
        [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.0, 0.0), (0.2, 2.2, 0.9, 0.0)],
    )
    return PathConfig(
        root=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        captures_dir=tmp_path / "captures",
    )


def test_metrics_service_discovers_and_persists_evo_results(tmp_path: Path) -> None:
    path_config = _build_path_config(tmp_path)
    service = MetricsAppService(path_config)

    runs = service.discover_runs(DatasetId.ADVIO, "advio-15")

    assert len(runs) == 1
    selection = service.resolve_selection(
        dataset=DatasetId.ADVIO,
        sequence_slug="advio-15",
        run_root=runs[0].artifact_root,
    )
    assert selection is not None

    result = service.compute_evaluation(
        selection=selection,
        controls=EvaluationControls(),
    )

    assert result.path.exists()
    assert result.matched_pairs == 3
    assert result.stats.rmse > 0.0
    assert len(result.trajectories) == 2


def test_run_app_renders_persisted_metrics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = _build_path_config(tmp_path)
    service = MetricsAppService(path_config)
    selection = service.resolve_selection(
        dataset=DatasetId.ADVIO,
        sequence_slug="advio-15",
        run_root=service.discover_runs(DatasetId.ADVIO, "advio-15")[0].artifact_root,
    )
    assert selection is not None
    service.compute_evaluation(selection=selection, controls=EvaluationControls())

    monkeypatch.setattr(bootstrap, "get_path_config", lambda: path_config)

    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    at = AppTest.from_file(str(app_path))
    at.run()

    assert at.title[0].value == "Trajectory Metrics"
    assert at.button[0].label == "Compute evo metrics"
    assert {metric.label for metric in at.metric} >= {"RMSE", "Mean", "Median", "Max"}
