"""Ground-alignment stage binding."""

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
from prml_vslam.pipeline.stages.ground_alignment.contracts import GroundAlignmentRuntimeInput


class GroundAlignmentStageBinding(StageBinding):
    """Bind ``gravity.align`` config to runtime execution."""

    key = StageKey.GRAVITY_ALIGNMENT
    section_name = "align_ground"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return ground-alignment metadata output."""
        return [context.run_paths.ground_alignment_path]

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return whether ground alignment has SLAM geometry to consume."""
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Ground alignment requires `[stages.slam.backend]`."
        descriptor = context.backend if context.backend is not None else slam_backend.describe()
        if not descriptor.capabilities.dense_points:
            return False, f"{descriptor.display_name} does not expose point-cloud outputs for ground alignment."
        outputs = context.run_config.stages.slam.outputs
        if not (outputs.emit_dense_points or outputs.emit_sparse_points):
            return False, "Ground alignment requires sparse or dense point-cloud outputs from the SLAM stage."
        return True, None

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy ground-alignment runtime factory."""
        del context
        from prml_vslam.pipeline.stages.ground_alignment.runtime import GroundAlignmentRuntime

        return GroundAlignmentRuntime

    def build_offline_input(self, context: StageInputContext) -> GroundAlignmentRuntimeInput:
        """Build the narrow ground-alignment runtime input."""
        return GroundAlignmentRuntimeInput(
            config=context.run_config.stages.align_ground.ground,
            run_paths=context.run_paths,
            slam=context.results.require_slam_artifacts(),
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return ground-alignment config and SLAM geometry fingerprint payloads."""
        slam = context.results.require_slam_artifacts()
        return FailureFingerprint(
            config_payload=context.run_config.stages.align_ground.ground,
            input_payload={
                "trajectory_tum": slam.trajectory_tum,
                "dense_points_ply": slam.dense_points_ply,
                "sparse_points_ply": slam.sparse_points_ply,
            },
        )


__all__ = ["GroundAlignmentStageBinding"]
