"""Minimal local runtime handle used by the pipeline coordinator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal, cast

from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.protocols import (
    BaseStageRuntime,
    LiveUpdateStageRuntime,
    OfflineStageRuntime,
    StreamingStageRuntime,
)
from prml_vslam.utils import BaseData

JsonScalar = str | int | float | bool | None
RuntimeInput = BaseData
StreamItem = BaseData | FramePacket
DeploymentKind = Literal["in_process", "ray"]


class RuntimeCapability(StrEnum):
    """Name runtime protocol capabilities required by a stage."""

    OFFLINE = "offline"
    LIVE_UPDATES = "live_updates"
    STREAMING = "streaming"


@dataclass
class StageRuntimeHandle(BaseStageRuntime):
    """Wrap one local runtime with counters and capability checks."""

    stage_key: StageKey
    runtime: BaseStageRuntime
    supported_capabilities: frozenset[RuntimeCapability]
    executor_id: str | None = None
    resource_assignment: dict[str, JsonScalar] = field(default_factory=dict)
    _submitted_count: int = 0
    _completed_count: int = 0
    _failed_count: int = 0
    _in_flight_count: int = 0

    def __post_init__(self) -> None:
        """Validate declared capabilities against the wrapped local runtime."""
        if RuntimeCapability.OFFLINE in self.supported_capabilities and not isinstance(
            self.runtime, OfflineStageRuntime
        ):
            raise TypeError(f"Runtime for stage '{self.stage_key.value}' does not implement OfflineStageRuntime.")
        if RuntimeCapability.LIVE_UPDATES in self.supported_capabilities and not isinstance(
            self.runtime, LiveUpdateStageRuntime
        ):
            raise TypeError(f"Runtime for stage '{self.stage_key.value}' does not implement LiveUpdateStageRuntime.")
        if RuntimeCapability.STREAMING in self.supported_capabilities and not isinstance(
            self.runtime, StreamingStageRuntime
        ):
            raise TypeError(f"Runtime for stage '{self.stage_key.value}' does not implement StreamingStageRuntime.")

    def status(self) -> StageRuntimeStatus:
        """Return wrapped runtime status with handle-owned counters."""
        status = self.runtime.status()
        return status.model_copy(
            update={
                "submitted_count": self._submitted_count,
                "completed_count": self._completed_count,
                "failed_count": self._failed_count,
                "in_flight_count": self._in_flight_count,
                "executor_id": self.executor_id if self.executor_id is not None else status.executor_id,
                "resource_assignment": self.resource_assignment or status.resource_assignment,
            }
        )

    def stop(self) -> None:
        """Request runtime stop through the wrapped runtime."""
        self.runtime.stop()

    def run_offline(self, input_payload: RuntimeInput) -> StageResult:
        """Invoke the wrapped offline runtime."""
        self._require_capability(RuntimeCapability.OFFLINE)
        runtime = cast(OfflineStageRuntime[RuntimeInput], self.runtime)
        return self._counted(lambda: runtime.run_offline(input_payload))

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Drain updates from a live-update runtime."""
        self._require_capability(RuntimeCapability.LIVE_UPDATES)
        runtime = cast(LiveUpdateStageRuntime, self.runtime)
        return runtime.drain_runtime_updates(max_items=max_items)

    def start_streaming(self, input_payload: RuntimeInput) -> None:
        """Start the wrapped streaming runtime."""
        self._require_capability(RuntimeCapability.STREAMING)
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        self._counted(lambda: runtime.start_streaming(input_payload))

    def submit_stream_item(self, item: StreamItem) -> None:
        """Submit one item to the wrapped streaming runtime."""
        self._require_capability(RuntimeCapability.STREAMING)
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        self._counted(lambda: runtime.submit_stream_item(item))

    def finish_streaming(self) -> StageResult:
        """Finalize the wrapped streaming runtime."""
        self._require_capability(RuntimeCapability.STREAMING)
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        return self._counted(runtime.finish_streaming)

    def _require_capability(self, capability: RuntimeCapability) -> None:
        if capability not in self.supported_capabilities:
            raise RuntimeError(f"Runtime for stage '{self.stage_key.value}' does not support '{capability.value}'.")

    def _counted(self, call):
        self._submitted_count += 1
        self._in_flight_count += 1
        try:
            result = call()
        except Exception:
            self._failed_count += 1
            self._in_flight_count -= 1
            raise
        self._completed_count += 1
        self._in_flight_count -= 1
        return result


__all__ = ["DeploymentKind", "RuntimeCapability", "StageRuntimeHandle"]
