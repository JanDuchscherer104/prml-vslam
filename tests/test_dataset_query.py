"""Tests for dataset-wide trajectory evaluation query helpers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from prml_vslam.eval.query import TrajectoryEvaluationQueryService
from prml_vslam.eval.services import TrajectoryEvaluationRepairService
from prml_vslam.eval.trajectory_contracts import stable_run_id
from prml_vslam.interfaces import FrameTransform
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import write_tum_trajectory


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


def _write_evaluation_manifest(
    eval_dir: Path,
    *,
    sequence_id: str,
    run_id: str,
    skipped_metrics: list[dict] | None = None,
) -> None:
    eval_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "artifact_root": str(eval_dir.parent.parent),
        "sequence_id": sequence_id,
        "run_id": run_id,
        "reference_trajectories": [],
        "candidate_trajectories": [],
        "error_series_paths": [],
        "evaluation_cases": [],
        "skipped_metrics": skipped_metrics or [],
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
    run_id = f"{sequence_id}/{method}"
    _write_sequence_manifest(run_root / "input", sequence_id=sequence_id, dataset_id="advio")
    _write_trajectory(run_root / "slam" / "trajectory.tum")
    eval_dir = run_root / "evaluation" / "trajectory"
    _write_evaluation_manifest(eval_dir, sequence_id=sequence_id, run_id=run_id)
    _write_metrics_long(eval_dir, sequence_id=sequence_id, run_id=run_id)
    return run_root


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
    assert result.coverage[0].run_id == "advio-20/vista"
    assert result.metric_rows[0].run_id == "advio-20/vista"


def test_load_dataset_evaluation_keeps_same_method_runs_distinct(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    run_a = _build_advio_run(artifacts, sequence_id="exp-a", method="vista")
    run_b = _build_advio_run(artifacts, sequence_id="exp-b", method="vista")
    for run_root in (run_a, run_b):
        _write_sequence_manifest(run_root / "input", sequence_id="advio-20", dataset_id="advio")
        eval_dir = run_root / "evaluation" / "trajectory"
        run_id = stable_run_id(run_root, PathConfig(root=tmp_path, artifacts_dir=artifacts))
        _write_evaluation_manifest(eval_dir, sequence_id="advio-20", run_id=run_id)
        _write_metrics_long(eval_dir, sequence_id="advio-20", run_id=run_id)

    service = TrajectoryEvaluationQueryService(PathConfig(root=tmp_path, artifacts_dir=artifacts))

    with patch("prml_vslam.eval.query.list_sequence_slugs", return_value=["advio-20"]):
        result = service.load_dataset_evaluation(DatasetId.ADVIO)

    assert {item.run_id for item in result.coverage} == {"exp-a/vista", "exp-b/vista"}
    assert {row.run_id for row in result.metric_rows} == {"exp-a/vista", "exp-b/vista"}


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


def _write_four_pose_trajectory(path: Path) -> Path:
    """Write a non-degenerate 4-pose trajectory (required for Sim3 rank check)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    return write_tum_trajectory(
        path,
        poses=[
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=1.0, tz=0.0),
            FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=1.0, tz=0.0),
        ],
        timestamps=[0.0, 1.0, 2.0, 3.0],
    )


def _write_benchmark_inputs_json(
    run_root: Path,
    *,
    reference_path: Path,
    candidate_paths: list[tuple[Path, str, str]] | None = None,
) -> None:
    inputs = {
        "reference_trajectories": [
            {
                "source": "ground_truth",
                "path": str(reference_path),
                "target_frame": "advio_gt_world",
                "coordinate_status": "source_native",
            }
        ],
        "candidate_trajectories": [
            {"source": source, "path": str(path), "coordinate_status": status}
            for path, source, status in (candidate_paths or [])
        ],
        "reference_clouds": [],
        "observation_sequences": [],
    }
    benchmark_dir = run_root / "benchmark"
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    (benchmark_dir / "inputs.json").write_text(json.dumps(inputs), encoding="utf-8")


def test_recompute_run_evaluation_regenerates_manifest_from_benchmark_inputs_json(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    run_root = artifacts / "advio-20" / "vista"
    _write_sequence_manifest(run_root / "input", sequence_id="advio-20", dataset_id="advio")
    _write_four_pose_trajectory(run_root / "slam" / "trajectory.tum")
    reference_path = _write_four_pose_trajectory(run_root / "benchmark" / "ground_truth.tum")
    _write_benchmark_inputs_json(run_root, reference_path=reference_path)

    path_config = PathConfig(root=tmp_path, artifacts_dir=artifacts)
    query = TrajectoryEvaluationQueryService(path_config)
    service = TrajectoryEvaluationRepairService(path_config)
    run = query.discover_runs("advio-20", dataset=DatasetId.ADVIO)[0]

    manifest = service.recompute_run_evaluation(run)

    manifest_path = run_root / "evaluation" / "trajectory" / "manifest.json"
    assert manifest_path.exists()
    assert manifest.sequence_id == "advio-20"
    assert manifest.run_id == "advio-20/vista"
    assert len(manifest.evaluation_cases) >= 1
    assert any(c.metric_family == "ape" for c in manifest.evaluation_cases)
