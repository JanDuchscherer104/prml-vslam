from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prml_vslam.eval.interfaces import DiscoveredRun, EvaluationArtifact, EvaluationControls, SelectionSnapshot
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils.path_config import PathConfig

from . import selection as _selection
from .mock_metrics import build_evaluation_artifact, load_trajectory_pair, stats_payload

# Backwards-compatible re-exports for app code and tests that still import from eval.services.
build_selection = _selection.build_selection
list_sequences = _selection.list_sequences
resolve_dataset_root = _selection.resolve_dataset_root
resolve_reference_path = _selection.resolve_reference_path

__all__ = [
    "TrajectoryEvaluationService",
    "build_selection",
    "list_sequences",
    "resolve_dataset_root",
    "resolve_reference_path",
]


class TrajectoryEvaluationService:
    """Discover runs and persist a lightweight local trajectory-delta mock."""

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

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact | None:
        """Load a persisted local mock evaluation when it exists."""
        reference_path = selection.reference_path
        result_path = self.result_path(selection.run.artifact_root, controls)
        if reference_path is None or not result_path.exists():
            return None
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return build_evaluation_artifact(
            result_path=result_path,
            controls=controls,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact:
        """Compute and persist a simple local trajectory-delta mock."""
        reference_path = selection.reference_path
        if reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        trajectories = load_trajectory_pair(
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
        )
        reference_trajectory, estimate_trajectory = trajectories
        matched_pairs = min(len(reference_trajectory.timestamps_s), len(estimate_trajectory.timestamps_s))
        if matched_pairs == 0:
            raise ValueError("Mock evaluation requires at least one trajectory row in both files.")

        error_values = np.linalg.norm(
            estimate_trajectory.positions_xyz[:matched_pairs] - reference_trajectory.positions_xyz[:matched_pairs],
            axis=1,
        )
        result_path = self.result_path(selection.run.artifact_root, controls)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "title": "Mock Trajectory Error",
            "matched_pairs": matched_pairs,
            "stats": stats_payload(error_values),
            "error_timestamps_s": reference_trajectory.timestamps_s[:matched_pairs].tolist(),
            "error_values": error_values.tolist(),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return build_evaluation_artifact(
            result_path=result_path,
            controls=controls,
            payload=payload,
            reference_path=reference_path,
            estimate_path=selection.run.estimate_path,
            trajectories=trajectories,
        )

    @staticmethod
    def result_path(run_root: Path, controls: EvaluationControls) -> Path:
        """Return the deterministic persisted mock-result path for the controls."""
        diff_token = str(controls.max_diff_s).replace(".", "p")
        align_flag = "align" if controls.align else "no-align"
        scale_flag = "scale" if controls.correct_scale else "no-scale"
        filename = f"mock_metrics__{controls.pose_relation.value}__{align_flag}__{scale_flag}__diff-{diff_token}.json"
        return run_root / "evaluation" / filename


def _discover_run(*, trajectory_path: Path, artifacts_dir: Path, sequence_slug: str) -> DiscoveredRun | None:
    run_root = trajectory_path.parent.parent
    relative_parts = run_root.relative_to(artifacts_dir).parts
    if sequence_slug not in relative_parts and sequence_slug not in run_root.name:
        return None

    method = next(
        (method for part in reversed(relative_parts) for method in MethodId if part == method.artifact_slug),
        None,
    )
    hidden_tokens = {sequence_slug, "slam"} | ({method.artifact_slug} if method is not None else set())
    visible_parts = [part for part in relative_parts if part not in hidden_tokens]
    label = method.display_name if method is not None else relative_parts[-1]
    return DiscoveredRun(
        artifact_root=run_root,
        estimate_path=trajectory_path,
        method=method,
        label=label if not visible_parts else f"{label} · {' / '.join(visible_parts)}",
    )
