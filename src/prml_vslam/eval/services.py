from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from evo.core import metrics, sync
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.datasets.contracts import DatasetId
from prml_vslam.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.eval.contracts import (
    DiscoveredRun,
    EvaluationArtifact,
    EvaluationSelection,
    MetricStats,
    SelectionSnapshot,
    TrajectorySeries,
)
from prml_vslam.eval.protocols import TrajectoryEvaluator
from prml_vslam.methods.contracts import MethodId
from prml_vslam.utils.geometry import load_tum_trajectory
from prml_vslam.utils.path_config import PathConfig

__all__ = ["TrajectoryEvaluationService"]

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
            run
            for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum"))
            if (
                run := _discover_run(
                    trajectory_path=trajectory_path,
                    artifacts_dir=self.path_config.artifacts_dir,
                    sequence_slug=sequence_slug,
                )
            )
            is not None
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
        reference_series, _ = _load_trajectory_input(reference_path, "Reference")
        estimate_series, _ = _load_trajectory_input(selection.run.estimate_path, "Estimate")
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

        reference_series, reference_trajectory = _load_trajectory_input(reference_path, "Reference")
        estimate_series, estimate_trajectory = _load_trajectory_input(selection.run.estimate_path, "Estimate")
        trajectories = (reference_series, estimate_series)
        try:
            associated_reference, associated_estimate = sync.associate_trajectories(
                reference_trajectory,
                estimate_trajectory,
                max_diff=_EVO_ASSOCIATION_MAX_DIFF_S,
            )
        except sync.SyncException as exc:
            raise ValueError(
                "No matching trajectory timestamps were found for evo APE "
                f"(max_diff={_EVO_ASSOCIATION_MAX_DIFF_S:.3f}s)."
            ) from exc

        metric = metrics.APE(metrics.PoseRelation.translation_part)
        metric.process_data((associated_reference, associated_estimate))
        error_values = np.asarray(metric.error, dtype=np.float64)
        matched_pairs = int(error_values.size)
        if matched_pairs == 0:
            raise ValueError("evo APE produced zero matched trajectory pairs.")

        result_path = self.result_path(selection.run.artifact_root)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        stats = MetricStats.from_error_values(error_values)
        payload = {
            "title": "Trajectory APE (evo)",
            "matched_pairs": matched_pairs,
            "stats": stats.model_dump(mode="python"),
            "error_timestamps_s": associated_reference.timestamps.tolist(),
            "error_values": error_values.tolist(),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return EvaluationArtifact.from_payload(
            path=result_path,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=trajectories,
        )

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic persisted trajectory-metrics path for the controls."""
        return run_root / "evaluation" / "trajectory_metrics.json"


def _load_trajectory_input(path: Path, name: str) -> tuple[TrajectorySeries, PoseTrajectory3D]:
    """Load one TUM trajectory as both plotting series and evo-native trajectory."""
    trajectory = load_tum_trajectory(path)
    return (
        TrajectorySeries(
            name=name,
            timestamps_s=np.asarray(trajectory.timestamps, dtype=np.float64),
            positions_xyz=trajectory.positions_xyz,
        ),
        trajectory,
    )


def _discover_run(*, trajectory_path: Path, artifacts_dir: Path, sequence_slug: str) -> DiscoveredRun | None:
    run_root = trajectory_path.parent.parent
    relative_parts = run_root.relative_to(artifacts_dir).parts
    if sequence_slug not in relative_parts and sequence_slug not in run_root.name:
        return None

    method = next(
        (method for part in reversed(relative_parts) for method in MethodId if part == method.value),
        None,
    )
    hidden_tokens = {sequence_slug, "slam"} | ({method.value} if method is not None else set())
    visible_parts = [part for part in relative_parts if part not in hidden_tokens]
    label = method.display_name if method is not None else relative_parts[-1]
    return DiscoveredRun(
        artifact_root=run_root,
        estimate_path=trajectory_path,
        method=method,
        label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
    )
