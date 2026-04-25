"""Persisted source-stage config and source backend muxing."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pydantic import ConfigDict

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext, PipelinePlanContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint, StageConfig
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.sources.config import SourceBackendConfig
from prml_vslam.sources.stage.contracts import SourceStageInput
from prml_vslam.utils.serialization import stable_hash


class SourceStageConfig(StageConfig):
    """Target source-stage policy plus source backend selection."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.SOURCE
    """Canonical source stage key."""

    backend: SourceBackendConfig | None = None
    """Concrete source backend config that constructs the source adapter."""

    def planned_outputs(self, context: PipelinePlanContext) -> list[Path]:
        """Return source-owned normalized input artifacts."""
        return [context.run_paths.sequence_manifest_path, context.run_paths.benchmark_inputs_path]

    def runtime_factory(self, context: PipelineExecutionContext) -> Callable[[], BaseStageRuntime]:
        """Return a lazy source runtime factory bound to the prepared source."""
        if context.source is None:
            raise RuntimeError("Source stage runtime construction requires a source adapter.")

        def _factory() -> BaseStageRuntime:
            from prml_vslam.sources.stage.runtime import SourceRuntime

            return SourceRuntime(source=context.source)

        return _factory

    def build_offline_input(self, context: PipelineExecutionContext) -> SourceStageInput:
        """Build the narrow source runtime input."""
        source_backend = self.backend
        slam_backend = context.run_config.stages.slam.backend
        return SourceStageInput(
            artifact_root=context.plan.artifact_root,
            mode=context.run_config.mode,
            frame_stride=1 if source_backend is None else source_backend.frame_stride,
            streaming_max_frames=None if slam_backend is None else slam_backend.max_frames,
            config_hash=stable_hash(source_backend),
            input_fingerprint=stable_hash(source_backend),
        )

    def failure_fingerprint(self, context: PipelineExecutionContext) -> FailureFingerprint:
        """Return source config and input fingerprint payloads."""
        del context
        return FailureFingerprint(config_payload=self.backend, input_payload=self.backend)


__all__ = ["SourceStageConfig"]
