"""Post-run trajectory evaluation discovery and aggregation helpers.

This module is the read-only counterpart to the metric computation service. It
discovers runs, loads persisted trajectory evaluation manifests, and prepares
rows for app review without invoking evo or mutating run artifacts.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from pydantic import Field

from prml_vslam.eval.trajectory_contracts import (
    DiscoveredRun,
    TrajectoryEvaluationManifest,
    TrajectoryMetricResultRow,
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
    """Run identifier derived from the artifact root name."""

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
                    run_id=run.artifact_root.name,
                    artifact_root=run.artifact_root,
                    method=run.method,
                    manifest_present=evaluation.manifest is not None,
                    metric_row_count=len(evaluation.metric_rows),
                    matched_pairs=sum(r.matched_pairs for r in evaluation.metric_rows),
                    load_error=evaluation.load_error,
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
        return RunTrajectoryEvaluation(run=run, manifest=manifest, metric_rows=metric_rows)

    def load_metric_rows(self, path: Path) -> list[TrajectoryMetricResultRow]:
        """Load the long-form metrics CSV emitted by the trajectory evaluator."""
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [
                TrajectoryMetricResultRow.model_validate(
                    {
                        **row,
                        "value": float(row["value"]),
                        "matched_pairs": int(row["matched_pairs"]),
                        "delta": _optional_float(row.get("delta")),
                        "delta_unit": row.get("delta_unit") or None,
                        "error_series_path": _resolve_error_series_path(row.get("error_series_path"), path),
                    }
                )
                for row in csv.DictReader(handle)
            ]

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


def _matches_dataset(sequence_manifest: SequenceManifest | None, dataset: DatasetId) -> bool:
    """Return True when the manifest's dataset_id matches or is absent."""
    return sequence_manifest is not None and (
        sequence_manifest.dataset_id is None or sequence_manifest.dataset_id == dataset
    )


def _resolve_error_series_path(raw: str | None, csv_path: Path) -> Path | None:
    """Resolve an error-series path stored in a metrics CSV row.

    Handles three cases:
    - Empty / missing: returns None.
    - Relative path (new portable format): resolved relative to the CSV's directory.
    - Absolute path from another machine: remapped to the local ``error_series/`` sibling
      directory when the original absolute path does not exist.
    """
    if not raw:
        return None
    p = Path(raw)
    if not p.is_absolute():
        return (csv_path.parent / p).resolve()
    if p.exists():
        return p
    # Legacy absolute path written on a different machine — remap to local error_series dir.
    return (csv_path.parent / "error_series" / p.name).resolve()


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


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


__all__ = [
    "DatasetEvaluationSelection",
    "DatasetRunCoverage",
    "EvaluationSelection",
    "RunTrajectoryEvaluation",
    "TrajectoryEvaluationQueryService",
]
