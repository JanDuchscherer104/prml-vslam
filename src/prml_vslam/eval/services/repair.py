"""Explicit repair service for regenerating trajectory evaluation artifacts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.eval.services.trajectory_evaluation import TrajectoryEvaluationService
from prml_vslam.eval.trajectory_contracts import (
    DiscoveredRun,
    SelectionSnapshot,
    TrajectoryEvaluationManifest,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.utils.path_config import PathConfig


class TrajectoryEvaluationRepairService:
    """Mutating service for rebuilding persisted trajectory evaluation artifacts."""

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def recompute_run_evaluation(
        self,
        run: DiscoveredRun,
        *,
        baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH,
        sequence_slug: str | None = None,
    ) -> TrajectoryEvaluationManifest:
        """Recompute and persist trajectory metrics for one discovered run.

        This method overwrites ``evaluation/trajectory/manifest.json``,
        ``metrics_long.csv``, and error-series artifacts under the run root.
        It is intentionally separate from the read-only query service.
        """
        sequence_manifest = _load_run_sequence_manifest(run.artifact_root)
        resolved_sequence_slug = (
            sequence_slug
            if sequence_slug is not None
            else sequence_manifest.sequence_id
            if sequence_manifest
            else run.artifact_root.name
        )
        dataset_id = sequence_manifest.dataset_id if sequence_manifest else None

        benchmark_inputs = _load_benchmark_inputs(run.artifact_root)
        reference: ReferenceTrajectoryRef | None = None
        candidate_trajectories: list[ReferenceTrajectoryRef] | None = None

        if benchmark_inputs is not None:
            raw_ref = benchmark_inputs.trajectory_for_source(baseline_source)
            if raw_ref is not None:
                reference = _remap_reference(raw_ref, run.artifact_root)
            candidate_trajectories = [
                _remap_reference(candidate, run.artifact_root) for candidate in benchmark_inputs.candidate_trajectories
            ]

        if reference is None:
            reference_path = run.artifact_root / "benchmark" / _reference_trajectory_filename(baseline_source)
            if not reference_path.exists():
                raise FileNotFoundError(f"No reference trajectory found for run at {run.artifact_root}")
            reference = ReferenceTrajectoryRef(source=baseline_source, path=reference_path)

        selection = SelectionSnapshot(
            sequence_slug=resolved_sequence_slug,
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
        for index, part in enumerate(parts):
            if part == marker:
                candidate = local_artifact_root / Path(*parts[index:])
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


def _reference_trajectory_filename(source: ReferenceSource) -> str:
    return "ground_truth.tum" if source is ReferenceSource.GROUND_TRUTH else f"{source.value}.tum"


def _load_run_sequence_manifest(run_root: Path) -> SequenceManifest | None:
    manifest_path = run_root / "input" / "sequence_manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return SequenceManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


__all__ = ["TrajectoryEvaluationRepairService"]
