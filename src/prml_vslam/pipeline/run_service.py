"""Thin façade over the active pipeline backend."""

from __future__ import annotations

import numpy as np

from prml_vslam.pipeline.backend import PipelineBackend
from prml_vslam.pipeline.backend_ray import RayPipelineBackend
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.utils import PathConfig


class RunService:
    """App-facing and CLI-facing adapter over `PipelineBackend`."""

    def __init__(
        self,
        *,
        path_config: PathConfig | None = None,
        backend: PipelineBackend | None = None,
    ) -> None:
        self.path_config = PathConfig() if path_config is None else path_config
        self._backend = backend
        self._run_id: str | None = None

    def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
        if self._run_id is not None:
            self.stop_run()
        self._run_id = self._require_backend().submit_run(request=request, runtime_source=runtime_source)

    def stop_run(self) -> None:
        if self._run_id is None:
            return
        self._require_backend().stop_run(self._run_id)

    def snapshot(self) -> RunSnapshot:
        if self._run_id is None:
            return RunSnapshot()
        return self._require_backend().get_snapshot(self._run_id)

    def tail_events(self, *, after_event_id: str | None = None, limit: int = 200) -> list[RunEvent]:
        if self._run_id is None:
            return []
        return self._require_backend().get_events(self._run_id, after_event_id=after_event_id, limit=limit)

    def read_array(self, handle: ArrayHandle | PreviewHandle | None) -> np.ndarray | None:
        if self._run_id is None:
            return None
        return self._require_backend().read_array(self._run_id, handle)

    def shutdown(self) -> None:
        if self._backend is None:
            return
        self._backend.shutdown()

    def _require_backend(self) -> PipelineBackend:
        if self._backend is None:
            self._backend = RayPipelineBackend(path_config=self.path_config)
        return self._backend


__all__ = ["RunService"]
