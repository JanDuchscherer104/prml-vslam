"""Deployment-neutral stage runtime proxy scaffolding.

``StageRuntimeProxy`` hides whether a runtime is local or Ray-hosted while
exposing only the capability views selected by runtime preflight. Unsupported
capabilities fail at view selection time instead of becoming no-op methods.
"""

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
    """Name runtime protocol capabilities exposed through a proxy."""

    OFFLINE = "offline"
    LIVE_UPDATES = "live_updates"
    STREAMING = "streaming"


@dataclass
class StageRuntimeProxy(BaseStageRuntime):
    """Wrap one runtime and expose explicit capability-specific views."""

    stage_key: StageKey
    runtime: BaseStageRuntime
    supported_capabilities: frozenset[RuntimeCapability]
    deployment_kind: DeploymentKind = "in_process"
    executor_id: str | None = None
    resource_assignment: dict[str, JsonScalar] = field(default_factory=dict)
    _submitted_count: int = 0
    _completed_count: int = 0
    _failed_count: int = 0
    _in_flight_count: int = 0

    def __post_init__(self) -> None:
        """Validate that declared capabilities match the wrapped runtime."""
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
        """Return wrapped runtime status with proxy-owned task counters."""
        status = self.runtime.status()
        executor_id = self.executor_id if self.executor_id is not None else status.executor_id
        resource_assignment = self.resource_assignment or status.resource_assignment
        return status.model_copy(
            update={
                "submitted_count": self._submitted_count,
                "completed_count": self._completed_count,
                "failed_count": self._failed_count,
                "in_flight_count": self._in_flight_count,
                "executor_id": executor_id,
                "resource_assignment": resource_assignment,
            }
        )

    def stop(self) -> None:
        """Request runtime stop through the wrapped runtime."""
        self.runtime.stop()

    def offline(self) -> OfflineStageRuntime[RuntimeInput]:
        """Return an offline-capability view or fail before invocation."""
        self._require_capability(RuntimeCapability.OFFLINE)
        return _OfflineProxyView(self)

    def live_updates(self) -> LiveUpdateStageRuntime:
        """Return a live-update-capability view or fail before invocation."""
        self._require_capability(RuntimeCapability.LIVE_UPDATES)
        return _LiveUpdateProxyView(self)

    def streaming(self) -> StreamingStageRuntime[RuntimeInput, StreamItem]:
        """Return a streaming-capability view or fail before invocation."""
        self._require_capability(RuntimeCapability.STREAMING)
        return _StreamingProxyView(self)

    def _require_capability(self, capability: RuntimeCapability) -> None:
        if capability not in self.supported_capabilities:
            raise RuntimeError(f"Runtime for stage '{self.stage_key.value}' does not support '{capability.value}'.")

    def _run_offline(self, input_payload: RuntimeInput) -> StageResult:
        runtime = cast(OfflineStageRuntime[RuntimeInput], self.runtime)
        self._mark_submitted()
        try:
            result = runtime.run_offline(input_payload)
        except Exception:
            self._mark_failed()
            raise
        self._mark_completed()
        return result

    def _drain_runtime_updates(self, max_items: int | None) -> list[StageRuntimeUpdate]:
        runtime = cast(LiveUpdateStageRuntime, self.runtime)
        return runtime.drain_runtime_updates(max_items=max_items)

    def _start_streaming(self, input_payload: RuntimeInput) -> None:
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        self._mark_submitted()
        try:
            runtime.start_streaming(input_payload)
        except Exception:
            self._mark_failed()
            raise
        self._mark_completed()

    def _submit_stream_item(self, item: StreamItem) -> None:
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        self._mark_submitted()
        try:
            runtime.submit_stream_item(item)
        except Exception:
            self._mark_failed()
            raise
        self._mark_completed()

    def _finish_streaming(self) -> StageResult:
        runtime = cast(StreamingStageRuntime[RuntimeInput, StreamItem], self.runtime)
        self._mark_submitted()
        try:
            result = runtime.finish_streaming()
        except Exception:
            self._mark_failed()
            raise
        self._mark_completed()
        return result

    def _mark_submitted(self) -> None:
        self._submitted_count += 1
        self._in_flight_count += 1

    def _mark_completed(self) -> None:
        self._completed_count += 1
        self._in_flight_count -= 1

    def _mark_failed(self) -> None:
        self._failed_count += 1
        self._in_flight_count -= 1


@dataclass
class _BaseProxyView(BaseStageRuntime):
    proxy: StageRuntimeProxy

    def status(self) -> StageRuntimeStatus:
        """Return the proxy status."""
        return self.proxy.status()

    def stop(self) -> None:
        """Request runtime stop through the proxy."""
        self.proxy.stop()


class _OfflineProxyView(_BaseProxyView, OfflineStageRuntime[RuntimeInput]):
    def run_offline(self, input_payload: RuntimeInput) -> StageResult:
        """Invoke the proxied offline runtime."""
        return self.proxy._run_offline(input_payload)


class _LiveUpdateProxyView(_BaseProxyView, LiveUpdateStageRuntime):
    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Drain updates from the proxied runtime."""
        return self.proxy._drain_runtime_updates(max_items)


class _StreamingProxyView(_BaseProxyView, StreamingStageRuntime[RuntimeInput, StreamItem]):
    def start_streaming(self, input_payload: RuntimeInput) -> None:
        """Start the proxied streaming runtime."""
        self.proxy._start_streaming(input_payload)

    def submit_stream_item(self, item: StreamItem) -> None:
        """Submit one item to the proxied streaming runtime."""
        self.proxy._submit_stream_item(item)

    def finish_streaming(self) -> StageResult:
        """Finalize the proxied streaming runtime."""
        return self.proxy._finish_streaming()


__all__ = [
    "RuntimeCapability",
    "StageRuntimeProxy",
]
