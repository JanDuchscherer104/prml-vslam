"""Runtime spec for the image-evaluation stage."""

from __future__ import annotations

from prml_vslam.eval.render_eval import RenderEvalConfig
from prml_vslam.eval.stage_image.config import ImageEvaluationPolicy
from prml_vslam.eval.stage_image.contracts import ImageEvaluationStageInput
from prml_vslam.eval.stage_image.runtime import ImageEvaluationRuntime
from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec


def _render_config(policy: ImageEvaluationPolicy) -> RenderEvalConfig:
    return RenderEvalConfig(
        depth_max_m=policy.depth_max_m,
        dilation_px=policy.dilation_px,
        save_gallery=policy.save_gallery,
        gallery_every=policy.gallery_every,
        compute_lpips=policy.compute_lpips,
        lpips_net=policy.lpips_net,
    )


def _build_offline_input(context: PipelineExecutionContext) -> ImageEvaluationStageInput:
    config = context.run_config.stages.evaluate_image
    return ImageEvaluationStageInput(
        artifact_root=context.plan.artifact_root,
        render_config=_render_config(config.rendering),
        slam=context.results.require_slam_artifacts(),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    slam = context.results.require_slam_artifacts()
    return FailureFingerprint(
        config_payload=context.run_config.stages.evaluate_image.rendering,
        input_payload={
            "slam_dense": slam.dense_points_ply,
            "slam_trajectory": slam.trajectory_tum,
        },
    )


IMAGE_EVALUATION_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.IMAGE_EVALUATION,
    runtime_factory=lambda _context: ImageEvaluationRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["IMAGE_EVALUATION_STAGE_SPEC"]
