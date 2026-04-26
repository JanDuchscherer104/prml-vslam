"""Stage-owned runtime integration contracts.

Specs bind the generic runner to domain-owned runtime inputs without putting
input construction on persisted config models. They are evaluated by the local
coordinator/runner so remote runtimes receive only narrow, serializable stage
input DTOs.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from prml_vslam.pipeline.contracts.context import PipelineExecutionContext
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import FailureFingerprint
from prml_vslam.pipeline.stages.base.protocols import BaseStageRuntime
from prml_vslam.utils import BaseData

RuntimeFactory = Callable[[], BaseStageRuntime]
RuntimeFactoryBuilder = Callable[[PipelineExecutionContext], RuntimeFactory | None]
StageInputBuilder = Callable[[PipelineExecutionContext], BaseData]
FailureFingerprintBuilder = Callable[[PipelineExecutionContext], FailureFingerprint]


@dataclass(frozen=True, slots=True)
class StageRuntimeSpec:
    """Stage-owned integration surface used by generic runtime plumbing."""

    stage_key: StageKey
    """Canonical stage key represented by this runtime spec."""

    runtime_factory: RuntimeFactoryBuilder
    """Build a lazy runtime factory for the current execution context."""

    build_offline_input: StageInputBuilder | None = None
    """Build the bounded/offline input payload consumed by the stage runtime."""

    build_streaming_start_input: StageInputBuilder | None = None
    """Build the run-scoped payload used to start a streaming runtime."""

    failure_fingerprint: FailureFingerprintBuilder | None = None
    """Build stable config and input payloads for failure provenance."""


__all__ = [
    "FailureFingerprintBuilder",
    "RuntimeFactory",
    "RuntimeFactoryBuilder",
    "StageInputBuilder",
    "StageRuntimeSpec",
]
