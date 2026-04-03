"""Mock method runtimes that satisfy the shared repository interfaces."""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator

from prml_vslam.methods.interfaces import (
    MethodArtifacts,
    MethodCommand,
    MethodId,
    MethodRunRequest,
    MethodRunResult,
    ViewerId,
)
from prml_vslam.methods.visualization import show_open3d_scene, write_plotly_scene_html
from prml_vslam.pipeline.workspace import PreparedInput
from prml_vslam.utils import BaseConfig

_MOCK_TRAJECTORY = (
    "# timestamp tx ty tz qx qy qz qw\n"
    "0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000\n"
    "1.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000\n"
)
_MOCK_POINT_CLOUD = (
    "ply\n"
    "format ascii 1.0\n"
    "element vertex 2\n"
    "property float x\n"
    "property float y\n"
    "property float z\n"
    "end_header\n"
    "0.0 0.0 0.0\n"
    "1.0 0.0 0.0\n"
)


class MockMethodConfig(BaseConfig):
    """Base config for a repository-local mock method runtime."""

    repo_path: Path
    """Path recorded as the mock upstream checkout location."""

    python_executable: str = "python"
    """Executable echoed into the mock command payload."""

    @field_validator("repo_path", mode="before")
    @classmethod
    def _resolve_repo_path(cls, value: str | Path) -> Path:
        return Path(value).expanduser().resolve()

    @property
    def target_type(self) -> type[MockMethodRuntime]:
        return MockMethodRuntime

    @property
    def method_id(self) -> MethodId:
        raise NotImplementedError


class MockMethodRuntime:
    """Small local runtime that writes deterministic placeholder artifacts."""

    def __init__(self, config: MockMethodConfig) -> None:
        self.config = config

    def plan(self, request: MethodRunRequest) -> MethodRunResult:
        """Build the typed mock run payload without writing artifacts."""
        source_path = request.input_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input path '{source_path}' does not exist.")

        artifact_root = request.artifact_root.expanduser().resolve()
        method_slug = self.config.method_id.artifact_slug
        native_output_dir = artifact_root / "native" / method_slug
        return MethodRunResult(
            method=self.config.method_id,
            prepared_input=PreparedInput(
                source_path=source_path,
                resolved_input_path=source_path,
            ),
            command=MethodCommand(
                cwd=self.config.repo_path,
                argv=[
                    self.config.python_executable,
                    f"<mock-{method_slug}>",
                    source_path.as_posix(),
                ],
            ),
            artifacts=MethodArtifacts(
                artifact_root=artifact_root,
                native_output_dir=native_output_dir,
                normalized_trajectory_path=artifact_root / "slam" / "trajectory.tum",
                normalized_point_cloud_path=artifact_root / "dense" / "dense_points.ply",
                raw_trajectory_path=native_output_dir / "trajectory.tum",
                raw_point_cloud_path=native_output_dir / "dense_points.ply",
                plotly_html_path=artifact_root / "visualization" / f"{method_slug}_scene.html",
            ),
            notes=[
                f"{self.config.method_id.display_name} is a mock interface in this repository.",
            ],
        )

    def infer(self, request: MethodRunRequest, *, execute: bool = True) -> MethodRunResult:
        """Return the planned mock run and optionally materialize placeholder outputs."""
        result = self.plan(request)
        if not execute:
            return result

        self._write_mock_artifact(result.artifacts.normalized_trajectory_path, _MOCK_TRAJECTORY)
        self._write_mock_artifact(result.artifacts.normalized_point_cloud_path, _MOCK_POINT_CLOUD)
        if result.artifacts.raw_trajectory_path is not None:
            self._write_mock_artifact(result.artifacts.raw_trajectory_path, _MOCK_TRAJECTORY)
        if result.artifacts.raw_point_cloud_path is not None:
            self._write_mock_artifact(result.artifacts.raw_point_cloud_path, _MOCK_POINT_CLOUD)

        if request.viewer is ViewerId.PLOTLY and result.artifacts.plotly_html_path is not None:
            result.artifacts.plotly_html_path = write_plotly_scene_html(
                output_path=result.artifacts.plotly_html_path,
                point_cloud_path=result.artifacts.normalized_point_cloud_path,
                trajectory_path=result.artifacts.normalized_trajectory_path,
            )
        elif request.viewer is ViewerId.OPEN3D and request.launch_viewer:
            show_open3d_scene(
                point_cloud_path=result.artifacts.normalized_point_cloud_path,
                trajectory_path=result.artifacts.normalized_trajectory_path,
            )

        result.executed = True
        return result

    @staticmethod
    def _write_mock_artifact(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.resolve()


__all__ = ["MockMethodConfig", "MockMethodRuntime"]
