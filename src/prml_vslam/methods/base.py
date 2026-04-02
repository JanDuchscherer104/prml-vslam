"""Base classes for external VSLAM method adapters."""

from __future__ import annotations

import shutil
import subprocess
import webbrowser
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import field_validator

from prml_vslam.methods.contracts import (
    MethodArtifacts,
    MethodCommand,
    MethodId,
    MethodRunRequest,
    MethodRunResult,
    ViewerId,
)
from prml_vslam.methods.io import ensure_directory
from prml_vslam.methods.visualization import show_open3d_scene, write_plotly_scene_html
from prml_vslam.pipeline.workspace import PreparedInput
from prml_vslam.utils import BaseConfig, Console, RunArtifactPaths

if TYPE_CHECKING:
    from collections.abc import Sequence


class ExternalMethodConfig(BaseConfig, ABC):
    """Base config shared by external method adapters."""

    repo_path: Path
    """Path to the checked-out upstream repository."""

    python_executable: str = "python"
    """Python executable used to invoke the upstream entry point."""

    config_path: Path | None = None
    """Optional explicit upstream config path."""

    @field_validator("repo_path", mode="before")
    @classmethod
    def _resolve_repo_path(cls, value: str | Path) -> Path:
        repo_path = Path(value).expanduser().resolve()
        if not repo_path.exists():
            raise ValueError(f"Configured upstream repository '{repo_path}' does not exist.")
        return repo_path

    @field_validator("config_path", mode="before")
    @classmethod
    def _resolve_optional_config_path(cls, value: str | Path | None) -> Path | None:
        if value is None:
            return None
        return Path(value).expanduser().resolve()

    @property
    @abstractmethod
    def method_id(self) -> MethodId:
        """Return the backend identity."""

    @property
    @abstractmethod
    def default_config_relpath(self) -> Path:
        """Return the default config path relative to the upstream repo."""

    def resolve_config_path(self) -> Path:
        """Return the explicit or default upstream config path."""
        config_path = self.config_path or (self.repo_path / self.default_config_relpath)
        resolved = config_path if config_path.is_absolute() else (self.repo_path / config_path)
        resolved = resolved.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Config path '{resolved}' does not exist.")
        return resolved


class BaseMethod(ABC):
    """Shared runtime orchestration for external VSLAM backends."""

    console = Console(__name__)

    def __init__(self, config: ExternalMethodConfig) -> None:
        self.config = config

    @property
    def method_id(self) -> MethodId:
        """Return the backend identity from the config."""
        return self.config.method_id

    def infer(self, request: MethodRunRequest, *, execute: bool = True) -> MethodRunResult:
        """Plan and optionally execute one upstream SLAM run."""
        plan = self.plan(request)
        if not execute:
            return plan

        self._run_command(plan.command)
        self._normalize_outputs(plan)
        plan.executed = True
        self._render_outputs(plan, request)
        return plan

    def plan(self, request: MethodRunRequest) -> MethodRunResult:
        """Materialize method-ready input and build the explicit invocation."""
        prepared_input = self._prepare_input(request)
        artifacts = self._build_artifacts(request, prepared_input)
        command = self._build_command(request, prepared_input, artifacts)
        native_viewer_command = self._build_native_viewer_command(artifacts)
        notes = self._build_notes()
        return MethodRunResult(
            method=self.method_id,
            prepared_input=prepared_input,
            command=command,
            artifacts=artifacts,
            native_viewer_command=native_viewer_command,
            notes=notes,
        )

    @abstractmethod
    def _prepare_input(self, request: MethodRunRequest) -> PreparedInput:
        """Return the method-ready input derived from the shared request."""

    @abstractmethod
    def _build_artifacts(self, request: MethodRunRequest, prepared_input: PreparedInput) -> MethodArtifacts:
        """Return native and normalized artifact paths for the run."""

    @abstractmethod
    def _build_command(
        self,
        request: MethodRunRequest,
        prepared_input: PreparedInput,
        artifacts: MethodArtifacts,
    ) -> MethodCommand:
        """Build the upstream inference command."""

    @abstractmethod
    def _normalize_outputs(self, result: MethodRunResult) -> None:
        """Copy or convert upstream outputs into normalized artifact paths."""

    def _build_native_viewer_command(self, artifacts: MethodArtifacts) -> MethodCommand | None:
        """Return a post-hoc native viewer command when the backend supports one."""
        return None

    def _build_notes(self) -> list[str]:
        """Return backend-specific caveats for the caller."""
        return []

    def _render_outputs(self, result: MethodRunResult, request: MethodRunRequest) -> None:
        """Prepare or launch the selected visualization surface."""
        match request.viewer:
            case ViewerId.NONE:
                return
            case ViewerId.PLOTLY:
                plotly_html_path = result.artifacts.plotly_html_path
                if plotly_html_path is None:
                    msg = f"{self.method_id.display_name} does not define a Plotly output path."
                    raise ValueError(msg)
                result.artifacts.plotly_html_path = write_plotly_scene_html(
                    output_path=plotly_html_path,
                    point_cloud_path=result.artifacts.normalized_point_cloud_path,
                    trajectory_path=result.artifacts.normalized_trajectory_path,
                    view_graph_path=result.artifacts.view_graph_path,
                    max_points=request.max_plotly_points,
                )
                if request.launch_viewer:
                    webbrowser.open(result.artifacts.plotly_html_path.as_uri())
            case ViewerId.OPEN3D:
                if request.launch_viewer:
                    show_open3d_scene(
                        point_cloud_path=result.artifacts.normalized_point_cloud_path,
                        trajectory_path=result.artifacts.normalized_trajectory_path,
                        view_graph_path=result.artifacts.view_graph_path,
                    )
            case ViewerId.NATIVE:
                native_viewer_command = result.native_viewer_command
                if request.launch_viewer and native_viewer_command is not None:
                    self._run_command(native_viewer_command)

    def _run_command(self, command: MethodCommand) -> None:
        """Execute one explicit external command and raise on failure."""
        ensure_directory(command.cwd)
        rendered_command = " ".join(command.argv)
        self.console.info(f"Running [{self.method_id.artifact_slug}] from '{command.cwd}': {rendered_command}")
        subprocess.run(command.argv, cwd=command.cwd, check=True)

    @staticmethod
    def resolve_existing_input_path(input_path: Path) -> Path:
        """Resolve one input path and raise when it does not exist."""
        source_path = input_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input path '{source_path}' does not exist.")
        return source_path

    @staticmethod
    def run_paths(artifact_root: Path) -> RunArtifactPaths:
        """Return the canonical repository-owned layout for `artifact_root`."""
        return RunArtifactPaths.build(artifact_root)

    def build_method_artifacts(
        self,
        request: MethodRunRequest,
        *,
        native_output_dir: Path,
        raw_trajectory_path: Path | None = None,
        raw_point_cloud_path: Path | None = None,
        view_graph_path: Path | None = None,
    ) -> MethodArtifacts:
        """Build canonical normalized artifact paths plus method-native outputs."""
        run_paths = self.run_paths(request.artifact_root)
        return MethodArtifacts(
            artifact_root=run_paths.artifact_root,
            native_output_dir=native_output_dir.resolve(),
            normalized_trajectory_path=run_paths.trajectory_path,
            normalized_point_cloud_path=run_paths.dense_points_path,
            raw_trajectory_path=raw_trajectory_path.resolve() if raw_trajectory_path is not None else None,
            raw_point_cloud_path=raw_point_cloud_path.resolve() if raw_point_cloud_path is not None else None,
            view_graph_path=view_graph_path.resolve() if view_graph_path is not None else None,
            plotly_html_path=run_paths.plotly_scene_path(self.method_id.artifact_slug),
        )

    @staticmethod
    def ensure_files_exist(paths: Sequence[Path]) -> None:
        """Raise if any expected artifact path does not exist."""
        missing_paths = [path for path in paths if not path.exists()]
        if missing_paths:
            missing_rendered = ", ".join(str(path) for path in missing_paths)
            raise FileNotFoundError(f"Expected output artifacts were not produced: {missing_rendered}")

    @staticmethod
    def copy_artifact(source_path: Path, destination_path: Path) -> Path:
        """Copy an artifact into a normalized repository-owned location."""
        ensure_directory(destination_path.parent)
        shutil.copy2(source_path, destination_path)
        return destination_path.resolve()

    @staticmethod
    def build_run_slug(artifact_root: Path, method_id: MethodId) -> str:
        """Build a stable method-run slug from the artifact root."""
        experiment_slug = artifact_root.parent.name or "run"
        return f"{experiment_slug}-{method_id.artifact_slug}"


__all__ = [
    "BaseMethod",
    "ExternalMethodConfig",
]
