"""Ray-backed stage runtime handles.

The generic stage runtime protocols are intentionally synchronous and
deployment-neutral. ``RayStageRuntimeHandle`` is the narrow substrate adapter
used when a stage runtime already lives inside a Ray actor but the coordinator
still wants the same high-level lifecycle methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.interfaces import Observation
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import BaseData, JsonScalar

RuntimeInput = BaseData
StreamItem = BaseData | Observation


@dataclass
class RayStageRuntimeHandle:
    """Proxy one Ray-hosted stage runtime through the local runtime surface."""

    stage_key: StageKey
    actor: ActorHandle
    executor_id: str | None = "ray"
    resource_assignment: dict[str, JsonScalar] = field(default_factory=dict)
    _submitted_count: int = 0
    _completed_count: int = 0
    _failed_count: int = 0
    _in_flight_count: int = 0

    def status(self) -> StageRuntimeStatus:
        """Return wrapped actor status with proxy-owned counters."""
        status = cast(StageRuntimeStatus, ray.get(self.actor.status.remote()))
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
        """Request actor runtime stop."""
        ray.get(self.actor.stop.remote())

    def run_offline(self, input_payload: RuntimeInput) -> StageResult:
        """Run the actor runtime over one bounded input payload."""
        return self._counted_result(self.actor.run_offline.remote(input_payload))

    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Drain live updates from the actor runtime."""
        return ray.get(self.actor.drain_runtime_updates.remote(max_items=max_items))

    def start_streaming(self, input_payload: RuntimeInput) -> None:
        """Start the actor runtime's streaming session."""
        self._counted_void(self.actor.start_streaming.remote(input_payload))

    def submit_stream_item(self, item: StreamItem) -> None:
        """Submit one stream item synchronously."""
        ref = self.submit_stream_item_async(item)
        try:
            ray.get(ref)
        except Exception:
            self.mark_async_item_failed()
            raise
        self.mark_async_item_completed()

    def submit_stream_item_async(self, item: StreamItem) -> ray.ObjectRef[None]:
        """Submit one stream item and return its Ray completion ref."""
        self._submitted_count += 1
        self._in_flight_count += 1
        return self.actor.submit_stream_item.remote(item)

    def mark_async_item_completed(self) -> None:
        """Record successful completion for a previously returned async ref."""
        self._completed_count += 1
        self._in_flight_count = max(0, self._in_flight_count - 1)

    def mark_async_item_failed(self) -> None:
        """Record failed completion for a previously returned async ref."""
        self._failed_count += 1
        self._in_flight_count = max(0, self._in_flight_count - 1)

    def finish_streaming(self) -> StageResult:
        """Finalize streaming execution and return the actor runtime result."""
        return self._counted_result(self.actor.finish_streaming.remote())

    def read_payload(self, ref: TransientPayloadRef) -> np.ndarray | None:
        """Resolve one actor-owned transient payload by ref."""
        payload = cast(np.ndarray | None, ray.get(self.actor.read_payload.remote(ref)))
        return None if payload is None else np.asarray(payload)

    def read_payload_by_id(self, handle_id: str) -> np.ndarray | None:
        """Resolve one actor-owned transient payload by handle id."""
        payload = cast(np.ndarray | None, ray.get(self.actor.read_payload_by_id.remote(handle_id)))
        return None if payload is None else np.asarray(payload)

    def _counted_result(self, ref: ray.ObjectRef[StageResult]) -> StageResult:
        self._submitted_count += 1
        self._in_flight_count += 1
        try:
            result: StageResult = ray.get(ref)
        except Exception:
            self._failed_count += 1
            self._in_flight_count = max(0, self._in_flight_count - 1)
            raise
        self._completed_count += 1
        self._in_flight_count = max(0, self._in_flight_count - 1)
        return result

    def _counted_void(self, ref: ray.ObjectRef[None]) -> None:
        self._submitted_count += 1
        self._in_flight_count += 1
        try:
            ray.get(ref)
        except Exception:
            self._failed_count += 1
            self._in_flight_count = max(0, self._in_flight_count - 1)
            raise
        self._completed_count += 1
        self._in_flight_count = max(0, self._in_flight_count - 1)


__all__ = ["RayStageRuntimeHandle"]
