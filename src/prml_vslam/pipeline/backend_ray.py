"""Ray-backed backend for plan execution and run attachment.

This module owns substrate-specific concerns that the rest of
:mod:`prml_vslam.pipeline` should not need to understand: Ray initialization,
local head lifecycle, runtime environment setup, coordinator actor discovery,
and conversion from opaque runtime handles back into local NumPy arrays.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Ray snapshots this flag at import time. Set it before importing `ray` so the
# local Streamlit/CLI path does not get rewritten back to `uv run ...`.
os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

import numpy as np
import ray
from ray.actor import ActorHandle

from prml_vslam.pipeline.backend import PipelineBackend, PipelineRuntimeSource
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.placement import actor_options_for_stage
from prml_vslam.pipeline.ray_runtime.common import coordinator_actor_name
from prml_vslam.pipeline.ray_runtime.coordinator import RunCoordinatorActor
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.utils import Console, PathConfig

_DEFAULT_NAMESPACE = "prml_vslam.local"
_DEFAULT_LOCAL_HEAD_PORT = 25001
_MAX_LOCAL_HEAD_INIT_ATTEMPTS = 5
_LOCAL_HEAD_METADATA_FILE = "ray-local-head.json"
_RAY_RUNTIME_EXCLUDES = [
    ".git",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".artifacts",
    ".artifacts-test",
    "external/vista-slam/media",
    "external/vista-slam/media/**",
    "external/vista-slam/DBoW3Py/DBoW3/orbvoc.dbow3",
]
_RAY_NATIVE_THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "UV_NUM_THREADS": "1",
}
RayRuntimeEnvValue = list[str] | dict[str, str] | str
RayActorOption = str | float | int | dict[str, float] | None


def _coordinator_actor_options(request: RunRequest) -> dict[str, RayActorOption]:
    options = actor_options_for_stage(
        stage_key=StageKey.SLAM,
        request=request,
        default_num_cpus=1.0,
        default_num_gpus=0.0,
        restartable=False,
        inherit_backend_defaults=True,
    )
    return {key: value for key, value in options.items() if value is not None and value != {}}


class RayPipelineBackend(PipelineBackend):
    """Execute pipeline runs through detached per-run coordinator actors.

    The backend is responsible for turning a validated :class:`RunRequest` into
    a running Ray topology. The :class:`RunCoordinatorActor` remains the
    authoritative owner of one run's state; this backend only manages how the
    caller reaches that coordinator.
    """

    def __init__(self, *, path_config: PathConfig | None = None, namespace: str | None = None) -> None:
        self._path_config = PathConfig() if path_config is None else path_config
        self._namespace = namespace or os.getenv("PRML_VSLAM_RAY_NAMESPACE", _DEFAULT_NAMESPACE)
        self._console = Console(__name__).child(self.__class__.__name__).child(self._namespace)
        self._coordinators: dict[str, ActorHandle] = {}
        self._local_head_process: subprocess.Popen[str] | None = None
        self._local_head_address: str | None = None
        self._local_head_log_path: Path | None = None
        self._reuse_local_head = False
        self._next_coordinator_options: dict[str, object] = {}

    def submit_run(self, *, request: RunRequest, runtime_source: PipelineRuntimeSource = None) -> str:
        """Build the plan, ensure Ray is available, and boot one coordinator."""
        self._reuse_local_head = request.runtime.ray.local_head_lifecycle == "reusable"
        self._ensure_ray()
        plan = request.build(self._path_config)
        unavailable = [stage for stage in plan.stages if not stage.available]
        if unavailable:
            reason = unavailable[0].availability_reason or f"Stage '{unavailable[0].key.value}' is unavailable."
            raise RuntimeError(reason)
        self._console.info(
            "Submitting run '%s' in %s mode with %d planned stages.",
            plan.run_id,
            plan.mode.value,
            len(plan.stages),
        )
        self._next_coordinator_options = _coordinator_actor_options(request)
        coordinator = self._create_coordinator(plan.run_id)
        coordinator.start.remote(
            request=request,
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

    def read_array(self, run_id: str, handle: ArrayHandle | PreviewHandle | None) -> np.ndarray | None:
        """Resolve one coordinator-owned live payload handle."""
        # TODO(pipeline-refactor/WP-10): Delete after all live payload callers
        # use read_payload(..., TransientPayloadRef).
        if handle is None:
            return None
        return ray.get(self._coordinator_for(run_id).read_array.remote(handle.handle_id))

    def read_payload(self, run_id: str, ref: TransientPayloadRef | None) -> np.ndarray | None:
        """Resolve one coordinator-owned target transient payload ref."""
        # TODO(pipeline-refactor/WP-08): Return a typed not-found result
        # instead of None once payload resolver contracts land.
        if ref is None:
            return None
        return ray.get(self._coordinator_for(run_id).read_payload.remote(ref.handle_id))

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Detach from Ray and stop any backend-owned shared infrastructure."""
        self._console.info("Shutting down Ray backend for namespace '%s'.", self._namespace)
        if not ray.is_initialized():
            if not preserve_local_head:
                self._shutdown_local_head()
            return
        for run_id in list(self._coordinators):
            self._shutdown_run(run_id)
        ray.shutdown()
        if not preserve_local_head:
            self._shutdown_local_head()

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
        self._prepare_ray_environment()
        init_kwargs = {
            "namespace": self._namespace,
            "ignore_reinit_error": True,
            "log_to_driver": True,
            "include_dashboard": False,
            "_skip_env_hook": True,
        }
        if not self._namespace.startswith("pytest-"):
            init_kwargs["runtime_env"] = self._build_runtime_env(address=address)
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
        local_address = self._ensure_local_head_address()
        init_kwargs["address"] = local_address
        for attempt in range(_MAX_LOCAL_HEAD_INIT_ATTEMPTS):
            try:
                ray.init(**init_kwargs)
                return
            except Exception as exc:
                if not self._is_local_ray_connectivity_error(exc) or attempt == _MAX_LOCAL_HEAD_INIT_ATTEMPTS - 1:
                    raise
                time.sleep(2.0)

    @staticmethod
    def _build_runtime_env(*, address: str | None) -> dict[str, RayRuntimeEnvValue]:
        """Build the process-wide Ray runtime environment for this backend."""
        runtime_env: dict[str, RayRuntimeEnvValue] = {
            "excludes": _RAY_RUNTIME_EXCLUDES,
            "env_vars": dict(_RAY_NATIVE_THREAD_ENV),
        }
        if not address:
            runtime_env["py_executable"] = sys.executable
        return runtime_env

    @staticmethod
    def _prepare_ray_environment() -> None:
        """Set environment flags that Ray snapshots at import and init time."""
        os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

    def _ensure_local_head_address(self) -> str:
        if (
            self._local_head_process is not None
            and self._local_head_process.poll() is None
            and self._local_head_address is not None
        ):
            return self._local_head_address
        if self._reuse_local_head:
            reused_address = self._reuse_local_head_address_if_available()
            if reused_address is not None:
                self._local_head_address = reused_address
                self._console.debug("Reusing healthy local Ray head at '%s'.", reused_address)
                return reused_address
        ray_bin = str(Path(sys.executable).with_name("ray"))
        if not self._reuse_local_head:
            subprocess.run(
                [ray_bin, "stop", "--force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            time.sleep(1.0)
        address = self._pick_local_head_address()
        self._console.info("Starting local Ray head on '%s'.", address)
        logs_dir = self._path_config.resolve_logs_dir(create=True)
        self._local_head_log_path = logs_dir / "ray-local-head.log"
        log_handle = self._local_head_log_path.open("a", encoding="utf-8")
        try:
            self._local_head_process = subprocess.Popen(
                [
                    ray_bin,
                    "start",
                    "--head",
                    f"--node-ip-address={address.rsplit(':', maxsplit=1)[0]}",
                    f"--port={address.rsplit(':', maxsplit=1)[1]}",
                    "--include-dashboard=false",
                    "--disable-usage-stats",
                    "--block",
                ],
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
        finally:
            log_handle.close()
        if self._wait_until_connectable(address):
            self._local_head_address = address
            self._write_local_head_metadata(address=address, pid=self._local_head_process.pid)
            return address
        if self._local_head_process.poll() is not None:
            raise RuntimeError(self._read_local_head_log())
        raise RuntimeError(f"Timed out waiting for local Ray head at {address}.\n{self._read_local_head_log()}")

    @staticmethod
    def _can_connect(address: str) -> bool:
        host, port = address.rsplit(":", maxsplit=1)
        try:
            with socket.create_connection((host, int(port)), timeout=1.0):
                return True
        except OSError:
            return False

    def _wait_until_connectable(self, address: str, *, timeout_seconds: float = 60.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self._can_connect(address):
                return True
            if self._local_head_process is not None and self._local_head_process.poll() is not None:
                return False
            time.sleep(0.25)
        return self._can_connect(address)

    def _shutdown_local_head(self) -> None:
        metadata = self._read_local_head_metadata()
        self._clear_local_head_metadata()
        if self._local_head_process is not None and self._local_head_process.poll() is None:
            self._local_head_process.terminate()
            try:
                self._local_head_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._local_head_process.kill()
                self._local_head_process.wait(timeout=5.0)
        elif self._local_head_address is not None or metadata is not None:
            ray_bin = str(Path(sys.executable).with_name("ray"))
            subprocess.run(
                [ray_bin, "stop", "--force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        self._local_head_process = None
        self._local_head_address = None

    def _local_head_metadata_path(self) -> Path:
        return self._path_config.resolve_logs_dir(create=True) / _LOCAL_HEAD_METADATA_FILE

    def _read_local_head_metadata(self) -> dict[str, str | int] | None:
        path = self._local_head_metadata_path()
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        address = payload.get("address")
        pid = payload.get("pid")
        if not isinstance(address, str) or not isinstance(pid, int):
            return None
        return {"address": address, "pid": pid}

    def _write_local_head_metadata(self, *, address: str, pid: int) -> None:
        self._local_head_metadata_path().write_text(
            json.dumps({"address": address, "pid": pid}, indent=2),
            encoding="utf-8",
        )

    def _clear_local_head_metadata(self) -> None:
        try:
            self._local_head_metadata_path().unlink(missing_ok=True)
        except OSError:
            pass

    def _reuse_local_head_address_if_available(self) -> str | None:
        metadata = self._read_local_head_metadata()
        if metadata is None:
            return None
        address = metadata["address"]
        if isinstance(address, str) and self._can_connect(address):
            self._console.debug("Found reusable local Ray head metadata for '%s'.", address)
            return address
        self._console.debug("Discarding stale local Ray head metadata.")
        self._clear_local_head_metadata()
        return None

    def _read_local_head_log(self) -> str:
        if self._local_head_log_path is None or not self._local_head_log_path.exists():
            return ""
        try:
            lines = self._local_head_log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        return "\n".join(lines[-80:])

    @staticmethod
    def _local_node_ip_address() -> str:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return str(probe.getsockname()[0])
        except OSError:
            return "127.0.0.1"
        finally:
            probe.close()

    def _pick_local_head_address(self) -> str:
        host = self._local_node_ip_address()
        for _ in range(32):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                candidate.bind((host, 0))
                port = int(candidate.getsockname()[1])
            if port >= _DEFAULT_LOCAL_HEAD_PORT:
                return f"{host}:{port}"
        return f"{host}:{_DEFAULT_LOCAL_HEAD_PORT}"

    @staticmethod
    def _is_local_ray_connectivity_error(exc: Exception) -> bool:
        message = str(exc)
        return "Failed to connect to Ray cluster" in message or "GCS" in message


__all__ = ["RayPipelineBackend"]
