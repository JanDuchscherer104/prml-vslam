"""Persisted config for the projection-only ``summary`` stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import ConfigDict

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime


class SummaryStageConfig(StageConfig):
    """Summary-stage policy without metric or runtime interpretation."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SUMMARY

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.summary_path, context.run_paths.stage_manifests_path]

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        del context
        from prml_vslam.pipeline.stages.summary.runtime import SummaryRuntime

        return SummaryRuntime

    def build_offline_input(self, context: PipelineExecutionContext):
        from prml_vslam.pipeline.stages.summary.runtime import SummaryStageInput

        return SummaryStageInput(
            experiment_name=context.run_config.experiment_name,
            mode=context.run_config.mode,
            plan=context.plan,
            run_paths=context.run_paths,
            stage_outcomes=context.results.ordered_outcomes(),
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        return FailureFingerprint(
            config_payload={
                "experiment_name": context.run_config.experiment_name,
                "mode": context.run_config.mode.value,
            },
            input_payload=context.results.ordered_outcomes(),
        )


__all__ = ["SummaryStageConfig"]
