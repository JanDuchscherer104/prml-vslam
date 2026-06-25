"""Read-only query helpers for persisted evaluation artifacts.

The service layer owns metric computation. This module discovers runs, loads
persisted trajectory evaluation manifests, and turns trajectory and dense-cloud
evaluation artifacts into long-form rows that app, reporting, and notebooks can
aggregate without knowing each JSON schema.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import Field

from prml_vslam.eval.contracts import CloudMetricId, DenseCloudEvaluationArtifact
from prml_vslam.eval.dataset_aggregation import metric_frame_to_rows
from prml_vslam.eval.trajectory_contracts import (
    DiscoveredRun,
    TrajectoryEvaluationManifest,
    TrajectoryMetricResultRow,
    stable_run_id,
)
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import SequenceManifest
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.registry import list_sequence_slugs
from prml_vslam.utils import BaseData, PathConfig


class DatasetRunCoverage(BaseData):
    """Coverage summary for one discovered run under a dataset."""

    sequence_id: str
    """Source sequence identifier for this run."""

    run_id: str
    """Stable run identifier derived from the artifact root under ``artifacts_dir``."""

    artifact_root: Path
    """Run artifact root directory."""

    method: str | None = None
    """Known benchmark method id, when it can be inferred from the path."""

    manifest_present: bool = False
    """Whether the canonical trajectory evaluation manifest exists for this run."""

    metric_row_count: int = 0
    """Number of metric rows loaded from ``metrics_long.csv``."""

    matched_pairs: int = 0
    """Sum of matched pairs across all loaded metric rows."""

    load_error: str | None = None
    """Non-fatal loading error, when the manifest or CSV could not be parsed."""

    skipped_metric_count: int = 0
    """Number of non-primary metrics that were attempted but skipped during evaluation."""

    sim3_alignment_skip_count: int = 0
    """Number of metrics skipped because Sim(3) alignment could not be applied."""


class DatasetEvaluationSelection(BaseData):
    """All discovered run coverage and metric rows for one dataset."""

    dataset: DatasetId
    """Dataset this selection covers."""

    all_sequence_ids: list[str] = Field(default_factory=list)
    """All sequence slugs known to the local dataset registry, including those with no runs."""

    coverage: list[DatasetRunCoverage] = Field(default_factory=list)
    """One coverage entry per discovered run, sorted by (sequence_id, method, run_id)."""

    metric_rows: list[TrajectoryMetricResultRow] = Field(default_factory=list)
    """All metric rows loaded across every discovered run."""


class EvaluationSelection(BaseData):
    """Bundle dataset and run choices exposed to review surfaces."""

    dataset: DatasetId
    """Dataset currently selected in the UI."""

    dataset_root: Path
    """Resolved local root for the selected dataset."""

    artifacts_root: Path
    """Configured artifacts root used for run discovery."""

    sequence_slugs: list[str] = Field(default_factory=list)
    """Local sequence slugs currently available under `dataset_root`."""

    sequence_slug: str | None = None
    """Resolved sequence slug after applying user preferences."""

    runs: list[DiscoveredRun] = Field(default_factory=list)
    """Discovered runs matching the resolved sequence."""


class RunTrajectoryEvaluation(BaseData):
    """Loaded trajectory evaluation state for one discovered run."""

    run: DiscoveredRun
    """Run this loaded state describes."""

    manifest: TrajectoryEvaluationManifest | None = None
    """Loaded trajectory evaluation manifest, when present."""

    metric_rows: list[TrajectoryMetricResultRow] = Field(default_factory=list)
    """Loaded long-form metric rows."""

    load_error: str | None = None
    """Non-fatal loading error shown by review surfaces."""

    skipped_metric_count: int = 0
    """Number of non-primary metrics that were skipped during evaluation of this run."""


class EvaluationMetricRow(BaseData):
    """One long-form metric row from a persisted non-trajectory evaluation artifact."""

    evaluation_kind: str
    """High-level evaluation family, such as ``point_cloud``."""

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


class TrajectoryEvaluationQueryService:
    """Read-only post-run query service for trajectory evaluation artifacts."""

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def discover_dataset_runs(self, dataset: DatasetId) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root whose sequence manifest matches ``dataset``."""
        return [
            DiscoveredRun(
                artifact_root=run_root,
                estimate_path=trajectory_path,
                method=method.value if method is not None else None,
                label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
            )
            for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum"))
            for run_root in [trajectory_path.parent.parent]
            for sequence_manifest in [_load_run_sequence_manifest(run_root)]
            if _matches_dataset(sequence_manifest, dataset)
            for relative_parts in [run_root.relative_to(self.path_config.artifacts_dir).parts]
            for method in [
                next(
                    (method for part in reversed(relative_parts) for method in MethodId if part == method.value),
                    None,
                )
            ]
            for visible_parts in [
                [part for part in relative_parts if part not in ({method.value} if method is not None else set())]
            ]
            for label in [method.display_name if method is not None else relative_parts[-1]]
        ]

    def load_dataset_evaluation(self, dataset: DatasetId) -> DatasetEvaluationSelection:
        """Load all run coverage and metric rows for one dataset."""
        dataset_root = self.path_config.resolve_dataset_dir(dataset.value)
        all_sequence_ids = list_sequence_slugs(dataset, dataset_root)
        runs = self.discover_dataset_runs(dataset)
        all_metric_rows: list[TrajectoryMetricResultRow] = []
        coverage: list[DatasetRunCoverage] = []
        for run in runs:
            evaluation = self.load_run_evaluation(run)
            if evaluation.metric_rows:
                sequence_id = evaluation.metric_rows[0].sequence_id
            elif evaluation.manifest is not None:
                sequence_id = evaluation.manifest.sequence_id
            else:
                sm = _load_run_sequence_manifest(run.artifact_root)
                sequence_id = sm.sequence_id if sm is not None else run.artifact_root.name
            coverage.append(
                DatasetRunCoverage(
                    sequence_id=sequence_id,
                    run_id=stable_run_id(run.artifact_root, self.path_config),
                    artifact_root=run.artifact_root,
                    method=run.method,
                    manifest_present=evaluation.manifest is not None,
                    metric_row_count=len(evaluation.metric_rows),
                    matched_pairs=sum(r.matched_pairs for r in evaluation.metric_rows),
                    load_error=evaluation.load_error,
                    skipped_metric_count=evaluation.skipped_metric_count,
                    sim3_alignment_skip_count=_sim3_alignment_skip_count(evaluation.manifest),
                )
            )
            all_metric_rows.extend(evaluation.metric_rows)
        coverage.sort(key=lambda c: (c.sequence_id, c.method or "", c.run_id))
        return DatasetEvaluationSelection(
            dataset=dataset,
            all_sequence_ids=all_sequence_ids,
            coverage=coverage,
            metric_rows=all_metric_rows,
        )

    def load_dataset_coverage(self, dataset: DatasetId) -> list[DatasetRunCoverage]:
        """Return coverage summaries for all runs matching ``dataset``."""
        return self.load_dataset_evaluation(dataset).coverage

    def discover_runs(self, sequence_slug: str | None, dataset: DatasetId | None = None) -> list[DiscoveredRun]:
        """Return all metadata-backed runs under the artifacts root that match one sequence slug."""
        if sequence_slug is None:
            return []
        return [
            DiscoveredRun(
                artifact_root=run_root,
                estimate_path=trajectory_path,
                method=method.value if method is not None else None,
                label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
            )
            for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum"))
            for run_root in [trajectory_path.parent.parent]
            for sequence_manifest in [_load_run_sequence_manifest(run_root)]
            if _matches_selection(sequence_manifest, sequence_slug, dataset)
            for relative_parts in [run_root.relative_to(self.path_config.artifacts_dir).parts]
            for method in [
                next(
                    (method for part in reversed(relative_parts) for method in MethodId if part == method.value),
                    None,
                )
            ]
            for visible_parts in [
                [part for part in relative_parts if part not in ({method.value} if method is not None else set())]
            ]
            for label in [method.display_name if method is not None else relative_parts[-1]]
        ]

    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        preferred_sequence_slug: str | None,
    ) -> EvaluationSelection:
        """Resolve dataset sequences and matching runs for the metrics page."""
        dataset_root = self.path_config.resolve_dataset_dir(dataset.value)
        sequence_slugs = list_sequence_slugs(dataset, dataset_root)
        if not sequence_slugs:
            return EvaluationSelection(
                dataset=dataset,
                dataset_root=dataset_root,
                artifacts_root=self.path_config.artifacts_dir,
            )
        sequence_slug = preferred_sequence_slug if preferred_sequence_slug in sequence_slugs else sequence_slugs[0]
        runs = self.discover_runs(sequence_slug, dataset=dataset)
        return EvaluationSelection(
            dataset=dataset,
            dataset_root=dataset_root,
            artifacts_root=self.path_config.artifacts_dir,
            sequence_slugs=sequence_slugs,
            sequence_slug=sequence_slug,
            runs=runs,
        )

    def load_run_evaluation(self, run: DiscoveredRun) -> RunTrajectoryEvaluation:
        """Load one run's trajectory evaluation manifest and metric rows."""
        manifest_path = self.manifest_path(run.artifact_root)
        if not manifest_path.exists():
            return RunTrajectoryEvaluation(run=run)
        try:
            manifest = TrajectoryEvaluationManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            metric_rows = self.load_metric_rows(self.metrics_long_path(run.artifact_root))
        except (OSError, ValueError) as exc:
            return RunTrajectoryEvaluation(run=run, load_error=str(exc))
        return RunTrajectoryEvaluation(
            run=run,
            manifest=manifest,
            metric_rows=metric_rows,
            skipped_metric_count=len(manifest.skipped_metrics),
        )

    def load_metric_rows(self, path: Path) -> list[TrajectoryMetricResultRow]:
        """Load the long-form metrics CSV emitted by the trajectory evaluator."""
        if not path.exists():
            return []
        return metric_frame_to_rows(
            pd.read_csv(path, keep_default_na=False).assign(
                value=lambda df: pd.to_numeric(df["value"]),
                matched_pairs=lambda df: pd.to_numeric(df["matched_pairs"]).astype(int),
                delta=lambda df: pd.to_numeric(df["delta"].replace("", pd.NA), errors="coerce"),
                delta_unit=lambda df: df["delta_unit"].replace("", None),
                error_series_path=lambda df: df["error_series_path"].map(
                    lambda raw: _resolve_error_series_path(raw, path)
                ),
            )
        )

    @staticmethod
    def manifest_path(run_root: Path) -> Path:
        """Return the canonical trajectory evaluation manifest path for a run."""
        return (run_root / "evaluation" / "trajectory" / "manifest.json").resolve()

    @staticmethod
    def metrics_long_path(run_root: Path) -> Path:
        """Return the canonical long-form trajectory metric table path for a run."""
        return (run_root / "evaluation" / "trajectory" / "metrics_long.csv").resolve()

    @staticmethod
    def load_error_series_values(path: Path) -> np.ndarray:
        """Load metric error values from an `.npz` error-series artifact."""
        with np.load(path) as payload:
            return np.asarray(payload["values"], dtype=np.float64)


def dense_cloud_metric_rows(
    artifact: DenseCloudEvaluationArtifact,
    *,
    context: dict[str, str | int | float] | None = None,
) -> list[EvaluationMetricRow]:
    """Return long-form rows for one dense-cloud evaluation artifact."""
    rows: list[EvaluationMetricRow] = []
    row_context = context or {}
    for estimate in artifact.estimates:
        for metric_id, value in estimate.metrics.items():
            rows.append(
                EvaluationMetricRow(
                    evaluation_kind="point_cloud",
                    metric_id=metric_id.value,
                    value=value,
                    unit=_cloud_metric_unit(metric_id),
                    source_artifact_path=artifact.path,
                    reference_artifact_path=artifact.reference_cloud_path,
                    estimate_artifact_path=estimate.estimate_cloud_path,
                    estimate_kind=estimate.estimate_kind.value,
                    threshold_m=artifact.f1_threshold_m if metric_id is CloudMetricId.F1 else None,
                    context=row_context,
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
                    context=row_context,
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
                    context=row_context,
                ),
            ]
        )
    return rows


def _matches_dataset(sequence_manifest: SequenceManifest | None, dataset: DatasetId) -> bool:
    """Return True when the manifest's dataset_id matches or is absent."""
    return sequence_manifest is not None and (
        sequence_manifest.dataset_id is None or sequence_manifest.dataset_id == dataset
    )


def _resolve_error_series_path(raw: str | None, csv_path: Path) -> Path | None:
    """Resolve an error-series path stored in a metrics CSV row."""
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        return (csv_path.parent / p).resolve()
    if p.exists():
        return p
    return (csv_path.parent / "error_series" / p.name).resolve()


def _sim3_alignment_skip_count(manifest: TrajectoryEvaluationManifest | None) -> int:
    if manifest is None:
        return 0
    return sum(1 for record in manifest.skipped_metrics if "Sim(3) alignment" in record.reason)


def _load_run_sequence_manifest(run_root: Path) -> SequenceManifest | None:
    manifest_path = run_root / "input" / "sequence_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return SequenceManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _matches_selection(
    sequence_manifest: SequenceManifest | None,
    sequence_slug: str,
    dataset: DatasetId | None,
) -> bool:
    if sequence_manifest is None or sequence_manifest.sequence_id != sequence_slug:
        return False
    return dataset is None or sequence_manifest.dataset_id is None or sequence_manifest.dataset_id == dataset


def _cloud_metric_unit(metric_id: CloudMetricId) -> str:
    if metric_id in {CloudMetricId.ACCURACY, CloudMetricId.COMPLETENESS, CloudMetricId.CHAMFER, CloudMetricId.ICP_RMSE}:
        return "m"
    if metric_id in {CloudMetricId.F1, CloudMetricId.ICP_FITNESS}:
        return "ratio"
    return ""


__all__ = [
    "DatasetEvaluationSelection",
    "DatasetRunCoverage",
    "EvaluationMetricRow",
    "EvaluationSelection",
    "RunTrajectoryEvaluation",
    "TrajectoryEvaluationQueryService",
    "dense_cloud_metric_rows",
]
