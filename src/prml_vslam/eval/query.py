"""Post-run trajectory evaluation discovery and aggregation helpers.

This module is the primary counterpart to the metric computation service for
discovery and loading. Most of its surface is read-only: it discovers runs,
loads persisted trajectory evaluation manifests, and prepares rows for app
review. The exception is :meth:`TrajectoryEvaluationQueryService.recompute_run_evaluation`,
which explicitly invokes evo metric computation and overwrites persisted artifacts.
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from pydantic import Field

from prml_vslam.eval.trajectory_contracts import (
    DiscoveredRun,
    SelectionSnapshot,
    TrajectoryEvaluationManifest,
    TrajectoryMetricResultRow,
)
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
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

    skipped_metric_count: int = 0
    """Number of non-primary metrics that were attempted but skipped during evaluation."""


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


class TrajectoryEvaluationQueryService:
    """Post-run query service for trajectory evaluation artifacts.

    All methods except :meth:`recompute_run_evaluation` are read-only.
    """

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
                    skipped_metric_count=evaluation.skipped_metric_count,
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

    def recompute_run_evaluation(self, run: DiscoveredRun) -> TrajectoryEvaluationManifest:
        """Recompute and persist trajectory metrics for one discovered run from its artifact data.

        **This method is mutating**: it invokes evo APE/RPE computation and overwrites
        ``evaluation/trajectory/manifest.json`` and ``evaluation/trajectory/metrics_long.csv``
        under the run's artifact root. It is not safe to call concurrently on the same run.

        Reads ``benchmark/inputs.json`` for reference and candidate trajectories, remapping
        absolute paths written on other machines to the local artifact root. Falls back to
        ``benchmark/ground_truth.tum`` when no inputs file is present.
        """
        from prml_vslam.eval.services import TrajectoryEvaluationService

        sequence_manifest = _load_run_sequence_manifest(run.artifact_root)
        sequence_slug = sequence_manifest.sequence_id if sequence_manifest else run.artifact_root.name
        dataset_id = sequence_manifest.dataset_id if sequence_manifest else None

        benchmark_inputs = _load_benchmark_inputs(run.artifact_root)
        reference: ReferenceTrajectoryRef | None = None
        candidate_trajectories: list[ReferenceTrajectoryRef] | None = None

        if benchmark_inputs is not None:
            raw_ref = benchmark_inputs.trajectory_for_source(ReferenceSource.GROUND_TRUTH)
            if raw_ref is not None:
                reference = _remap_reference(raw_ref, run.artifact_root)
            candidate_trajectories = [
                _remap_reference(c, run.artifact_root) for c in benchmark_inputs.candidate_trajectories
            ]

        if reference is None:
            gt_path = run.artifact_root / "benchmark" / "ground_truth.tum"
            if not gt_path.exists():
                raise FileNotFoundError(f"No reference trajectory found for run at {run.artifact_root}")
            reference = ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=gt_path)

        selection = SelectionSnapshot(
            sequence_slug=sequence_slug,
            reference_path=reference.path,
            target_frame=reference.target_frame or _infer_target_frame_for_dataset(dataset_id),
            coordinate_status=reference.coordinate_status.value
            if reference.coordinate_status
            else _infer_coord_status_for_dataset(dataset_id),
            reference_source=reference.source.value,
            run=run,
        )
        return TrajectoryEvaluationService(path_config=self.path_config).compute_evaluation(
            selection=selection,
            candidate_trajectories=candidate_trajectories,
        )

    @staticmethod
    def load_error_series_values(path: Path) -> np.ndarray:
        """Load metric error values from an `.npz` error-series artifact."""
        with np.load(path) as payload:
            return np.asarray(payload["values"], dtype=np.float64)


def _load_benchmark_inputs(artifact_root: Path) -> PreparedBenchmarkInputs | None:
    inputs_path = artifact_root / "benchmark" / "inputs.json"
    if not inputs_path.exists():
        return None
    try:
        return PreparedBenchmarkInputs.model_validate_json(inputs_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not load benchmark inputs from '{inputs_path}': {exc}") from exc


def _remap_reference(ref: ReferenceTrajectoryRef, local_artifact_root: Path) -> ReferenceTrajectoryRef:
    path = _remap_artifact_path(ref.path, local_artifact_root)
    metadata_path = _remap_artifact_path(ref.metadata_path, local_artifact_root) if ref.metadata_path else None
    return ref.model_copy(update={"path": path, "metadata_path": metadata_path})


def _remap_artifact_path(path: Path, local_artifact_root: Path) -> Path:
    """Remap an absolute path written on another machine to the local artifact root."""
    if path.exists():
        return path
    for marker in ("benchmark", "slam", "evaluation", "input"):
        parts = path.parts
        for i, part in enumerate(parts):
            if part == marker:
                candidate = local_artifact_root / Path(*parts[i:])
                if candidate.exists():
                    return candidate
    return path


def _infer_target_frame_for_dataset(dataset_id: DatasetId | None) -> str:
    if dataset_id is DatasetId.ADVIO:
        return "advio_gt_world"
    if dataset_id is DatasetId.TUM_RGBD:
        return "tum_rgbd_world"
    return "world"


def _infer_coord_status_for_dataset(dataset_id: DatasetId | None) -> str:
    if dataset_id is DatasetId.ADVIO:
        return "aligned"
    return "source_native"


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
