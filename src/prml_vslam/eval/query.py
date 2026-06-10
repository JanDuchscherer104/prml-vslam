"""Read-only query helpers for persisted evaluation artifacts.

The service layer owns metric computation. This module turns persisted
trajectory and dense-cloud evaluation artifacts into long-form rows that app,
reporting, and notebooks can aggregate without knowing each JSON schema.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from prml_vslam.eval.contracts import DenseCloudEvaluationArtifact, EvaluationArtifact
from prml_vslam.utils import BaseData


class EvaluationMetricRow(BaseData):
    """One long-form metric row from a persisted evaluation artifact."""

    evaluation_kind: str
    """High-level evaluation family, such as ``trajectory`` or ``point_cloud``."""

    metric_id: str
    """Canonical metric identifier."""

    value: float
    """Scalar metric value."""

    unit: str = ""
    """Metric unit, when applicable."""

    source_artifact_path: Path
    """Metrics JSON artifact that produced this row."""

    reference_artifact_path: Path | None = None
    """Reference artifact used by the metric."""

    estimate_artifact_path: Path | None = None
    """Estimate artifact used by the metric."""

    estimate_kind: str | None = None
    """Point-cloud estimate role when the metric is cloud-specific."""

    threshold_m: float | None = None
    """Distance threshold in meters for thresholded metrics such as F1."""

    context: dict[str, str | int | float] = Field(default_factory=dict)
    """Optional caller-supplied identifiers such as run, sequence, or method."""

    def table_row(self) -> dict[str, str | int | float | None]:
        """Return a Streamlit/dataframe-friendly row."""
        return {
            **self.context,
            "Evaluation": self.evaluation_kind,
            "Estimate": self.estimate_kind,
            "Metric": self.metric_id,
            "Value": self.value,
            "Unit": self.unit,
            "Threshold (m)": self.threshold_m,
            "Reference": self.reference_artifact_path.as_posix() if self.reference_artifact_path else None,
            "Estimate Artifact": self.estimate_artifact_path.as_posix() if self.estimate_artifact_path else None,
            "Metrics Artifact": self.source_artifact_path.as_posix(),
        }


def trajectory_metric_rows(
    artifact: EvaluationArtifact,
    *,
    context: dict[str, str | int | float] | None = None,
) -> list[EvaluationMetricRow]:
    """Return long-form summary rows for one trajectory evaluation artifact."""
    base = {
        "evaluation_kind": "trajectory",
        "source_artifact_path": artifact.path,
        "reference_artifact_path": artifact.reference_path,
        "estimate_artifact_path": artifact.estimate_path,
        "context": context or {},
    }
    return [
        EvaluationMetricRow(metric_id="ape.translation.rmse", value=artifact.stats.rmse, unit="m", **base),
        EvaluationMetricRow(metric_id="ape.translation.mean", value=artifact.stats.mean, unit="m", **base),
        EvaluationMetricRow(metric_id="ape.translation.median", value=artifact.stats.median, unit="m", **base),
        EvaluationMetricRow(metric_id="ape.translation.std", value=artifact.stats.std, unit="m", **base),
        EvaluationMetricRow(metric_id="ape.translation.min", value=artifact.stats.min, unit="m", **base),
        EvaluationMetricRow(metric_id="ape.translation.max", value=artifact.stats.max, unit="m", **base),
        EvaluationMetricRow(metric_id="matched_pairs", value=float(artifact.matched_pairs), unit="count", **base),
    ]


def dense_cloud_metric_rows(
    artifact: DenseCloudEvaluationArtifact,
    *,
    context: dict[str, str | int | float] | None = None,
) -> list[EvaluationMetricRow]:
    """Return long-form rows for one dense-cloud evaluation artifact."""
    rows: list[EvaluationMetricRow] = []
    for estimate in artifact.estimates:
        for metric_id, value in estimate.metrics.items():
            rows.append(
                EvaluationMetricRow(
                    evaluation_kind="point_cloud",
                    metric_id=metric_id.value,
                    value=value,
                    unit=_cloud_metric_unit(metric_id.value),
                    source_artifact_path=artifact.path,
                    reference_artifact_path=artifact.reference_cloud_path,
                    estimate_artifact_path=estimate.estimate_cloud_path,
                    estimate_kind=estimate.estimate_kind.value,
                    threshold_m=artifact.f1_threshold_m if metric_id.value == "f1" else None,
                    context=context or {},
                )
            )
        rows.extend(
            [
                EvaluationMetricRow(
                    evaluation_kind="point_cloud",
                    metric_id="reference_point_count",
                    value=float(estimate.reference_point_count),
                    unit="count",
                    source_artifact_path=artifact.path,
                    reference_artifact_path=artifact.reference_cloud_path,
                    estimate_artifact_path=estimate.estimate_cloud_path,
                    estimate_kind=estimate.estimate_kind.value,
                    context=context or {},
                ),
                EvaluationMetricRow(
                    evaluation_kind="point_cloud",
                    metric_id="estimate_point_count",
                    value=float(estimate.estimate_point_count),
                    unit="count",
                    source_artifact_path=artifact.path,
                    reference_artifact_path=artifact.reference_cloud_path,
                    estimate_artifact_path=estimate.estimate_cloud_path,
                    estimate_kind=estimate.estimate_kind.value,
                    context=context or {},
                ),
            ]
        )
    return rows


def _cloud_metric_unit(metric_id: str) -> str:
    if metric_id in {"accuracy", "completeness", "chamfer", "icp_rmse"}:
        return "m"
    if metric_id in {"f1", "icp_fitness"}:
        return "ratio"
    return ""


__all__ = [
    "EvaluationMetricRow",
    "dense_cloud_metric_rows",
    "trajectory_metric_rows",
]
