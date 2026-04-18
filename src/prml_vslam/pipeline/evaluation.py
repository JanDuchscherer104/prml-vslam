"""Pipeline-side helpers for trajectory evaluation execution."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.eval.contracts import DiscoveredRun, EvaluationArtifact, SelectionSnapshot
from prml_vslam.eval.services import TrajectoryEvaluationService
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.plan import RunPlan, RunPlanStageId
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import BaseData, PathConfig


class TrajectoryEvaluationExecution(BaseData):
    """Trajectory-evaluation execution outcome for one pipeline run."""

    started: bool = False
    """Whether the trajectory stage was actually attempted."""

    reference_path: Path | None = None
    """Resolved reference trajectory path used for evaluation."""

    estimate_path: Path | None = None
    """Resolved estimated trajectory path used for evaluation."""

    artifact: EvaluationArtifact | None = None
    """Persisted evaluation artifact when stage execution succeeds."""

    error_message: str = ""
    """Explicit surfaced stage error when evaluation fails."""


def execute_trajectory_evaluation(
    *,
    request: RunRequest,
    plan: RunPlan,
    sequence_manifest: SequenceManifest | None,
    benchmark_inputs: PreparedBenchmarkInputs | None,
    slam: SlamArtifacts | None,
) -> TrajectoryEvaluationExecution:
    """Execute one explicit trajectory-evaluation stage for the planned run."""
    planned_stage_ids = {stage.id for stage in plan.stages}
    if not request.benchmark.trajectory.enabled or RunPlanStageId.TRAJECTORY_EVALUATION not in planned_stage_ids:
        return TrajectoryEvaluationExecution()

    execution = TrajectoryEvaluationExecution(started=True)
    if sequence_manifest is None:
        execution.error_message = "Trajectory evaluation requires a prepared sequence manifest."
        return execution
    if slam is None:
        execution.error_message = "Trajectory evaluation requires SLAM trajectory artifacts."
        return execution

    estimate_path = slam.trajectory_tum.path
    execution.estimate_path = estimate_path
    if not estimate_path.exists():
        execution.error_message = f"Estimated trajectory is missing: '{estimate_path}'."
        return execution

    if benchmark_inputs is None:
        execution.error_message = "Trajectory evaluation requires prepared benchmark reference trajectories."
        return execution

    reference = benchmark_inputs.trajectory_for_source(request.benchmark.trajectory.baseline_source)
    if reference is None:
        execution.error_message = (
            "Missing reference trajectory for selected baseline "
            f"'{request.benchmark.trajectory.baseline_source.value}'."
        )
        return execution

    execution.reference_path = reference.path
    if not reference.path.exists():
        execution.error_message = f"Reference trajectory is missing: '{reference.path}'."
        return execution

    selection = SelectionSnapshot(
        sequence_slug=sequence_manifest.sequence_id,
        reference_path=reference.path,
        run=DiscoveredRun(
            artifact_root=plan.artifact_root,
            estimate_path=estimate_path,
            method=plan.method,
            label=plan.method.display_name,
        ),
    )
    try:
        service = TrajectoryEvaluationService(PathConfig())
        execution.artifact = service.compute_evaluation(selection=selection)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        execution.error_message = str(exc)
    return execution


__all__ = ["TrajectoryEvaluationExecution", "execute_trajectory_evaluation"]
