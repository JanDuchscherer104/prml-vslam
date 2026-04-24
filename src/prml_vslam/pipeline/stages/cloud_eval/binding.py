"""Dense-cloud diagnostic stage binding."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import PlanContext, StageBinding


class CloudEvaluationStageBinding(StageBinding):
    """Declare the planned dense-cloud diagnostic stage without a runtime."""

    key = StageKey.CLOUD_EVALUATION
    section_name = "evaluate_cloud"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return planned dense-cloud metrics output."""
        return [context.run_paths.cloud_metrics_path]

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return the placeholder availability diagnostic."""
        del context
        return False, "Dense-cloud evaluation is planned but no runtime is registered yet."


__all__ = ["CloudEvaluationStageBinding"]
