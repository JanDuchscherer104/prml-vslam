"""Summary stage binding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import (
    FailureFingerprint,
    PlanContext,
    RuntimeBuildContext,
    StageBinding,
    StageInputContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.summary.contracts import SummaryRuntimeInput
from prml_vslam.pipeline.stages.summary.runtime import SummaryRuntime


class SummaryStageBinding(StageBinding):
    """Bind summary config to projection runtime execution."""

    key = StageKey.SUMMARY
    section_name = "summary"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return summary output artifacts."""
        return [context.run_paths.summary_path, context.run_paths.stage_manifests_path]

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy summary runtime factory."""
        del context
        return SummaryRuntime

    def build_offline_input(self, context: StageInputContext) -> SummaryRuntimeInput:
        """Build the narrow summary runtime input."""
        return SummaryRuntimeInput(
            experiment_name=context.run_config.experiment_name,
            mode=context.run_config.mode,
            plan=context.plan,
            run_paths=context.run_paths,
            stage_outcomes=context.results.ordered_outcomes(),
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return summary config and prior stage outcomes fingerprint payloads."""
        return FailureFingerprint(
            config_payload={
                "experiment_name": context.run_config.experiment_name,
                "mode": context.run_config.mode.value,
            },
            input_payload=context.results.ordered_outcomes(),
        )


__all__ = ["SummaryStageBinding"]
