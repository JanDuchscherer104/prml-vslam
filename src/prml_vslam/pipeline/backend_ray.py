"""Ray-backed backend for plan execution and run attachment.

This module owns substrate-specific concerns that the rest of
:mod:`prml_vslam.pipeline` should not need to understand: Ray initialization,
local head lifecycle, runtime environment setup, coordinator actor discovery,
and conversion from opaque runtime handles back into local NumPy arrays.
"""

from __future__ import annotations

import os
import shutil
import time
from typing import Any

# Ray snapshots this flag at import time. Set it before importing `ray` so the
# local Streamlit/CLI path does not get rewritten back to `uv run ...`.
os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.pipeline.backend import PipelineBackend, PipelineRuntimeSource
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import coordinator_actor_name
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.ray_runtime.substrate import LocalRayHead, build_runtime_env, prepare_ray_environment
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import Console, PathConfig

_DEFAULT_NAMESPACE = "prml_vslam.local"
_MAX_LOCAL_HEAD_INIT_ATTEMPTS = 5
RayActorOption = str | float | int | dict[str, float] | None


# TODO: What is this? Must respect the respective StageConfig's ressource settings!.
def _coordinator_actor_options(run_config: RunConfig) -> dict[str, RayActorOption]:
    options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        run_config=run_config,
        default_num_cpus=1.0,
        default_num_gpus=0.0,
        restartable=False,
        inherit_backend_defaults=True,
    )
    return {key: value for key, value in options.items() if value is not None and value != {}}


class RayPipelineBackend(PipelineBackend):
    """Execute pipeline runs through detached per-run coordinator actors.

    The backend is responsible for turning a validated :class:`RunConfig` into
    a running Ray topology. The :class:`RunCoordinatorActor` remains the
    authoritative owner of one run's state; this backend only manages how the
    caller reaches that coordinator.
    """

    def __init__(self, *, path_config: PathConfig | None = None, namespace: str | None = None) -> None:
        self._path_config = PathConfig() if path_config is None else path_config
        self._namespace = namespace or os.getenv("PRML_VSLAM_RAY_NAMESPACE", _DEFAULT_NAMESPACE)
        self._console = Console(__name__).child(self.__class__.__name__).child(self._namespace)
        self._coordinators: dict[str, ActorHandle] = {}
        self._local_head = LocalRayHead(path_config=self._path_config, console=self._console)
        self._reuse_local_head = False
        self._next_coordinator_options: dict[str, Any] = {}

    def submit_run(
        self,
        *,
        run_config: RunConfig,
        runtime_source: PipelineRuntimeSource = None,
    ) -> str:
        """Build the plan, ensure Ray is available, and boot one coordinator."""
        self._reuse_local_head = run_config.ray_local_head_lifecycle == "reusable"
        self._ensure_ray()
        plan = run_config.compile_plan(self._path_config)
        unavailable = [stage for stage in plan.stages if not stage.available]
        if unavailable:
            reason = unavailable[0].availability_reason or f"Stage '{unavailable[0].key.value}' is unavailable."
            raise RuntimeError(reason)
        if plan.artifact_root.exists():
            self._console.warning("Overwriting existing run artifact root '%s'.", plan.artifact_root)
            shutil.rmtree(plan.artifact_root)
        plan.artifact_root.mkdir(parents=True, exist_ok=True)
        self._console.info(
            "Submitting run '%s' in %s mode with %d planned stages.",
            plan.run_id,
            plan.mode.value,
            len(plan.stages),
        )
        self._next_coordinator_options = _coordinator_actor_options(run_config)
        coordinator = self._create_coordinator(plan.run_id)
        coordinator.start.remote(
            run_config=run_config,
            plan=plan,
            path_config=self._path_config,
            runtime_source=runtime_source,
        )
        return plan.run_id

    def stop_run(self, run_id: str) -> None:
        """Forward a stop request to the named coordinator actor."""
        self._console.warning("Stopping run '%s' through Ray backend.", run_id)
        self._coordinator_for(run_id).stop.remote()

    def get_snapshot(self, run_id: str) -> RunSnapshot:
        """Fetch the latest projected snapshot from the coordinator actor."""
        return ray.get(self._coordinator_for(run_id).snapshot.remote())

    def get_events(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        limit: int = 200,
    ) -> list[RunEvent]:
        """Fetch trailing events from the coordinator actor."""
        return ray.get(self._coordinator_for(run_id).events.remote(after_event_id, limit))

    def read_payload(self, run_id: str, ref: TransientPayloadRef | None) -> np.ndarray | None:
        """Resolve one coordinator-owned target transient payload ref."""
        # TODO(pipeline-refactor/post-target-alignment): Return a typed
        # not-found result instead of None.
        if ref is None:
            return None
        return ray.get(self._coordinator_for(run_id).read_payload.remote(ref.handle_id))

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Detach from Ray and stop any backend-owned shared infrastructure."""
        self._console.info("Shutting down Ray backend for namespace '%s'.", self._namespace)
        if not ray.is_initialized():
            if not preserve_local_head:
                self._local_head.shutdown()
            return
        for run_id in list(self._coordinators):
            self._shutdown_run(run_id)
        ray.shutdown()
        if not preserve_local_head:
            self._local_head.shutdown()

    def _create_coordinator(self, run_id: str):
        self._shutdown_run(run_id)
        options = {"name": coordinator_actor_name(run_id), "namespace": self._namespace}
        options.update(self._next_coordinator_options)
        self._next_coordinator_options = {}
        if not self._namespace.startswith("pytest-"):
            options["lifetime"] = "detached"
        coordinator = RunCoordinatorActor.options(**options).remote(run_id=run_id, namespace=self._namespace)
        self._coordinators[run_id] = coordinator
        self._console.info("Created coordinator for run '%s' in namespace '%s'.", run_id, self._namespace)
        return coordinator

    def _coordinator_for(self, run_id: str):
        coordinator = self._coordinators.get(run_id)
        if coordinator is not None:
            return coordinator
        self._console.debug("Coordinator for run '%s' not cached locally; attempting Ray lookup.", run_id)
        self._ensure_ray()
        try:
            coordinator = ray.get_actor(coordinator_actor_name(run_id), namespace=self._namespace)
        except ValueError:
            raise RuntimeError(f"Coordinator for run '{run_id}' is not available.") from None
        self._coordinators[run_id] = coordinator
        self._console.debug("Reattached to coordinator for run '%s' via Ray lookup.", run_id)
        return coordinator

    def _shutdown_run(self, run_id: str) -> None:
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
        try:
            ray.kill(coordinator, no_restart=True)
        except Exception:
            pass
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                ray.get_actor(coordinator_actor_name(run_id), namespace=self._namespace)
            except ValueError:
                return
            time.sleep(0.1)
        raise RuntimeError(f"Timed out waiting for coordinator '{coordinator_actor_name(run_id)}' to shut down.")

    def _ensure_ray(self) -> None:
        if ray.is_initialized():
            return
        address = os.getenv("PRML_VSLAM_RAY_ADDRESS")
        prepare_ray_environment()
        init_kwargs = {
            "namespace": self._namespace,
            "ignore_reinit_error": True,
            "log_to_driver": True,  # TODO: must be exposed via RunConfig!
            "include_dashboard": False,
            "_skip_env_hook": True,
        }
        if not self._namespace.startswith("pytest-"):
            init_kwargs["runtime_env"] = build_runtime_env(address=address)
            self._console.debug("Prepared Ray runtime environment for namespace '%s'.", self._namespace)
        if address:
            self._console.info("Connecting Ray backend to configured address '%s'.", address)
            init_kwargs["address"] = address
            ray.init(**init_kwargs)
            return
        if self._namespace.startswith("pytest-"):
            self._console.debug("Initializing in-process Ray runtime for pytest namespace '%s'.", self._namespace)
            ray.init(**init_kwargs)
            return
        local_address = self._local_head.ensure_address(reuse=self._reuse_local_head)
        init_kwargs["address"] = local_address
        for attempt in range(_MAX_LOCAL_HEAD_INIT_ATTEMPTS):
            try:
                ray.init(**init_kwargs)
                return
            except Exception as exc:
                if not LocalRayHead.is_connectivity_error(exc) or attempt == _MAX_LOCAL_HEAD_INIT_ATTEMPTS - 1:
                    raise
                time.sleep(2.0)


__all__ = ["RayPipelineBackend"]
