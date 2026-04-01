"""Typed discovery and evaluation services for the PRML VSLAM app."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from prml_vslam.datasets import (
    AdvioSequenceConfig,
    AdvioSequenceSummary,
    convert_advio_pose_csv_to_tum,
    list_advio_sequence_ids,
    summarize_advio_sequence,
)
from prml_vslam.eval import (
    TrajectoryEvaluationConfig,
    TrajectoryEvaluationResult,
    evaluate_tum_trajectories,
    write_evaluation_result,
)
from prml_vslam.io import Record3DUSBStatus, probe_record3d_usb_status
from prml_vslam.path_config import PathConfig
from prml_vslam.pipeline.contracts import MethodId, PipelineMode
from prml_vslam.utils import resolve_first_existing

from .models import (
    DatasetId,
    DiscoveredRun,
    EvaluationControls,
    MetricsSelection,
    StoredTrajectoryEvaluation,
    TrajectoryPoint,
)


class EvaluationService:
    """Discover dataset artifacts and manage `evo` trajectory evaluations."""

    def __init__(self, paths: PathConfig) -> None:
        self.paths = paths

    def list_sequences(self, dataset: DatasetId) -> list[int]:
        """Return the locally available sequence ids for ``dataset``."""
        match dataset:
            case DatasetId.ADVIO:
                return list_advio_sequence_ids(self.paths.advio_root)

    def summarize_sequence(self, dataset: DatasetId, sequence_id: int) -> AdvioSequenceSummary:
        """Return a typed summary for one supported dataset sequence."""
        match dataset:
            case DatasetId.ADVIO:
                return summarize_advio_sequence(
                    AdvioSequenceConfig(dataset_root=self.paths.advio_root, sequence_id=sequence_id)
                )

    def discover_runs(self, dataset: DatasetId, sequence_id: int) -> list[DiscoveredRun]:
        """Discover runnable artifact roots for the selected dataset slice."""
        match dataset:
            case DatasetId.ADVIO:
                sequence_name = f"advio-{sequence_id:02d}"
                sequence_root = self.paths.artifacts_root / sequence_name
                if not sequence_root.exists():
                    return []
                runs: list[DiscoveredRun] = []
                for mode_dir in sorted(path for path in sequence_root.iterdir() if path.is_dir()):
                    try:
                        mode = PipelineMode(mode_dir.name)
                    except ValueError:
                        continue
                    for method_dir in sorted(path for path in mode_dir.iterdir() if path.is_dir()):
                        try:
                            method = MethodId(method_dir.name)
                        except ValueError:
                            continue
                        trajectory_path = method_dir / "slam" / "trajectory.tum"
                        if not trajectory_path.exists():
                            continue
                        runs.append(
                            DiscoveredRun(
                                artifact_root=method_dir,
                                sequence_id=sequence_id,
                                mode=mode,
                                method=method,
                                estimate_path=trajectory_path,
                                trajectory_metadata_path=self._optional_path(
                                    method_dir / "slam" / "trajectory.metadata.json"
                                ),
                                evaluations=self._discover_evaluations(method_dir / "evaluation"),
                            )
                        )
                return sorted(runs, key=lambda run: (run.mode.value, run.method.value, run.artifact_root.as_posix()))

    def resolve_metrics_selection(
        self,
        *,
        dataset: DatasetId,
        sequence_id: int | None,
        run_path: Path | None,
    ) -> MetricsSelection | None:
        """Resolve the current metrics-page selection into concrete paths."""
        if sequence_id is None:
            return None

        runs = self.discover_runs(dataset, sequence_id)
        if not runs:
            return None

        resolved_run = None
        if run_path is not None:
            resolved_run = next((run for run in runs if run.artifact_root == run_path), None)
        if resolved_run is None:
            resolved_run = runs[0]

        match dataset:
            case DatasetId.ADVIO:
                config = AdvioSequenceConfig(dataset_root=self.paths.advio_root, sequence_id=sequence_id)
                sequence_dir = config.sequence_dir
                existing_reference = self._optional_path(sequence_dir / "ground-truth" / "ground_truth.tum")
                try:
                    reference_csv_path = resolve_first_existing(
                        sequence_dir / "ground-truth", ("pose.csv", "poses.csv")
                    )
                except FileNotFoundError:
                    reference_csv_path = None
                return MetricsSelection(
                    dataset=dataset,
                    sequence_id=sequence_id,
                    sequence_name=config.sequence_name,
                    run=resolved_run,
                    reference_path=existing_reference,
                    reference_csv_path=reference_csv_path,
                )

    def find_matching_evaluation(
        self,
        *,
        selection: MetricsSelection,
        controls: EvaluationControls,
    ) -> StoredTrajectoryEvaluation | None:
        """Return the persisted evaluation that matches ``controls`` when present."""
        deterministic_path = self._evaluation_output_path(selection.run.artifact_root, controls)
        if deterministic_path.exists():
            document = self._load_evaluation_document(deterministic_path)
            if document is not None:
                return document

        for evaluation in selection.run.evaluations:
            if self._controls_match(evaluation.result, controls):
                return evaluation
        return None

    def list_persisted_evaluations(self, selection: MetricsSelection) -> list[StoredTrajectoryEvaluation]:
        """Return all persisted evaluations for ``selection.run``."""
        return selection.run.evaluations

    def compute_evaluation(
        self,
        *,
        selection: MetricsSelection,
        controls: EvaluationControls,
    ) -> StoredTrajectoryEvaluation:
        """Run `evo` evaluation explicitly and persist the result under the run root."""
        reference_path = self._ensure_reference_path(selection)
        result = evaluate_tum_trajectories(
            TrajectoryEvaluationConfig(
                reference_path=reference_path,
                estimate_path=selection.run.estimate_path,
                pose_relation=controls.pose_relation,
                align=controls.align,
                correct_scale=controls.correct_scale,
                max_diff_s=controls.max_diff_s,
            )
        )
        output_path = self._evaluation_output_path(selection.run.artifact_root, controls)
        write_evaluation_result(result, output_path)
        return StoredTrajectoryEvaluation(path=output_path, result=result)

    def load_trajectory_points(self, path: Path) -> list[TrajectoryPoint]:
        """Parse one TUM trajectory file into typed plot points."""
        points: list[TrajectoryPoint] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            values = stripped.split()
            if len(values) < 8:
                continue
            timestamp_s, tx, ty, tz = map(float, values[:4])
            points.append(TrajectoryPoint(timestamp_s=timestamp_s, x=tx, y=ty, z=tz))
        return points

    @staticmethod
    def _optional_path(path: Path) -> Path | None:
        return path if path.exists() else None

    def _discover_evaluations(self, evaluation_dir: Path) -> list[StoredTrajectoryEvaluation]:
        if not evaluation_dir.exists():
            return []
        documents: list[StoredTrajectoryEvaluation] = []
        for candidate in sorted(evaluation_dir.glob("*.json")):
            document = self._load_evaluation_document(candidate)
            if document is not None:
                documents.append(document)
        return documents

    @staticmethod
    def _load_evaluation_document(path: Path) -> StoredTrajectoryEvaluation | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = TrajectoryEvaluationResult.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError):
            return None
        return StoredTrajectoryEvaluation(path=path, result=result)

    @staticmethod
    def _controls_match(result: TrajectoryEvaluationResult, controls: EvaluationControls) -> bool:
        return (
            result.pose_relation == controls.pose_relation
            and result.align == controls.align
            and result.correct_scale == controls.correct_scale
            and abs(result.max_diff_s - controls.max_diff_s) < 1e-12
        )

    def _ensure_reference_path(self, selection: MetricsSelection) -> Path:
        if selection.reference_path is not None and selection.reference_path.exists():
            return selection.reference_path
        if selection.reference_csv_path is None:
            msg = "A reference trajectory is not available for the selected dataset slice."
            raise FileNotFoundError(msg)
        target_path = selection.run.artifact_root / "evaluation" / "advio_ground_truth.tum"
        return convert_advio_pose_csv_to_tum(selection.reference_csv_path, target_path)

    @staticmethod
    def _evaluation_output_path(artifact_root: Path, controls: EvaluationControls) -> Path:
        align_flag = "align" if controls.align else "no-align"
        scale_flag = "scale" if controls.correct_scale else "no-scale"
        diff_token = str(controls.max_diff_s).replace(".", "p")
        filename = (
            f"trajectory_eval__{controls.pose_relation.value}__{align_flag}__{scale_flag}__diff-{diff_token}.json"
        )
        return artifact_root / "evaluation" / filename


class Record3DService:
    """Provide typed app-level access to optional Record3D capabilities."""

    def probe_usb_status(self) -> Record3DUSBStatus:
        """Return the current USB Record3D availability summary."""
        return probe_record3d_usb_status()


__all__ = ["EvaluationService", "Record3DService"]
