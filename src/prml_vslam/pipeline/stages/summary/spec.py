"""Runtime spec for the summary stage."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.spec import StageRuntimeSpec
from prml_vslam.pipeline.stages.summary.runtime import SummaryRuntime, SummaryStageInput


def _build_offline_input(context: PipelineExecutionContext) -> SummaryStageInput:
    return SummaryStageInput(
        experiment_name=context.run_config.experiment_name,
        mode=context.run_config.mode,
        plan=context.plan,
        run_paths=context.run_paths,
        stage_outcomes=context.results.ordered_outcomes(),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    return FailureFingerprint(
        config_payload={
            "experiment_name": context.run_config.experiment_name,
            "mode": context.run_config.mode.value,
        },
        input_payload=context.results.ordered_outcomes(),
    )


SUMMARY_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.SUMMARY,
    runtime_factory=lambda _context: SummaryRuntime,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["SUMMARY_STAGE_SPEC"]
