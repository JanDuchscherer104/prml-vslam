"""Runtime spec for the dense-cloud evaluation stage."""

from __future__ import annotations

from prml_vslam.eval.contracts import DenseCloudEvaluationSelection, EvaluationArtifact
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationStageInput
from prml_vslam.eval.stage_cloud.runtime import CloudEvaluationRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.runner import StageDependencyError
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.reconstruction import ReconstructionArtifacts


def _build_offline_input(context: PipelineExecutionContext) -> CloudEvaluationStageInput:
    config = context.run_config.stages.evaluate_cloud
    reconstruction = context.results.require_payload(StageKey.RECONSTRUCTION, ReconstructionArtifacts)
    trajectory_evaluation = context.results.require_payload(StageKey.TRAJECTORY_EVALUATION, EvaluationArtifact)
    if trajectory_evaluation.aligned_point_cloud_path is None:
        raise StageDependencyError(
            "Cloud evaluation requires the trajectory-evaluation stage to materialize a Sim(3)-aligned SLAM point cloud."
        )
    return CloudEvaluationStageInput(
        selection=DenseCloudEvaluationSelection(
            artifact_root=context.plan.artifact_root,
            reference_cloud_path=reconstruction.reference_cloud_path,
            estimate_cloud_path=trajectory_evaluation.aligned_point_cloud_path,
            f_score_threshold_m=config.selection.f_score_threshold_m,
        )
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    trajectory_evaluation = context.results.require_payload(StageKey.TRAJECTORY_EVALUATION, EvaluationArtifact)
    reconstruction = context.results.require_payload(StageKey.RECONSTRUCTION, ReconstructionArtifacts)
    return FailureFingerprint(
        config_payload=context.run_config.stages.evaluate_cloud,
        input_payload={
            "reference_cloud_path": reconstruction.reference_cloud_path,
            "estimate_cloud_path": trajectory_evaluation.aligned_point_cloud_path,
        },
    )


CLOUD_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.CLOUD_EVALUATION,
    runtime_factory=lambda _context: CloudEvaluationRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["CLOUD_EVALUATION_STAGE_SPEC"]
