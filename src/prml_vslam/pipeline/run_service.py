"""Thin launch-surface façade over the active pipeline backend.

This module contains the small service object that app pages and CLI commands
use instead of depending directly on the Ray backend. It intentionally keeps
only the currently active run id and forwards lifecycle operations into a
:class:`PipelineBackend`, making it the main app/CLI click-through entry point
into runtime orchestration.
"""

from __future__ import annotations

import numpy as np

from prml_vslam.pipeline.backend import PipelineBackend, PipelineRuntimeSource
from prml_vslam.pipeline.backend_ray import RayPipelineBackend
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import PathConfig


class RunService:
    """Start and inspect at most one active run from app or CLI code.

    The service lazily constructs :class:`RayPipelineBackend` by default, but it
    also accepts an injected :class:`PipelineBackend` for tests or alternate
    substrates.
    """

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        backend: PipelineBackend | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self._backend = backend
        self._run_id: str | None = None

    def start_run(self, *, request: RunRequest, runtime_source: PipelineRuntimeSource = None) -> None:
        """Start one run and replace any previously tracked active run."""
        if self._run_id is not None:
            self.stop_run()
        self._run_id = self._require_backend().submit_run(request=request, runtime_source=runtime_source)

    def stop_run(self) -> None:
        """Request stop for the currently tracked run, if one exists."""
        if self._run_id is None:
            return
        self._require_backend().stop_run(self._run_id)

    def snapshot(self) -> RunSnapshot:
        """Return the latest projected snapshot for the active run.

        Returns an empty :class:`RunSnapshot` when the service is idle.
        """
        if self._run_id is None:
            return RunSnapshot()
        return self._require_backend().get_snapshot(self._run_id)

    def tail_events(self, *, after_event_id: str | None = None, limit: int = 200) -> list[RunEvent]:
        """Return trailing events for the active run.

        Args:
            after_event_id: Optional cursor for incremental polling.
            limit: Maximum number of events to return.
        """
        if self._run_id is None:
            return []
        return self._require_backend().get_events(self._run_id, after_event_id=after_event_id, limit=limit)

    def read_payload(self, ref: TransientPayloadRef | None) -> np.ndarray | None:
        """Resolve one active-run transient payload ref into a local NumPy array."""
        # TODO(pipeline-refactor/WP-08): Return a typed not-found result
        # instead of None once payload resolver contracts land.
        if self._run_id is None:
            return None
        return self._require_backend().read_payload(self._run_id, ref)

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Shut down the backing runtime if one has been created."""
        if self._backend is None:
            return
        self._backend.shutdown(preserve_local_head=preserve_local_head)

    def _require_backend(self) -> PipelineBackend:
        if self._backend is None:
            self._backend = RayPipelineBackend(path_config=self.path_config)
        return self._backend


__all__ = ["RunService"]
