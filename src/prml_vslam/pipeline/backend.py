"""Backend protocol for pipeline execution substrates."""

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
    """Execution backend consumed by CLI and Streamlit adapters."""

    def submit_run(self, *, request: RunRequest, runtime_source: PipelineRuntimeSource = None) -> str:
        """Submit one run and return its run id."""

    def stop_run(self, run_id: str) -> None:
        """Request one run to stop."""

    def get_snapshot(self, run_id: str) -> RunSnapshot:
        """Return the projected snapshot for one run."""

    def get_events(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        limit: int = 200,
    ) -> list[RunEvent]:
        """Return recent events for one run."""

    def read_array(self, run_id: str, handle: ArrayHandle | PreviewHandle | None) -> np.ndarray | None:
        """Resolve one array-like handle into a local NumPy array."""

    def shutdown(self) -> None:
        """Shut down backend-owned resources."""


__all__ = ["PipelineBackend", "PipelineRuntimeSource"]
