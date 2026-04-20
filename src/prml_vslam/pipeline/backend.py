"""Backend boundary between launch surfaces and execution substrates.

This module keeps the app and CLI-facing entrypoints decoupled from the active
runtime implementation. A backend accepts a typed :class:`RunRequest`, owns run
lifecycle operations, and exposes only projected metadata and opaque live-array
handles back to the caller. It is the narrow seam between user-facing launch
code and the concrete runtime implementation such as the Ray backend.
"""

from __future__ import annotations

from typing import Protocol, TypeAlias

import numpy as np

from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource

PipelineRuntimeSource: TypeAlias = OfflineSequenceSource | StreamingSequenceSource | None


class PipelineBackend(Protocol):
    """Execute, monitor, and tear down pipeline runs.

    Implementations own the concrete execution substrate, such as Ray. Callers
    should treat this protocol as the narrow runtime boundary: submit a run,
    read projected metadata, resolve opaque array handles when needed, and
    request shutdown through the backend rather than reaching into actor or
    process internals directly.
    """

    def submit_run(self, *, request: RunRequest, runtime_source: PipelineRuntimeSource = None) -> str:
        """Start one run and return the stable run identifier.

        Args:
            request: Typed pipeline request that has not yet been submitted.
            runtime_source: Optional already-constructed source object used for
                runtime execution. Offline runs usually omit it; streaming runs
                usually supply it explicitly.

        Returns:
            Filesystem-safe run identifier used for later snapshot, event, and
            array-handle reads.
        """

    def stop_run(self, run_id: str) -> None:
        """Request graceful stop for one active run."""

    def get_snapshot(self, run_id: str) -> RunSnapshot:
        """Return the latest projected metadata view for one run."""

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

    def read_array(self, run_id: str, handle: ArrayHandle | PreviewHandle | None) -> np.ndarray | None:
        """Resolve one opaque live payload handle into a local array.

        The handle identifies transient payloads stored by the execution
        substrate. Durable stage outputs should still be consumed through
        artifact paths rather than through this method.
        """

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Release backend-owned runtime resources.

        Args:
            preserve_local_head: Whether substrate-specific shared infrastructure
                such as a reusable local Ray head should remain alive after the
                backend detaches.
        """


__all__ = ["PipelineBackend", "PipelineRuntimeSource"]
