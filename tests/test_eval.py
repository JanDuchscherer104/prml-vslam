"""Focused tests for evaluation-stage protocol seams."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.eval.contracts import (
    DenseCloudEvaluationArtifact,
    DenseCloudEvaluationSelection,
    EfficiencyEvaluationArtifact,
    EfficiencyEvaluationSelection,
)
from prml_vslam.eval.protocols import DenseCloudEvaluator, EfficiencyEvaluator, TrajectoryEvaluator
from prml_vslam.eval.services import TrajectoryEvaluationService, compute_trajectory_ape_preview
from prml_vslam.utils import PathConfig


class FakeDenseCloudEvaluationService:
    """Small dense-cloud evaluator stand-in for protocol tests."""

    def load_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact | None:
        return None if selection.artifact_root.name == "missing" else self.compute_dense_evaluation(selection=selection)

    def compute_dense_evaluation(
        self,
        *,
        selection: DenseCloudEvaluationSelection,
    ) -> DenseCloudEvaluationArtifact:
        return DenseCloudEvaluationArtifact(
            path=selection.artifact_root / "evaluation" / "cloud_metrics.json",
            title="Dense Cloud Metrics",
            reference_cloud_path=selection.reference_cloud_path,
            estimate_cloud_path=selection.estimate_cloud_path,
            metrics={"chamfer_l1": 0.5},
        )


class FakeEfficiencyEvaluationService:
    """Small efficiency evaluator stand-in for protocol tests."""

    def load_efficiency_evaluation(
        self,
        *,
        selection: EfficiencyEvaluationSelection,
    ) -> EfficiencyEvaluationArtifact | None:
        return (
            None
            if selection.artifact_root.name == "missing"
            else self.compute_efficiency_evaluation(selection=selection)
        )

    def compute_efficiency_evaluation(
        self,
        *,
        selection: EfficiencyEvaluationSelection,
    ) -> EfficiencyEvaluationArtifact:
        return EfficiencyEvaluationArtifact(
            path=selection.artifact_root / "evaluation" / "efficiency_metrics.json",
            title="Efficiency Metrics",
            metrics={"latency_ms": 125.0},
        )


def test_trajectory_evaluation_service_satisfies_protocol(tmp_path: Path) -> None:
    service = TrajectoryEvaluationService(PathConfig(root=tmp_path))

    assert isinstance(service, TrajectoryEvaluator)


def test_compute_trajectory_ape_preview_returns_matched_error_series(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.tum"
    estimate_path = tmp_path / "estimate.tum"
    _write_tum(reference_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.0, 0.0, 0.0)])
    _write_tum(estimate_path, [(0.0, 0.0, 0.0, 0.0), (0.1, 1.1, 0.1, 0.0)])

    preview = compute_trajectory_ape_preview(reference_path=reference_path, estimate_path=estimate_path)

    assert len(preview.error_series.values) == 2
    assert preview.stats.rmse > 0.0


def test_dense_cloud_protocol_accepts_structural_implementations(tmp_path: Path) -> None:
    service = FakeDenseCloudEvaluationService()
    selection = DenseCloudEvaluationSelection(
        artifact_root=tmp_path / "run",
        reference_cloud_path=tmp_path / "reference.ply",
        estimate_cloud_path=tmp_path / "estimate.ply",
    )

    assert isinstance(service, DenseCloudEvaluator)
    assert service.compute_dense_evaluation(selection=selection).metrics["chamfer_l1"] == 0.5


def test_efficiency_protocol_accepts_structural_implementations(tmp_path: Path) -> None:
    service = FakeEfficiencyEvaluationService()
    selection = EfficiencyEvaluationSelection(artifact_root=tmp_path / "run")

    assert isinstance(service, EfficiencyEvaluator)
    assert service.compute_efficiency_evaluation(selection=selection).metrics["latency_ms"] == 125.0


def _write_tum(path: Path, rows: list[tuple[float, float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{timestamp} {tx} {ty} {tz} 0 0 0 1" for timestamp, tx, ty, tz in rows),
        encoding="utf-8",
    )
