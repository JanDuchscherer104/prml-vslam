"""Thin offline ViSTA-SLAM wrapper."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from prml_vslam.methods.contracts import MethodId, SlamBackendConfig, SlamOutputPolicy
from prml_vslam.methods.protocols import OfflineSlamBackend
from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import BaseConfig, PathConfig, RunArtifactPaths

from .config_bridge import build_vista_command
from .importer import import_vista_artifacts


class VistaSlamBackendConfig(BaseConfig):
    """Config that builds the thin offline ViSTA-SLAM wrapper."""

    repo_dir: Path | None = None
    """Optional explicit ViSTA-SLAM checkout path."""

    python_executable: str = sys.executable
    """Python executable used to invoke the upstream entry point."""

    @property
    def target_type(self) -> type[VistaSlamBackend]:
        """Runtime type used by `setup_target()`."""
        return VistaSlamBackend


class VistaSlamBackend(OfflineSlamBackend):
    """Offline-only ViSTA-SLAM backend wrapper."""

    method_id = MethodId.VISTA

    def __init__(self, config: VistaSlamBackendConfig) -> None:
        self.config = config
        self._path_config = PathConfig()

    def run_sequence(
        self,
        sequence: SequenceManifest,
        backend_config: SlamBackendConfig,
        output_policy: SlamOutputPolicy,
        artifact_root: Path,
    ) -> SlamArtifacts:
        """Run ViSTA-SLAM offline and import its normalized artifacts."""
        repo_dir = self._resolve_repo_dir()
        native_output_dir = RunArtifactPaths.build(artifact_root).native_output_dir
        if native_output_dir.exists():
            shutil.rmtree(native_output_dir)
        native_output_dir.mkdir(parents=True, exist_ok=True)
        command = build_vista_command(
            python_executable=self.config.python_executable,
            repo_dir=repo_dir,
            sequence_manifest=sequence,
            backend_config=backend_config,
            output_policy=output_policy,
            output_dir=native_output_dir,
        )
        completed = subprocess.run(command, cwd=repo_dir, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(
                "ViSTA-SLAM offline execution failed.\n"
                f"Command: {' '.join(command)}\n"
                f"STDOUT:\n{completed.stdout}\n"
                f"STDERR:\n{completed.stderr}"
            )
        return import_vista_artifacts(
            native_output_dir=native_output_dir, run_paths=RunArtifactPaths.build(artifact_root)
        )

    def _resolve_repo_dir(self) -> Path:
        repo_dir = (
            self.config.repo_dir
            if self.config.repo_dir is not None
            else self._path_config.resolve_method_repo_dir("vista-slam")
        )
        resolved = repo_dir.expanduser().resolve()
        if not resolved.exists():
            raise RuntimeError(f"ViSTA-SLAM repository not found at '{resolved}'.")
        if not (resolved / "run.py").exists():
            raise RuntimeError(f"ViSTA-SLAM checkout at '{resolved}' does not expose `run.py`.")
        return resolved


__all__ = ["VistaSlamBackend", "VistaSlamBackendConfig"]
