"""Reusable discovery and `evo` evaluation services for the metrics app."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from prml_vslam.pipeline.contracts import MethodId
from prml_vslam.utils.path_config import PathConfig

from .models import (
    DatasetId,
    DiscoveredRun,
    ErrorSeries,
    EvaluationArtifact,
    EvaluationControls,
    MetricStats,
    PoseRelationId,
    SelectionSnapshot,
    TrajectorySeries,
)


class MetricsAppService:
    """Discover benchmark artifacts and evaluate trajectory pairs with `evo`."""

    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config

    def dataset_root(self, dataset: DatasetId) -> Path:
        """Return the repo-owned root for the selected dataset."""
        match dataset:
            case DatasetId.ADVIO:
                return self.path_config.resolve_repo_path("data/advio")
            case _:
                raise NotImplementedError(f"Unsupported dataset: {dataset!r}")

    def list_sequences(self, dataset: DatasetId) -> list[str]:
        """List locally available sequence slugs for the selected dataset."""
        root = self.dataset_root(dataset)
        if not root.exists():
            return []
        return sorted(
            path.name for path in root.iterdir() if path.is_dir() and path.name.startswith(f"{dataset.value}-")
        )

    def discover_runs(self, dataset: DatasetId, sequence_slug: str | None) -> list[DiscoveredRun]:
        """Return all runs under the artifacts root that match `sequence_slug`."""
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
                    label=self._format_run_label(
                        sequence_slug=sequence_slug, relative_parts=relative_parts, method=method
                    ),
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
        """Return the repo-owned TUM reference trajectory for the selection when present."""
        sequence_root = self.dataset_root(dataset) / sequence_slug
        candidates = (
            sequence_root / "ground-truth" / "ground_truth.tum",
            sequence_root / "ground_truth.tum",
            sequence_root / "evaluation" / "ground_truth.tum",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact | None:
        """Load the persisted native `evo` result for the selected controls when present."""
        _, _, file_interface, _ = _load_evo_modules()
        result_path = self.result_path(selection.run.artifact_root, controls)
        if not result_path.exists() or selection.reference_path is None:
            return None
        result = file_interface.load_res_file(result_path, load_trajectories=True)
        return self._build_evaluation_artifact(
            result_path=result_path,
            selection=selection,
            controls=controls,
            info=result.info,
            stats=result.stats,
            np_arrays=result.np_arrays,
            trajectories=result.trajectories,
        )

    def compute_evaluation(
        self,
        *,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
    ) -> EvaluationArtifact:
        """Compute APE explicitly with `evo`, persist it, and return the loaded result."""
        ape, sync, file_interface, _ = _load_evo_modules()
        if selection.reference_path is None:
            msg = "The selected dataset slice is missing a TUM reference trajectory."
            raise FileNotFoundError(msg)
        reference = file_interface.read_tum_trajectory_file(selection.reference_path)
        estimate = file_interface.read_tum_trajectory_file(selection.run.estimate_path)
        associated_ref, associated_est = sync.associate_trajectories(
            reference,
            estimate,
            max_diff=controls.max_diff_s,
        )
        result = ape(
            associated_ref,
            associated_est,
            self._to_evo_pose_relation(controls.pose_relation),
            align=controls.align,
            correct_scale=controls.correct_scale,
        )
        result_path = self.result_path(selection.run.artifact_root, controls)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        file_interface.save_res_file(result_path, result, confirm_overwrite=False)
        loaded = self.load_evaluation(selection=selection, controls=controls)
        if loaded is None:
            msg = f"Expected persisted evo result at '{result_path}', but it could not be loaded."
            raise FileNotFoundError(msg)
        return loaded

    @staticmethod
    def result_path(run_root: Path, controls: EvaluationControls) -> Path:
        """Return the deterministic persisted `evo` result path for the controls."""
        align_flag = "align" if controls.align else "no-align"
        scale_flag = "scale" if controls.correct_scale else "no-scale"
        diff_token = str(controls.max_diff_s).replace(".", "p")
        filename = f"evo_ape__{controls.pose_relation.value}__{align_flag}__{scale_flag}__diff-{diff_token}.zip"
        return run_root / "evaluation" / filename

    @staticmethod
    def _to_evo_pose_relation(pose_relation: PoseRelationId) -> object:
        _, _, _, pose_relation_enum = _load_evo_modules()
        return {
            PoseRelationId.TRANSLATION_PART: pose_relation_enum.translation_part,
            PoseRelationId.FULL_TRANSFORMATION: pose_relation_enum.full_transformation,
            PoseRelationId.ROTATION_ANGLE_DEG: pose_relation_enum.rotation_angle_deg,
            PoseRelationId.ROTATION_ANGLE_RAD: pose_relation_enum.rotation_angle_rad,
        }[pose_relation]

    @staticmethod
    def _infer_method(relative_parts: tuple[str, ...]) -> MethodId | None:
        for part in reversed(relative_parts):
            if part in MethodId._value2member_map_:
                return MethodId(part)
        return None

    @staticmethod
    def _format_run_label(
        *,
        sequence_slug: str,
        relative_parts: tuple[str, ...],
        method: MethodId | None,
    ) -> str:
        hidden_tokens = {sequence_slug, "slam"}
        if method is not None:
            hidden_tokens.add(method.value)
        visible_parts = [part for part in relative_parts if part not in hidden_tokens]
        method_label = method.value.replace("_", " ").upper() if method is not None else relative_parts[-1]
        if visible_parts:
            return f"{method_label} · {' / '.join(visible_parts)}"
        return method_label

    @staticmethod
    def _build_evaluation_artifact(
        *,
        result_path: Path,
        selection: SelectionSnapshot,
        controls: EvaluationControls,
        info: dict[str, object],
        stats: dict[str, object],
        np_arrays: dict[str, np.ndarray],
        trajectories: dict[str, object],
    ) -> EvaluationArtifact:
        reference_trajectory = trajectories.get("reference")
        estimate_trajectory = trajectories.get("estimate")
        trajectory_series: list[TrajectorySeries] = []
        matched_pairs = 0

        for name, trajectory in (("Reference", reference_trajectory), ("Estimate", estimate_trajectory)):
            if trajectory is None:
                continue
            positions_xyz = np.asarray(trajectory.positions_xyz, dtype=np.float64)
            timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
            matched_pairs = max(matched_pairs, int(len(timestamps_s)))
            trajectory_series.append(
                TrajectorySeries(
                    name=name,
                    positions_xyz=positions_xyz,
                    timestamps_s=timestamps_s,
                )
            )

        error_array = np.asarray(np_arrays.get("error_array", np.array([], dtype=np.float64)), dtype=np.float64)
        timestamp_array = np.asarray(np_arrays.get("timestamps", np.array([], dtype=np.float64)), dtype=np.float64)
        error_series = None
        if error_array.size and timestamp_array.size and error_array.size == timestamp_array.size:
            error_series = ErrorSeries(
                timestamps_s=timestamp_array,
                values=error_array,
            )

        return EvaluationArtifact(
            path=result_path,
            controls=controls,
            title=str(info.get("title", "Absolute Pose Error")),
            matched_pairs=matched_pairs,
            stats=MetricStats(
                rmse=float(stats["rmse"]),
                mean=float(stats["mean"]),
                median=float(stats["median"]),
                std=float(stats["std"]),
                min=float(stats["min"]),
                max=float(stats["max"]),
                sse=float(stats["sse"]),
            ),
            reference_path=selection.reference_path or Path(),
            estimate_path=selection.run.estimate_path,
            trajectories=trajectory_series,
            error_series=error_series,
        )


def _load_evo_modules() -> tuple[object, object, object, object]:
    """Import the small `evo` surface required by the app."""
    try:
        from evo.core import sync  # type: ignore[import-not-found]
        from evo.core.metrics import PoseRelation  # type: ignore[import-not-found]
        from evo.main_ape import ape  # type: ignore[import-not-found]
        from evo.tools import file_interface  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        msg = "The metrics app requires the `eval` extra. Run `uv sync --extra eval` first."
        raise RuntimeError(msg) from exc
    return ape, sync, file_interface, PoseRelation


__all__ = ["MetricsAppService"]
