"""Local path bookkeeping for the repository-owned method mocks."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from prml_vslam.methods.interfaces import MethodId
from prml_vslam.utils import PathConfig, get_path_config

ENVIRONMENT_READY_MARKER = ".prml_vslam_sync_complete"


@dataclass(frozen=True)
class MethodInstallSpec:
    """Static local install metadata for one mock backend."""

    method: MethodId
    extra_name: str
    repo_name: str
    repo_checkpoint_dirname: str
    checkpoint_dirname: str


METHOD_INSTALL_SPECS: dict[MethodId, MethodInstallSpec] = {
    MethodId.VISTA: MethodInstallSpec(
        method=MethodId.VISTA,
        extra_name="vista",
        repo_name="vista-slam",
        repo_checkpoint_dirname="pretrains",
        checkpoint_dirname="vista",
    ),
    MethodId.MSTR: MethodInstallSpec(
        method=MethodId.MSTR,
        extra_name="mstr",
        repo_name="MASt3R-SLAM",
        repo_checkpoint_dirname="checkpoints",
        checkpoint_dirname="mstr",
    ),
}


class MethodInstallationService:
    """Expose deterministic local paths for the repository-local method mocks."""

    def __init__(self, path_config: PathConfig | None = None) -> None:
        self.path_config = path_config or get_path_config()

    def get_spec(self, method: MethodId) -> MethodInstallSpec:
        """Return the local metadata for a mock backend."""
        return METHOD_INSTALL_SPECS[method]

    def get_repo_path(self, method: MethodId) -> Path:
        """Return the mock checkout directory for a backend."""
        return self.path_config.resolve_method_repo_dir(self.get_spec(method).repo_name)

    def get_checkpoint_dir(self, method: MethodId) -> Path:
        """Return the shared checkpoint directory for a backend."""
        return self.path_config.resolve_checkpoint_dir(self.get_spec(method).checkpoint_dirname)

    def get_environment_dir(self, method: MethodId) -> Path:
        """Return the dedicated environment directory for a backend."""
        return self.path_config.resolve_method_env_dir(self.get_spec(method).extra_name)

    def get_python_executable(self, method: MethodId) -> Path:
        """Return the mock Python executable path inside the dedicated environment."""
        env_dir = self.get_environment_dir(method)
        executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        return (env_dir / executable).resolve()

    def get_environment_ready_marker(self, method: MethodId) -> Path:
        """Return the ready-marker path for a backend environment."""
        return (self.get_environment_dir(method) / ENVIRONMENT_READY_MARKER).resolve()

    def is_environment_ready(self, method: MethodId) -> bool:
        """Return whether the environment marker and executable are present."""
        return self.get_environment_ready_marker(method).exists() and self.get_python_executable(method).exists()

    def ensure_repo_checkout(self, method: MethodId) -> Path:
        """Create the mock repo directory when needed."""
        repo_path = self.get_repo_path(method)
        repo_path.mkdir(parents=True, exist_ok=True)
        return repo_path.resolve()

    def ensure_shared_checkpoint_link(self, method: MethodId) -> Path:
        """Link the repo-local checkpoint directory to the shared checkpoint folder."""
        spec = self.get_spec(method)
        repo_path = self.ensure_repo_checkout(method)
        checkpoint_dir = self.get_checkpoint_dir(method)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        link_path = repo_path / spec.repo_checkpoint_dirname
        if link_path.is_symlink():
            return link_path
        if link_path.exists():
            for child_path in link_path.iterdir():
                destination = checkpoint_dir / child_path.name
                if destination.exists():
                    continue
                shutil.move(child_path.as_posix(), destination.as_posix())
            link_path.rmdir()

        relative_target = Path(os.path.relpath(checkpoint_dir.as_posix(), start=repo_path.as_posix()))
        link_path.symlink_to(relative_target, target_is_directory=True)
        return link_path

    def sync_environment(self, method: MethodId) -> Path:
        """Create the environment directory and write the mock ready marker."""
        env_dir = self.get_environment_dir(method)
        env_dir.mkdir(parents=True, exist_ok=True)
        self.get_environment_ready_marker(method).write_text(f"{self.get_spec(method).extra_name}\n", encoding="utf-8")
        return self.get_python_executable(method)

    def download_checkpoints(self, method: MethodId, *, overwrite: bool = False) -> list[Path]:
        """Return an empty checkpoint list because real downloads are out of scope."""
        del method, overwrite
        return []

    def setup_method(
        self,
        method: MethodId,
        *,
        overwrite_checkpoints: bool = False,
        sync_environment: bool = False,
    ) -> dict[str, object]:
        """Return the deterministic local mock layout for one backend."""
        del overwrite_checkpoints
        if sync_environment:
            python_executable = self.sync_environment(method)
        else:
            python_executable = self.get_python_executable(method)
        return {
            "method": method.artifact_slug,
            "repo_path": str(self.ensure_repo_checkout(method)),
            "checkpoint_dir": str(self.get_checkpoint_dir(method)),
            "repo_checkpoint_link": str(self.ensure_shared_checkpoint_link(method)),
            "environment_dir": str(self.get_environment_dir(method)),
            "python_executable": str(python_executable),
            "environment_ready": self.is_environment_ready(method),
            "checkpoints": [str(path) for path in self.download_checkpoints(method)],
        }


__all__ = [
    "ENVIRONMENT_READY_MARKER",
    "METHOD_INSTALL_SPECS",
    "MethodInstallSpec",
    "MethodInstallationService",
]
