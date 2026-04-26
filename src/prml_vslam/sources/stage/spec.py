"""Runtime spec for the source stage."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.pipeline.stages.base.spec import RuntimeFactory, StageRuntimeSpec
from prml_vslam.sources.stage.contracts import SourceStageInput
from prml_vslam.sources.stage.runtime import SourceRuntime
from prml_vslam.utils.serialization import stable_hash


def _runtime_factory(context: PipelineExecutionContext) -> RuntimeFactory:
    if context.source is None:
        raise RuntimeError("Source stage runtime construction requires a source adapter.")

    def _factory() -> BaseStageRuntime:
        return SourceRuntime(source=context.source)

    return _factory


def _build_offline_input(context: PipelineExecutionContext) -> SourceStageInput:
    source_config = context.run_config.stages.source
    source_backend = source_config.backend
    slam_backend = context.run_config.stages.slam.backend
    return SourceStageInput(
        artifact_root=context.plan.artifact_root,
        mode=context.run_config.mode,
        frame_stride=1 if source_backend is None else source_backend.frame_stride,
        streaming_max_frames=None if slam_backend is None else slam_backend.max_frames,
        config_hash=stable_hash(source_backend),
        input_fingerprint=stable_hash(source_backend),
    )


def _failure_fingerprint(context: PipelineExecutionContext) -> FailureFingerprint:
    source_backend = context.run_config.stages.source.backend
    return FailureFingerprint(config_payload=source_backend, input_payload=source_backend)


SOURCE_STAGE_SPEC = StageRuntimeSpec(
    stage_key=StageKey.SOURCE,
    runtime_factory=_runtime_factory,
    build_offline_input=_build_offline_input,
    failure_fingerprint=_failure_fingerprint,
)

__all__ = ["SOURCE_STAGE_SPEC"]
