"""Generic runtime capability protocols for pipeline stages.

These protocols describe the target stage-runtime capability surface without
choosing an in-process or Ray-backed deployment. Concrete runtimes and proxies
are introduced by later work packages.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.stages.base.contracts import StageResult, StageRuntimeStatus, StageRuntimeUpdate
from prml_vslam.utils import BaseData

TOfflineInput = TypeVar("TOfflineInput", bound=BaseData)
TStreamingInput = TypeVar("TStreamingInput", bound=BaseData)
TStreamItem = TypeVar("TStreamItem", bound=BaseData | FramePacket)


@runtime_checkable
class BaseStageRuntime(Protocol):
    """Common lifecycle surface implemented by every stage runtime."""

    @abstractmethod
    def status(self) -> StageRuntimeStatus:
        """Return the latest queryable runtime status."""

    @abstractmethod
    def stop(self) -> None:
        """Request runtime shutdown or cancellation."""


@runtime_checkable
class OfflineStageRuntime(BaseStageRuntime, Protocol[TOfflineInput]):
    """Capability surface for bounded or batch-like stage execution."""

    @abstractmethod
    def run_offline(self, input_payload: TOfflineInput) -> StageResult:
        """Run the stage over one bounded input payload."""


@runtime_checkable
class LiveUpdateStageRuntime(BaseStageRuntime, Protocol):
    """Capability surface for runtimes that emit live observer updates."""

    @abstractmethod
    def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
        """Return pending live updates without blocking for new work."""


@runtime_checkable
class StreamingStageRuntime(BaseStageRuntime, Protocol[TStreamingInput, TStreamItem]):
    """Capability surface for active runtimes that accept stream items."""

    @abstractmethod
    def start_streaming(self, input_payload: TStreamingInput) -> None:
        """Start the streaming runtime with its run-scoped input payload."""

    @abstractmethod
    def submit_stream_item(self, item: TStreamItem) -> None:
        """Submit one hot-path stream item to the runtime."""

    @abstractmethod
    def finish_streaming(self) -> StageResult:
        """Finalize streaming execution and return the terminal stage result."""


__all__ = [
    "BaseStageRuntime",
    "LiveUpdateStageRuntime",
    "OfflineStageRuntime",
    "StreamingStageRuntime",
]
