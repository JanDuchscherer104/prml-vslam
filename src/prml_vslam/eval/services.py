"""Mock trajectory evaluation services for the app and tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from prml_vslam.datasets.interfaces import DatasetId
from prml_vslam.eval.interfaces import (
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationControls,
    MetricStats,
    SelectionSnapshot,
    TrajectorySeries,
)
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils.path_config import PathConfig


class TrajectoryEvaluationService:
    """Discover runs and persist a lightweight local trajectory-delta mock."""

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def dataset_root(self, dataset: DatasetId) -> Path:
        """Return the repo-owned root for the selected dataset."""
        match dataset:
            case DatasetId.ADVIO:
                return self.path_config.resolve_dataset_dir(dataset.value)
            case _:
                raise NotImplementedError(f"Unsupported dataset: {dataset!r}")

    def list_sequences(self, dataset: DatasetId) -> list[str]:
        """List locally available sequence slugs for the selected dataset."""
        root = self.dataset_root(dataset)
        sequence_names = {
            path.name
            for candidate_root in (root, root / "data")
            if candidate_root.exists()
            for path in candidate_root.iterdir()
            if path.is_dir() and path.name.startswith(f"{dataset.value}-")
        }
        return sorted(sequence_names)

    def discover_runs(self, dataset: DatasetId, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root that match `sequence_slug`."""
        del dataset
        if sequence_slug is None:
            return []

        runs: list[DiscoveredRun] = []
        for trajectory_path in sorted(self.path_config.artifacts_dir.glob("**/slam/trajectory.tum")):
            run_root = trajectory_path.parent.parent
            relative_parts = run_root.relative_to(self.path_config.artifacts_dir).parts
            if sequence_slug not in relative_parts and sequence_slug not in run_root.name:
                continue
            method = self._infer_method(relative_parts)
            runs.append(
                DiscoveredRun(
                    artifact_root=run_root,
                    estimate_path=trajectory_path,
                    method=method,
                    label=self._format_run_label(sequence_slug, relative_parts, method),
                )
            )
        return runs

    def resolve_selection(
        self,
        *,
        dataset: DatasetId,
        sequence_slug: str | None,
        run_root: Path | None,
    ) -> SelectionSnapshot | None:
        """Resolve the current selector state into concrete dataset and run paths."""
        if sequence_slug is None:
            return None
        runs = self.discover_runs(dataset, sequence_slug)
        if not runs:
            return None
        selected_run = next((run for run in runs if run.artifact_root == run_root), runs[0])
        return SelectionSnapshot(
            dataset=dataset,
            sequence_slug=sequence_slug,
            dataset_root=self.dataset_root(dataset),
            reference_path=self.reference_path(dataset=dataset, sequence_slug=sequence_slug),
            run=selected_run,
        )

    def reference_path(self, *, dataset: DatasetId, sequence_slug: str) -> Path | None:
        """Return the local TUM reference trajectory when it already exists."""
        sequence_root = self.dataset_root(dataset) / sequence_slug
        for candidate in (
            sequence_root / "ground-truth" / "ground_truth.tum",
            sequence_root / "ground_truth.tum",
            sequence_root / "evaluation" / "ground_truth.tum",
        ):
            if candidate.exists():
                return candidate
        return None

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact | None:
        """Load a persisted local mock evaluation when it exists."""
        result_path = self.result_path(selection.run.artifact_root, controls)
        if not result_path.exists() or selection.reference_path is None:
            return None
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        return self._build_evaluation_artifact(
            result_path=result_path,
            selection=selection,
            controls=controls,
            payload=payload,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact:
        """Compute and persist a simple local trajectory-delta mock."""
        if selection.reference_path is None:
            raise FileNotFoundError("The selected dataset slice is missing a TUM reference trajectory.")

        reference_timestamps_s, reference_positions_xyz = _load_tum_trajectory(selection.reference_path)
        estimate_timestamps_s, estimate_positions_xyz = _load_tum_trajectory(selection.run.estimate_path)
        matched_pairs = min(len(reference_timestamps_s), len(estimate_timestamps_s))
        if matched_pairs == 0:
            raise ValueError("Mock evaluation requires at least one trajectory row in both files.")

        error_values = np.linalg.norm(
            estimate_positions_xyz[:matched_pairs] - reference_positions_xyz[:matched_pairs],
            axis=1,
        )
        result_path = self.result_path(selection.run.artifact_root, controls)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "title": "Mock Trajectory Error",
            "matched_pairs": matched_pairs,
            "stats": _stats_payload(error_values),
            "error_timestamps_s": reference_timestamps_s[:matched_pairs].tolist(),
            "error_values": error_values.tolist(),
        }
        result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self._build_evaluation_artifact(
            result_path=result_path,
            selection=selection,
            controls=controls,
            payload=payload,
        )

    @staticmethod
    def result_path(run_root: Path, controls: EvaluationControls) -> Path:
        """Return the deterministic persisted mock-result path for the controls."""
        align_flag = "align" if controls.align else "no-align"
        scale_flag = "scale" if controls.correct_scale else "no-scale"
        diff_token = str(controls.max_diff_s).replace(".", "p")
        filename = f"mock_metrics__{controls.pose_relation.value}__{align_flag}__{scale_flag}__diff-{diff_token}.json"
        return run_root / "evaluation" / filename

    @staticmethod
    def _infer_method(relative_parts: tuple[str, ...]) -> MethodId | None:
        for part in reversed(relative_parts):
            for method in MethodId:
                if part == method.artifact_slug:
                    return method
        return None

    @staticmethod
    def _format_run_label(
        sequence_slug: str,
        relative_parts: tuple[str, ...],
        method: MethodId | None,
    ) -> str:
        hidden_tokens = {sequence_slug, "slam"}
        if method is not None:
            hidden_tokens.add(method.artifact_slug)
        visible_parts = [part for part in relative_parts if part not in hidden_tokens]
        method_label = method.display_name if method is not None else relative_parts[-1]
        return method_label if not visible_parts else f"{method_label} · {' / '.join(visible_parts)}"

    @staticmethod
    def _build_evaluation_artifact(
        *,
        result_path: Path,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
        payload: dict[str, object],
    ) -> EvaluationArtifact:
        reference_timestamps_s, reference_positions_xyz = _load_tum_trajectory(selection.reference_path or Path())
        estimate_timestamps_s, estimate_positions_xyz = _load_tum_trajectory(selection.run.estimate_path)
        return EvaluationArtifact(
            path=result_path,
            controls=controls,
            title=str(payload["title"]),
            matched_pairs=int(payload["matched_pairs"]),
            stats=MetricStats.model_validate(payload["stats"]),
            reference_path=selection.reference_path or Path(),
            estimate_path=selection.run.estimate_path,
            trajectories=[
                TrajectorySeries(
                    name="Reference",
                    positions_xyz=reference_positions_xyz,
                    timestamps_s=reference_timestamps_s,
                ),
                TrajectorySeries(
                    name="Estimate",
                    positions_xyz=estimate_positions_xyz,
                    timestamps_s=estimate_timestamps_s,
                ),
            ],
            error_series=ErrorSeries(
                timestamps_s=np.asarray(payload["error_timestamps_s"], dtype=np.float64),
                values=np.asarray(payload["error_values"], dtype=np.float64),
            ),
        )


def _load_tum_trajectory(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load timestamps and XYZ positions from a TUM trajectory file."""
    rows = [
        [float(value) for value in line.split()]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not rows:
        return np.empty(0, dtype=np.float64), np.empty((0, 3), dtype=np.float64)
    data = np.asarray(rows, dtype=np.float64)
    return data[:, 0], data[:, 1:4]


def _stats_payload(error_values: np.ndarray) -> dict[str, float]:
    """Return the persisted scalar summary for one mock trajectory comparison."""
    squared = np.square(error_values)
    return {
        "rmse": float(np.sqrt(np.mean(squared))),
        "mean": float(np.mean(error_values)),
        "median": float(np.median(error_values)),
        "std": float(np.std(error_values)),
        "min": float(np.min(error_values)),
        "max": float(np.max(error_values)),
        "sse": float(np.sum(squared)),
    }


__all__ = ["TrajectoryEvaluationService"]
