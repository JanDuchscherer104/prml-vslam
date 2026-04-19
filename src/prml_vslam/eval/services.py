from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.eval.contracts import (
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationSelection,
    MetricStats,
    SelectionSnapshot,
    TrajectoryAlignmentMode,
    TrajectoryEvaluationPreview,
    TrajectoryEvaluationSemantics,
    TrajectoryMetricId,
    TrajectorySeries,
)
from prml_vslam.eval.protocols import TrajectoryEvaluator
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.utils.path_config import PathConfig

__all__ = ["TrajectoryEvaluationService", "compute_trajectory_ape_preview"]

_EVO_ASSOCIATION_MAX_DIFF_S = 0.01


class TrajectoryEvaluationService(TrajectoryEvaluator):
    """Discover runs and persist explicit `evo` trajectory metrics."""

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
                method=method,
                label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
            )
            for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum"))
            if sequence_slug
            in (
                relative_parts := (run_root := trajectory_path.parent.parent)
                .relative_to(self.path_config.artifacts_dir)
                .parts
            )
            or sequence_slug in run_root.name
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
        preferred_run_root: Path | None,
    ) -> EvaluationSelection:
        """Resolve dataset sequences, runs, and the current metrics-page selection."""
        dataset_root = self.path_config.resolve_dataset_dir(dataset.value)
        artifacts_root = self.path_config.artifacts_dir
        sequence_slugs = list_sequence_slugs(dataset, dataset_root)
        if not sequence_slugs:
            return EvaluationSelection(
                dataset=dataset,
                dataset_root=dataset_root,
                artifacts_root=artifacts_root,
            )

        sequence_slug = preferred_sequence_slug if preferred_sequence_slug in sequence_slugs else sequence_slugs[0]
        runs = self.discover_runs(sequence_slug)
        if not runs:
            return EvaluationSelection(
                dataset=dataset,
                dataset_root=dataset_root,
                artifacts_root=artifacts_root,
                sequence_slugs=sequence_slugs,
                sequence_slug=sequence_slug,
                runs=runs,
            )

        run = next((candidate for candidate in runs if candidate.artifact_root == preferred_run_root), runs[0])
        return EvaluationSelection(
            dataset=dataset,
            dataset_root=dataset_root,
            artifacts_root=artifacts_root,
            sequence_slugs=sequence_slugs,
            sequence_slug=sequence_slug,
            runs=runs,
            selection=SelectionSnapshot(
                sequence_slug=sequence_slug,
                reference_path=resolve_reference_path(dataset, dataset_root, sequence_slug),
                run=run,
            ),
        )

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
    ) -> EvaluationArtifact | None:
        """Load a persisted `evo` evaluation when it exists."""
        reference_path = selection.reference_path
        result_path = self.result_path(selection.run.artifact_root)
        if reference_path is None or not result_path.exists():
            return None
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        reference_series = _series_from_trajectory("Reference", load_tum_trajectory(reference_path))
        estimate_series = _series_from_trajectory("Estimate", load_tum_trajectory(selection.run.estimate_path))
        trajectories = (reference_series, estimate_series)
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=trajectories,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
    ) -> EvaluationArtifact:
        """Compute and persist trajectory APE via the `evo` Python API."""
        reference_path = selection.reference_path
        if reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        preview = compute_trajectory_ape_preview(
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
        )
        result_path = self.result_path(selection.run.artifact_root)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "title": "Trajectory APE (evo)",
            "matched_pairs": len(preview.error_series.values),
            "stats": preview.stats.model_dump(mode="python"),
            "error_timestamps_s": preview.error_series.timestamps_s.tolist(),
            "error_values": preview.error_series.values.tolist(),
            "semantics": TrajectoryEvaluationSemantics(
                metric_id=TrajectoryMetricId.APE_TRANSLATION,
                pose_relation="translation_part",
                alignment_mode=TrajectoryAlignmentMode.TIMESTAMP_ASSOCIATED_ONLY,
                sync_max_diff_s=_EVO_ASSOCIATION_MAX_DIFF_S,
            ).model_dump(mode="python"),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=(preview.reference, preview.estimate),
        )

    def compute_pipeline_evaluation(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        sequence_manifest: SequenceManifest | None,
        benchmark_inputs: PreparedBenchmarkInputs | None,
        slam: SlamArtifacts | None,
    ) -> EvaluationArtifact | None:
        """Compute the trajectory-evaluation stage for one pipeline run."""
        if not request.benchmark.trajectory.enabled:
            return None
        if sequence_manifest is None or benchmark_inputs is None or slam is None:
            raise RuntimeError(
                "Trajectory evaluation requires a sequence manifest, benchmark inputs, and SLAM artifacts."
            )
        reference = benchmark_inputs.trajectory_for_source(request.benchmark.trajectory.baseline_source)
        if reference is None:
            raise RuntimeError(
                "Prepared benchmark inputs do not include the requested trajectory baseline "
                f"'{request.benchmark.trajectory.baseline_source.value}'."
            )
        return self.compute_evaluation(
            selection=SelectionSnapshot(
                sequence_slug=sequence_manifest.sequence_id,
                reference_path=reference.path,
                run=DiscoveredRun(
                    artifact_root=plan.artifact_root,
                    estimate_path=slam.trajectory_tum.path,
                    method=MethodId(request.slam.backend.kind),
                    label=MethodId(request.slam.backend.kind).display_name,
                ),
            )
        )

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic persisted trajectory-metrics path for the controls."""
        return run_root / "evaluation" / "trajectory_metrics.json"


def compute_trajectory_ape_preview(
    *,
    reference_path: Path,
    estimate_path: Path,
    max_diff_s: float = _EVO_ASSOCIATION_MAX_DIFF_S,
) -> TrajectoryEvaluationPreview:
    """Compute in-memory translation APE for two TUM trajectory artifacts."""
    reference_trajectory = load_tum_trajectory(reference_path)
    estimate_trajectory = load_tum_trajectory(estimate_path)
    try:
        associated_reference, associated_estimate = sync.associate_trajectories(
            reference_trajectory,
            estimate_trajectory,
            max_diff=max_diff_s,
        )
    except sync.SyncException as exc:
        raise ValueError(
            f"No matching trajectory timestamps were found for evo APE (max_diff={max_diff_s:.3f}s)."
        ) from exc

    metric = metrics.APE(metrics.PoseRelation.translation_part)
    metric.process_data((associated_reference, associated_estimate))
    error_values = np.asarray(metric.error, dtype=np.float64)
    if error_values.size == 0:
        raise ValueError("evo APE produced zero matched trajectory pairs.")
    return TrajectoryEvaluationPreview(
        reference=_series_from_trajectory("Reference", associated_reference),
        estimate=_series_from_trajectory("Estimate", associated_estimate),
        error_series=ErrorSeries(
            timestamps_s=np.asarray(associated_reference.timestamps, dtype=np.float64),
            values=error_values,
        ),
        stats=MetricStats.from_error_values(error_values),
    )


def _series_from_trajectory(name: str, trajectory: PoseTrajectory3D) -> TrajectorySeries:
    return TrajectorySeries(
        name=name,
        timestamps_s=np.asarray(trajectory.timestamps, dtype=np.float64),
        positions_xyz=np.asarray(trajectory.positions_xyz, dtype=np.float64),
    )
