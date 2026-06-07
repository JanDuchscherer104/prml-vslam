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
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.registry import list_sequence_slugs
from prml_vslam.utils import BaseData, PathConfig


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

    def discover_runs(self, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root that match one sequence slug."""
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
            for relative_parts in [run_root.relative_to(self.path_config.artifacts_dir).parts]
            if any(part == sequence_slug for part in relative_parts)
            for method in [
                next(
                    (method for part in reversed(relative_parts) for method in MethodId if part == method.value),
                    None,
                )
            ]
            for visible_parts in [
                [
                    part
                    for part in relative_parts
                    if part not in ({sequence_slug, "slam"} | ({method.value} if method is not None else set()))
                ]
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
        runs = self.discover_runs(sequence_slug)
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
                        "error_series_path": row.get("error_series_path") or None,
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


def _optional_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


__all__ = [
    "EvaluationSelection",
    "RunTrajectoryEvaluation",
    "TrajectoryEvaluationQueryService",
]
