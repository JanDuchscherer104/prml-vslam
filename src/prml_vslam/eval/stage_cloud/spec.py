"""Runtime spec for the dense-cloud evaluation stage."""

from __future__ import annotations

from prml_vslam.eval.contracts import CloudAlignmentArtifact, DenseCloudEvaluationSelection
from prml_vslam.eval.stage_cloud.contracts import CloudEvaluationStageInput
from prml_vslam.eval.stage_cloud.runtime import CloudEvaluationRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _build_offline_input(context: PipelineExecutionContext) -> CloudEvaluationStageInput:
    config = context.run_config.stages.evaluate_cloud
    alignment = context.results.require_payload(StageKey.CLOUD_ALIGNMENT, CloudAlignmentArtifact)
    return CloudEvaluationStageInput(
        selection=DenseCloudEvaluationSelection(
            artifact_root=context.plan.artifact_root,
            reference_cloud_path=alignment.reference_cloud_path,
            estimate_cloud_path=alignment.icp_point_cloud_path,
            f_score_threshold_m=config.selection.f_score_threshold_m,
        )
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    alignment = context.results.require_payload(StageKey.CLOUD_ALIGNMENT, CloudAlignmentArtifact)
    return FailureFingerprint(
        config_payload=context.run_config.stages.evaluate_cloud,
        input_payload={
            "reference_cloud_path": alignment.reference_cloud_path.as_posix(),
            "estimate_cloud_path": alignment.icp_point_cloud_path.as_posix(),
        },
    )


CLOUD_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.CLOUD_EVALUATION,
    runtime_factory=lambda _context: CloudEvaluationRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["CLOUD_EVALUATION_STAGE_SPEC"]
