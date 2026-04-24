"""Source stage binding."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.stages.base.binding import (
    FailureFingerprint,
    PlanContext,
    RuntimeBuildContext,
    StageBinding,
    StageInputContext,
)
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.proxy import RuntimeCapability
from prml_vslam.pipeline.stages.source.runtime import SourceRuntime, SourceRuntimeConfigInput, SourceRuntimeInput


class SourceStageBinding(StageBinding):
    """Bind source stage config to planning, runtime construction, and inputs."""

    key = StageKey.SOURCE
    section_name = "source"

    def planned_outputs(self, context: PlanContext) -> list[Path]:
        """Return source-owned normalized input artifacts."""
        return [context.run_paths.sequence_manifest_path, context.run_paths.benchmark_inputs_path]

    def runtime_factory(self, context: RuntimeBuildContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy source runtime factory bound to the prepared source."""
        if context.source is None:
            raise RuntimeError("Source stage runtime construction requires a source adapter.")

        def _factory() -> BaseStageRuntime:
            return SourceRuntime(source=context.source)

        return _factory

    def build_offline_input(self, context: StageInputContext) -> SourceRuntimeInput:
        """Build the narrow source runtime input."""
        source_backend = context.run_config.stages.source.backend
        slam_backend = context.run_config.stages.slam.backend
        return SourceRuntimeInput(
            config_input=SourceRuntimeConfigInput(
                mode=context.run_config.mode,
                frame_stride=1 if source_backend is None else source_backend.frame_stride,
                streaming_max_frames=None if slam_backend is None else slam_backend.max_frames,
                config_hash=stable_hash(source_backend),
                input_fingerprint=stable_hash(source_backend),
            ),
            artifact_root=context.plan.artifact_root,
        )

    def failure_fingerprint(self, context: StageInputContext) -> FailureFingerprint:
        """Return source config and input fingerprint payloads."""
        source_backend = context.run_config.stages.source.backend
        return FailureFingerprint(config_payload=source_backend, input_payload=source_backend)

    def runtime_capabilities(self, mode: PipelineMode) -> frozenset[RuntimeCapability]:
        """Return source runtime capabilities."""
        del mode
        return frozenset({RuntimeCapability.OFFLINE})


__all__ = ["SourceStageBinding"]
