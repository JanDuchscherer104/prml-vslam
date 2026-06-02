"""Persisted config for the ``align.trajectory`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict

from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.sources.contracts import ReferenceSource


class TrajectoryAlignmentStageConfig(StageConfig):
    """Stage-owned Sim(3) alignment policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.TRAJECTORY_ALIGNMENT
    enabled: bool = False
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        slam_backend = context.run_config.stages.slam.backend
        if slam_backend is None:
            return False, "Trajectory alignment requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else slam_backend
        if not backend.supports_trajectory_benchmark:
            return False, f"{backend.display_name} does not support trajectory alignment."
        return True, None

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return deterministic artifacts produced by ``align.trajectory``."""

        return [
            context.run_paths.artifact_root / "evaluation" / "trajectory_alignment.json",
            context.run_paths.artifact_root / "evaluation" / "trajectory_sim3_aligned.tum",
            context.run_paths.artifact_root / "evaluation" / "point_cloud_sim3_aligned.ply",
        ]


__all__ = ["TrajectoryAlignmentStageConfig"]
