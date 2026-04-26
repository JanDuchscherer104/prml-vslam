"""Persisted config and backend muxing for the ``reconstruction`` stage."""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.context import PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.reconstruction.config import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from prml_vslam.reconstruction.stage.contracts import (
    ReconstructionBackend,
    ReconstructionInputSelection,
    ReconstructionInputSourceKind,
)
from prml_vslam.sources.config import TumRgbdSourceConfig


class ReconstructionStageConfig(StageConfig):
    """Persisted reconstruction stage policy and backend selection."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.RECONSTRUCTION
    backend: ReconstructionBackend = Field(default_factory=Open3dTsdfBackendConfig)
    """Concrete reconstruction backend config."""

    input_selection: ReconstructionInputSelection = Field(default_factory=ReconstructionInputSelection)
    """Policy for selecting the upstream payload used by reconstruction."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        return [context.run_paths.reference_cloud_path]

    def availability(self, context: PipelinePlanContext) -> tuple[bool, str | None]:
        if self.input_selection.source_kind in {
            ReconstructionInputSourceKind.SLAM_DENSE_POINT_CLOUD,
            ReconstructionInputSourceKind.SLAM_SPARSE_POINT_CLOUD,
            ReconstructionInputSourceKind.SLAM_PREDICTED_GEOMETRY_SEQUENCE,
        }:
            slam_backend = context.run_config.stages.slam.backend
            if slam_backend is None:
                return False, "SLAM-derived reconstruction requires `[stages.slam.backend]`."
            outputs = context.run_config.stages.slam.outputs
            if self.input_selection.source_kind is ReconstructionInputSourceKind.SLAM_DENSE_POINT_CLOUD:
                if not outputs.emit_dense_points:
                    return False, "SLAM dense-point reconstruction requires dense SLAM point-cloud outputs."
            if self.input_selection.source_kind is ReconstructionInputSourceKind.SLAM_SPARSE_POINT_CLOUD:
                if not outputs.emit_sparse_points:
                    return False, "SLAM sparse-point reconstruction requires sparse SLAM point-cloud outputs."
            return True, None

        source_backend = context.run_config.stages.source.backend
        if not isinstance(source_backend, TumRgbdSourceConfig):
            return False, "Reconstruction currently requires a TUM RGB-D dataset source."
        return True, None


__all__ = [
    "ReconstructionBackend",
    "ReconstructionBackendConfig",
    "ReconstructionStageConfig",
]
