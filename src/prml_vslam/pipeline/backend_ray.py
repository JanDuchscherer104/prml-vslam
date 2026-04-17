"""Ray-backed pipeline execution backend."""

from __future__ import annotations

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

from prml_vslam.pipeline.backend import PipelineBackend
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.runtime import RunSnapshot
from prml_vslam.pipeline.ray_runtime import PipelineSupervisorActor
from prml_vslam.pipeline.services import RunPlannerService
from prml_vslam.utils import Console, PathConfig

_DEFAULT_NAMESPACE = "prml_vslam.local"
_DEFAULT_LOCAL_HEAD_PORT = 25001
_MAX_LOCAL_HEAD_INIT_ATTEMPTS = 5
_SUPERVISOR_NAME = "prml-vslam-supervisor"
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


class RayPipelineBackend(PipelineBackend):
    """Ray-backed execution substrate for the pipeline."""

    def __init__(self, *, path_config: PathConfig | None = None, namespace: str | None = None) -> None:
        self._path_config = PathConfig() if path_config is None else path_config
        self._namespace = namespace or os.getenv("PRML_VSLAM_RAY_NAMESPACE", _DEFAULT_NAMESPACE)
        self._console = Console(__name__).child(self.__class__.__name__).child(self._namespace)
        self._supervisor = None
        self._local_head_process: subprocess.Popen[str] | None = None
        self._local_head_address: str | None = None
        self._local_head_log_path: Path | None = None

    def submit_run(self, *, request: RunRequest, runtime_source: object | None = None) -> str:
        self._ensure_ray()
        supervisor = self._ensure_supervisor()
        plan = RunPlannerService().build_run_plan(request=request, path_config=self._path_config)
        unavailable = [stage for stage in plan.stages if not stage.available]
        if unavailable:
            reason = unavailable[0].availability_reason or f"Stage '{unavailable[0].key.value}' is unavailable."
            raise RuntimeError(reason)
        self._console.info("Submitting run '%s' through Ray backend.", plan.run_id)
        run_id = ray.get(
            supervisor.submit_run.remote(
                request=request,
                plan=plan,
                path_config=self._path_config,
                runtime_source=runtime_source,
            )
        )
        return run_id

    def stop_run(self, run_id: str) -> None:
        self._console.warning("Stopping run '%s' through Ray backend.", run_id)
        self._ensure_supervisor().stop_run.remote(run_id)

    def get_snapshot(self, run_id: str) -> RunSnapshot:
        return ray.get(self._ensure_supervisor().get_snapshot.remote(run_id))

    def get_events(
        self,
        run_id: str,
        *,
        after_event_id: str | None = None,
        limit: int = 200,
    ) -> list[RunEvent]:
        return ray.get(self._ensure_supervisor().get_events.remote(run_id, after_event_id, limit))

    def read_array(self, run_id: str, handle: ArrayHandle | PreviewHandle | None) -> np.ndarray | None:
        if handle is None:
            return None
        return ray.get(self._ensure_supervisor().read_array.remote(run_id, handle.handle_id))

    def shutdown(self) -> None:
        self._console.info("Shutting down Ray backend for namespace '%s'.", self._namespace)
        if not ray.is_initialized():
            self._shutdown_local_head()
            return
        if self._supervisor is not None:
            try:
                self._supervisor.shutdown.remote()
            except Exception:
                pass
            try:
                ray.kill(self._supervisor, no_restart=True)
            except Exception:
                pass
        ray.shutdown()
        self._shutdown_local_head()

    def _ensure_supervisor(self):
        if self._supervisor is not None:
            return self._supervisor
        self._ensure_ray()
        if self._should_refresh_local_supervisor():
            self._drop_existing_supervisor()
        try:
            self._supervisor = ray.get_actor(_SUPERVISOR_NAME, namespace=self._namespace)
        except ValueError:
            options = {"name": _SUPERVISOR_NAME, "namespace": self._namespace}
            if not self._namespace.startswith("pytest-"):
                options["lifetime"] = "detached"
            self._supervisor = PipelineSupervisorActor.options(**options).remote(namespace=self._namespace)
            self._console.info("Created supervisor '%s' in namespace '%s'.", _SUPERVISOR_NAME, self._namespace)
        return self._supervisor

    def _ensure_ray(self) -> None:
        if ray.is_initialized():
            return
        address = os.getenv("PRML_VSLAM_RAY_ADDRESS")
        self._prepare_ray_environment()
        init_kwargs = {
            "namespace": self._namespace,
            "ignore_reinit_error": True,
            "log_to_driver": False,
            "include_dashboard": False,
            "runtime_env": self._build_runtime_env(address=address),
            "_skip_env_hook": True,
        }
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
    def _build_runtime_env(*, address: str | None) -> dict[str, object]:
        runtime_env: dict[str, object] = {"excludes": _RAY_RUNTIME_EXCLUDES}
        if not address:
            runtime_env["py_executable"] = sys.executable
        return runtime_env

    @staticmethod
    def _prepare_ray_environment() -> None:
        os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")

    def _ensure_local_head_address(self) -> str:
        if (
            self._local_head_process is not None
            and self._local_head_process.poll() is None
            and self._local_head_address is not None
        ):
            return self._local_head_address
        ray_bin = str(Path(sys.executable).with_name("ray"))
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
        if self._wait_until_connectable(address):
            self._local_head_address = address
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
        if self._local_head_process is None:
            return
        if self._local_head_process.poll() is None:
            self._local_head_process.terminate()
            try:
                self._local_head_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._local_head_process.kill()
                self._local_head_process.wait(timeout=5.0)
        self._local_head_process = None
        self._local_head_address = None

    def _read_local_head_log(self) -> str:
        if self._local_head_log_path is None or not self._local_head_log_path.exists():
            return ""
        try:
            lines = self._local_head_log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        return "\n".join(lines[-80:])

    def _should_refresh_local_supervisor(self) -> bool:
        return os.getenv("PRML_VSLAM_RAY_ADDRESS") is None and not self._namespace.startswith("pytest-")

    def _drop_existing_supervisor(self) -> None:
        try:
            supervisor = ray.get_actor(_SUPERVISOR_NAME, namespace=self._namespace)
        except ValueError:
            return
        ray.kill(supervisor, no_restart=True)
        deadline = time.time() + 5.0
        while time.time() < deadline:
            try:
                ray.get_actor(_SUPERVISOR_NAME, namespace=self._namespace)
            except ValueError:
                return
            time.sleep(0.1)
        raise RuntimeError(f"Timed out waiting for supervisor '{_SUPERVISOR_NAME}' to shut down.")

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
