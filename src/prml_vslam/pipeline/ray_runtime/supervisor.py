"""Ray supervisor actor that owns run coordinators."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import ray

from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.ray_runtime.common import coordinator_actor_name
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.utils import PathConfig


@ray.remote(num_cpus=1, max_restarts=-1, max_task_retries=1)
class PipelineSupervisorActor:
    """Deployment-level root actor that owns run coordinators."""

    def __init__(self, *, namespace: str) -> None:
        self._namespace = namespace
        self._coordinators: dict[str, Any] = {}

    def submit_run(
        self,
        *,
        request: RunRequest,
        plan: RunPlan,
        path_config: PathConfig,
        runtime_source: object | None = None,
    ) -> str:
        run_id = plan.run_id
        self.shutdown_run(run_id)
        coordinator = RunCoordinatorActor.options(
            name=coordinator_actor_name(run_id),
            namespace=self._namespace,
        ).remote(run_id=run_id, namespace=self._namespace)
        self._coordinators[run_id] = coordinator
        coordinator.start.remote(request=request, plan=plan, path_config=path_config, runtime_source=runtime_source)
        return run_id

    def stop_run(self, run_id: str) -> None:
        self._coordinator_for(run_id).stop.remote()

    def get_snapshot(self, run_id: str) -> RunSnapshot:
        return ray.get(self._coordinator_for(run_id).snapshot.remote())

    def get_events(self, run_id: str, after_event_id: str | None = None, limit: int = 200) -> list[object]:
        return ray.get(self._coordinator_for(run_id).events.remote(after_event_id, limit))

    def read_array(self, run_id: str, handle_id: str) -> np.ndarray | None:
        return ray.get(self._coordinator_for(run_id).read_array.remote(handle_id))

    def shutdown_run(self, run_id: str) -> None:
        coordinator = self._coordinators.pop(run_id, None)
        if coordinator is None:
            try:
                coordinator = ray.get_actor(coordinator_actor_name(run_id), namespace=self._namespace)
            except ValueError:
                return
        try:
            coordinator.shutdown.remote()
        except Exception:
            pass
        ray.kill(coordinator, no_restart=True)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                ray.get_actor(coordinator_actor_name(run_id), namespace=self._namespace)
            except ValueError:
                return
            time.sleep(0.1)
        raise RuntimeError(f"Timed out waiting for coordinator '{coordinator_actor_name(run_id)}' to shut down.")

    def shutdown(self) -> None:
        for run_id in list(self._coordinators):
            self.shutdown_run(run_id)

    def _coordinator_for(self, run_id: str):
        coordinator = self._coordinators.get(run_id)
        if coordinator is not None:
            return coordinator
        coordinator = ray.get_actor(coordinator_actor_name(run_id), namespace=self._namespace)
        self._coordinators[run_id] = coordinator
        return coordinator


__all__ = ["PipelineSupervisorActor"]
