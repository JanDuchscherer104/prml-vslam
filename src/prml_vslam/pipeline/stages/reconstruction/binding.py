"""Reconstruction stage binding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.binding import (
    FailureFingerprint,
    PlanContext,
    RuntimeBuildContext,
    StageBinding,
    StageInputContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability
from prml_vslam.pipeline.stages.reconstruction.contracts import ReconstructionRuntimeInput
from prml_vslam.pipeline.stages.source.config import TumRgbdSourceConfig


class ReconstructionStageBinding(StageBinding):
    """Bind reconstruction config to runtime execution."""

    key = StageKey.RECONSTRUCTION
    section_name = "reconstruction"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return reconstruction output artifacts."""
        return [context.run_paths.reference_cloud_path]

    def availability(self, context: PlanContext) -> tuple[bool, str | None]:
        """Return whether reconstruction has source RGB-D inputs."""
        source_backend = context.run_config.stages.source.backend
        if not isinstance(source_backend, TumRgbdSourceConfig):
            return False, "Reconstruction currently requires a TUM RGB-D dataset source."
        return True, None

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy reconstruction runtime factory."""
        del context
        from prml_vslam.pipeline.stages.reconstruction.runtime import ReconstructionRuntime

        return ReconstructionRuntime

    def runtime_capabilities(self, mode: PipelineMode) -> frozenset[RuntimeCapability]:
        """Return reconstruction runtime capabilities."""
        del mode
        return frozenset({RuntimeCapability.OFFLINE, RuntimeCapability.LIVE_UPDATES})

    def build_offline_input(self, context: StageInputContext) -> ReconstructionRuntimeInput:
        """Build the narrow reconstruction runtime input."""
        return ReconstructionRuntimeInput(
            backend=context.run_config.stages.reconstruction.backend,
            run_paths=context.run_paths,
            benchmark_inputs=context.results.require_benchmark_inputs(),
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return reconstruction config and source RGB-D fingerprint payloads."""
        return FailureFingerprint(
            config_payload=context.run_config.stages.reconstruction.backend,
            input_payload=context.results.require_benchmark_inputs(),
        )


__all__ = ["ReconstructionStageBinding"]
