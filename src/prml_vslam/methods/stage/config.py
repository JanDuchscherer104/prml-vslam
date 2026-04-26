"""Persisted SLAM stage policy."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.methods.stage.backend_config import BackendConfig, MethodId, SlamOutputPolicy
from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig


class SlamStageConfig(StageConfig):
    """Persisted SLAM stage policy, backend selection, and output policy."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SLAM
    backend: BackendConfig | None = None
    """Selected SLAM backend config."""

    outputs: SlamOutputPolicy = Field(default_factory=SlamOutputPolicy)
    """SLAM output materialization policy."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return SLAM-owned output artifacts."""
        if self.backend is None:
            return []
        run_paths = context.run_paths
        artifact_paths = [run_paths.trajectory_path]
        if self.backend.method_id is MethodId.VISTA:
            if self.outputs.emit_sparse_points or self.outputs.emit_dense_points:
                artifact_paths.append(run_paths.point_cloud_path)
            return artifact_paths
        if self.outputs.emit_sparse_points:
            artifact_paths.append(run_paths.sparse_points_path)
        if self.outputs.emit_dense_points:
            artifact_paths.append(run_paths.dense_points_path)
        return artifact_paths

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        """Return whether the selected backend can execute in the selected mode."""
        if self.backend is None:
            return False, "SLAM stage requires `[stages.slam.backend]`."
        backend = context.slam_backend if context.slam_backend is not None else self.backend
        if context.run_config.mode is PipelineMode.OFFLINE and not backend.supports_offline:
            return False, f"{backend.display_name} does not support offline execution."
        if context.run_config.mode is PipelineMode.STREAMING and not backend.supports_streaming:
            return False, f"{backend.display_name} does not support streaming execution."
        return True, None


__all__ = ["SlamStageConfig"]
