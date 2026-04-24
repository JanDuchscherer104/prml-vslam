"""Backend boundary between launch surfaces and execution substrates.

This module keeps the app and CLI-facing entrypoints decoupled from the active
runtime implementation. A backend accepts a typed :class:`RunConfig`, owns run
lifecycle operations, and exposes only projected metadata and transient payload
refs back to the caller. It is the narrow seam between user-facing launch code
and the concrete runtime implementation such as the Ray backend.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, TypeAlias

import numpy as np

from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource

PipelineRuntimeSource: TypeAlias = OfflineSequenceSource | StreamingSequenceSource | None


# TODO(pipeline-refactor/WP-03): Move this behavior seam to pipeline/protocols.py
# when backend implementations are separated from public protocols.
class PipelineBackend(Protocol):
    """Execute, monitor, and tear down pipeline runs.

    Implementations own the concrete execution substrate, such as Ray. Callers
    should treat this protocol as the narrow runtime boundary: submit a run,
    read projected metadata, resolve transient payload refs when needed, and
    request shutdown through the backend rather than reaching into actor or
    process internals directly.
    """

    @abstractmethod
    def submit_run(self, *, run_config: RunConfig, runtime_source: PipelineRuntimeSource = None) -> str:
        """Start one run and return the stable run identifier.

        Args:
            run_config: Typed pipeline run config that has not yet been submitted.
            runtime_source: Optional already-constructed source object used for
                runtime execution. Offline runs usually omit it; streaming runs
                usually supply it explicitly.

        Returns:
            Filesystem-safe run identifier used for later snapshot, event, and
            payload-ref reads.
        """

    @abstractmethod
    def stop_run(self, run_id: str) -> None:
        """Request graceful stop for one active run."""

    @abstractmethod
    def get_snapshot(self, run_id: str) -> RunSnapshot:
        """Return the latest projected metadata view for one run."""

    @abstractmethod
    def get_events(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        limit: int = 200,
    ) -> list[RunEvent]:
        """Return recent runtime events for one run.

        Args:
            run_id: Stable run identifier returned by :meth:`submit_run`.
            after_event_id: Optional cursor for incremental tails.
            limit: Maximum number of trailing events to return.
        """

    @abstractmethod
    def read_payload(self, run_id: str, ref: TransientPayloadRef | None) -> np.ndarray | None:
        """Resolve one target transient payload ref into a local array."""
        # TODO(pipeline-refactor/post-target-alignment): Replace the nullable
        # return with a typed payload-resolution result.

    @abstractmethod
    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Release backend-owned runtime resources.

        Args:
            preserve_local_head: Whether substrate-specific shared infrastructure
                such as a reusable local Ray head should remain alive after the
                backend detaches.
        """


__all__ = ["PipelineBackend", "PipelineRuntimeSource"]
