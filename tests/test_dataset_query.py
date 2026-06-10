"""Tests for dataset-wide trajectory evaluation query helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from evo.core import metrics

from prml_vslam.eval.query import TrajectoryEvaluationQueryService
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import write_tum_trajectory
from prml_vslam.interfaces import FrameTransform


def _write_sequence_manifest(path: Path, *, sequence_id: str, dataset_id: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "sequence_id": sequence_id,
        "dataset_id": dataset_id,
    }
    (path / "sequence_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_trajectory(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_tum_trajectory(
        path,
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0],
    )


def _write_evaluation_manifest(eval_dir: Path, *, sequence_id: str, run_id: str) -> None:
    eval_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_root": str(eval_dir.parent.parent),
        "sequence_id": sequence_id,
        "run_id": run_id,
        "reference_trajectories": [],
        "candidate_trajectories": [],
        "error_series_paths": [],
        "evaluation_cases": [],
    }
    (eval_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _write_metrics_long(eval_dir: Path, *, sequence_id: str, run_id: str, estimate_source: str = "vista/raw") -> None:
    eval_dir.mkdir(parents=True, exist_ok=True)
    # pose_relation must be the enum .value (e.g. "translation part" with a space), matching
    # how _write_metric_rows serializes via model_dump(mode="json")
    rows = [
        {
            "run_id": run_id,
            "sequence_id": sequence_id,
            "reference_source": "ground_truth",
            "estimate_source": estimate_source,
            "metric_family": "ape",
            "pose_relation": "translation part",
            "statistic": "rmse",
            "value": "0.25",
            "unit": "m",
            "matched_pairs": "50",
            "delta": "",
            "delta_unit": "",
            "error_series_path": "",
        }
    ]
    with (eval_dir / "metrics_long.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _build_advio_run(
    artifacts_root: Path,
    *,
    sequence_id: str,
    method: str = "vista",
) -> Path:
    """Create a minimal run artifact tree for one ADVIO sequence."""
    run_root = artifacts_root / sequence_id / method
    _write_sequence_manifest(run_root / "input", sequence_id=sequence_id, dataset_id="advio")
    _write_trajectory(run_root / "slam" / "trajectory.tum")
    eval_dir = run_root / "evaluation" / "trajectory"
    _write_evaluation_manifest(eval_dir, sequence_id=sequence_id, run_id=run_root.name)
    _write_metrics_long(eval_dir, sequence_id=sequence_id, run_id=run_root.name)
    return run_root


# ---------------------------------------------------------------------------
# discover_dataset_runs
# ---------------------------------------------------------------------------


def test_discover_dataset_runs_finds_advio_trajectory(tmp_path: Path) -> None:
    _build_advio_run(tmp_path / "artifacts", sequence_id="advio-20")
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / "artifacts")
    service = TrajectoryEvaluationQueryService(path_config)

    runs = service.discover_dataset_runs(DatasetId.ADVIO)

    assert len(runs) == 1
    assert runs[0].artifact_root.name == "vista"


def test_discover_dataset_runs_excludes_mismatched_dataset(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    _build_advio_run(artifacts, sequence_id="advio-20")
    # Write a TUM RGB-D sequence manifest to another run
    tum_run = artifacts / "tum-desk" / "vista"
    _write_sequence_manifest(tum_run / "input", sequence_id="tum-desk", dataset_id="tum_rgbd")
    _write_trajectory(tum_run / "slam" / "trajectory.tum")

    path_config = PathConfig(root=tmp_path, artifacts_dir=artifacts)
    service = TrajectoryEvaluationQueryService(path_config)

    advio_runs = service.discover_dataset_runs(DatasetId.ADVIO)
    tum_runs = service.discover_dataset_runs(DatasetId.TUM_RGBD)

    assert len(advio_runs) == 1
    assert len(tum_runs) == 1


# ---------------------------------------------------------------------------
# load_dataset_evaluation
# ---------------------------------------------------------------------------


def test_load_dataset_evaluation_returns_coverage_and_metric_rows(tmp_path: Path) -> None:
    _build_advio_run(tmp_path / "artifacts", sequence_id="advio-20")
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / "artifacts")
    service = TrajectoryEvaluationQueryService(path_config)

    with patch("prml_vslam.eval.query.list_sequence_slugs", return_value=["advio-20", "advio-21"]):
        result = service.load_dataset_evaluation(DatasetId.ADVIO)

    assert result.dataset is DatasetId.ADVIO
    assert set(result.all_sequence_ids) == {"advio-20", "advio-21"}
    assert len(result.coverage) == 1
    assert result.coverage[0].sequence_id == "advio-20"
    assert result.coverage[0].manifest_present is True
    assert result.coverage[0].metric_row_count == 1
    assert len(result.metric_rows) == 1
    assert result.metric_rows[0].value == pytest.approx(0.25)


def test_load_dataset_evaluation_handles_missing_manifest_gracefully(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    run_root = artifacts / "advio-20" / "vista"
    _write_sequence_manifest(run_root / "input", sequence_id="advio-20", dataset_id="advio")
    _write_trajectory(run_root / "slam" / "trajectory.tum")
    # No manifest or metrics_long.csv written intentionally

    path_config = PathConfig(root=tmp_path, artifacts_dir=artifacts)
    service = TrajectoryEvaluationQueryService(path_config)

    with patch("prml_vslam.eval.query.list_sequence_slugs", return_value=["advio-20"]):
        result = service.load_dataset_evaluation(DatasetId.ADVIO)

    assert len(result.coverage) == 1
    assert result.coverage[0].manifest_present is False
    assert result.coverage[0].metric_row_count == 0
    assert result.metric_rows == []


# ---------------------------------------------------------------------------
# load_dataset_coverage
# ---------------------------------------------------------------------------


def test_load_dataset_coverage_convenience_wrapper_matches_evaluation(tmp_path: Path) -> None:
    _build_advio_run(tmp_path / "artifacts", sequence_id="advio-20")
    path_config = PathConfig(root=tmp_path, artifacts_dir=tmp_path / "artifacts")
    service = TrajectoryEvaluationQueryService(path_config)

    with patch("prml_vslam.eval.query.list_sequence_slugs", return_value=["advio-20"]):
        coverage = service.load_dataset_coverage(DatasetId.ADVIO)
        evaluation = service.load_dataset_evaluation(DatasetId.ADVIO)

    assert coverage == evaluation.coverage
