"""Ray substrate bootstrap helpers for the pipeline backend."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from prml_vslam.utils import Console, PathConfig

_DEFAULT_LOCAL_HEAD_PORT = 25001
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


def prepare_ray_environment() -> None:
    """Set environment flags that Ray snapshots at import and init time."""
    os.environ.setdefault("RAY_ENABLE_UV_RUN_RUNTIME_ENV", "0")


def build_runtime_env(*, address: str | None) -> dict[str, RayRuntimeEnvValue]:
    """Build the process-wide Ray runtime environment for this backend."""
    runtime_env: dict[str, RayRuntimeEnvValue] = {
        "excludes": _RAY_RUNTIME_EXCLUDES,
        "env_vars": dict(_RAY_NATIVE_THREAD_ENV),
    }
    if not address:
        runtime_env["py_executable"] = sys.executable
    return runtime_env


class LocalRayHead:
    """Own a backend-managed local Ray head process and its reuse metadata."""

    def __init__(self, *, path_config: PathConfig, console: Console) -> None:
        self._path_config = path_config
        self._console = console
        self._process: subprocess.Popen[str] | None = None
        self._address: str | None = None
        self._log_path: Path | None = None

    def ensure_address(self, *, reuse: bool) -> str:
        """Return a connectable local Ray head address, starting one if needed."""
        if self._process is not None and self._process.poll() is None and self._address is not None:
            return self._address
        if reuse:
            reused_address = self._reuse_address_if_available()
            if reused_address is not None:
                self._address = reused_address
                self._console.debug("Reusing healthy local Ray head at '%s'.", reused_address)
                return reused_address
        ray_bin = str(Path(sys.executable).with_name("ray"))
        if not reuse:
            subprocess.run(
                [ray_bin, "stop", "--force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            time.sleep(1.0)
        address = self._pick_address()
        self._console.info("Starting local Ray head on '%s'.", address)
        logs_dir = self._path_config.resolve_logs_dir(create=True)
        self._log_path = logs_dir / "ray-local-head.log"
        log_handle = self._log_path.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
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
            self._address = address
            self._write_metadata(address=address, pid=self._process.pid)
            return address
        if self._process.poll() is not None:
            raise RuntimeError(self._read_log())
        raise RuntimeError(f"Timed out waiting for local Ray head at {address}.\n{self._read_log()}")

    def shutdown(self) -> None:
        """Stop any local Ray head owned or tracked by this backend."""
        metadata = self._read_metadata()
        self._clear_metadata()
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5.0)
        elif self._address is not None or metadata is not None:
            ray_bin = str(Path(sys.executable).with_name("ray"))
            subprocess.run(
                [ray_bin, "stop", "--force"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        self._process = None
        self._address = None

    @staticmethod
    def is_connectivity_error(exc: Exception) -> bool:
        """Return whether ``exc`` looks like a transient local Ray connection failure."""
        message = str(exc)
        return "Failed to connect to Ray cluster" in message or "GCS" in message

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
            if self._process is not None and self._process.poll() is not None:
                return False
            time.sleep(0.25)
        return self._can_connect(address)

    def _metadata_path(self) -> Path:
        return self._path_config.resolve_logs_dir(create=True) / _LOCAL_HEAD_METADATA_FILE

    def _read_metadata(self) -> dict[str, str | int] | None:
        path = self._metadata_path()
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

    def _write_metadata(self, *, address: str, pid: int) -> None:
        self._metadata_path().write_text(
            json.dumps({"address": address, "pid": pid}, indent=2),
            encoding="utf-8",
        )

    def _clear_metadata(self) -> None:
        try:
            self._metadata_path().unlink(missing_ok=True)
        except OSError:
            pass

    def _reuse_address_if_available(self) -> str | None:
        metadata = self._read_metadata()
        if metadata is None:
            return None
        address = metadata["address"]
        if isinstance(address, str) and self._can_connect(address):
            self._console.debug("Found reusable local Ray head metadata for '%s'.", address)
            return address
        self._console.debug("Discarding stale local Ray head metadata.")
        self._clear_metadata()
        return None

    def _read_log(self) -> str:
        if self._log_path is None or not self._log_path.exists():
            return ""
        try:
            lines = self._log_path.read_text(encoding="utf-8").splitlines()
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

    def _pick_address(self) -> str:
        host = self._local_node_ip_address()
        for _ in range(32):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                candidate.bind((host, 0))
                port = int(candidate.getsockname()[1])
            if port >= _DEFAULT_LOCAL_HEAD_PORT:
                return f"{host}:{port}"
        return f"{host}:{_DEFAULT_LOCAL_HEAD_PORT}"


__all__ = ["LocalRayHead", "RayRuntimeEnvValue", "build_runtime_env", "prepare_ray_environment"]
