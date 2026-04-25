"""Persisted config and backend muxing for the ``reconstruction`` stage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import (
    FailureFingerprint,
    StageConfig,
    StageInputContext,
    StagePlanContext,
    StageRuntimeBuildContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.reconstruction.config import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from prml_vslam.sources.config import TumRgbdSourceConfig

ReconstructionBackend: TypeAlias = Annotated[
    Open3dTsdfBackendConfig,
    Field(discriminator="method_id"),
]


class ReconstructionStageConfig(StageConfig):
    """Persisted reconstruction stage policy and backend selection."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.RECONSTRUCTION
    backend: ReconstructionBackend = Field(default_factory=Open3dTsdfBackendConfig)
    """Concrete reconstruction backend config."""

    def planned_outputs(self, context: StagePlanContext) -> list[Path]:
        return [context.run_paths.reference_cloud_path]

    def availability(self, context: StagePlanContext) -> tuple[bool, str | None]:
        source_backend = context.run_config.stages.source.backend
        if not isinstance(source_backend, TumRgbdSourceConfig):
            return False, "Reconstruction currently requires a TUM RGB-D dataset source."
        return True, None

    def runtime_factory(self, context: StageRuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        del context
        from prml_vslam.reconstruction.stage.runtime import ReconstructionRuntime

        return ReconstructionRuntime

    def build_offline_input(self, context: StageInputContext):
        from prml_vslam.reconstruction.stage.runtime import ReconstructionStageInput

        return ReconstructionStageInput(
            backend=self.backend,
            run_paths=context.run_paths,
            benchmark_inputs=context.results.require_benchmark_inputs(),
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        return FailureFingerprint(
            config_payload=self.backend,
            input_payload=context.results.require_benchmark_inputs(),
        )


__all__ = [
    "ReconstructionBackend",
    "ReconstructionBackendConfig",
    "ReconstructionStageConfig",
]
