from __future__ import annotations

from pathlib import Path

from pydantic import field_validator

from prml_vslam.methods.interfaces import (
    MethodArtifacts,
    MethodCommand,
    MethodId,
    MethodRunRequest,
    MethodRunResult,
)
from prml_vslam.pipeline.workspace import PreparedInput
from prml_vslam.utils import BaseConfig

_MOCK_TRAJECTORY = """# timestamp tx ty tz qx qy qz qw
0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000
1.000000 1.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000
"""
_MOCK_POINT_CLOUD = """ply
format ascii 1.0
element vertex 2
property float x
property float y
property float z
end_header
0.0 0.0 0.0
1.0 0.0 0.0
"""


class MockMethodConfig(BaseConfig):
    repo_path: Path
    python_executable: str = "python"

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
    def __init__(self, config: MockMethodConfig) -> None:
        self.config = config

    def plan(self, request: MethodRunRequest) -> MethodRunResult:
        source_path = request.input_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input path '{source_path}' does not exist.")
        artifact_root = request.artifact_root.expanduser().resolve()
        method_id = self.config.method_id
        method_slug = method_id.artifact_slug
        native_output_dir = artifact_root / "native" / method_slug
        return MethodRunResult(
            method=method_id,
            prepared_input=PreparedInput(source_path=source_path, resolved_input_path=source_path),
            command=MethodCommand(
                cwd=self.config.repo_path,
                argv=[self.config.python_executable, f"<mock-{method_slug}>", source_path.as_posix()],
            ),
            artifacts=MethodArtifacts(
                artifact_root=artifact_root,
                native_output_dir=native_output_dir,
                normalized_trajectory_path=artifact_root / "slam" / "trajectory.tum",
                normalized_point_cloud_path=artifact_root / "dense" / "dense_points.ply",
                raw_trajectory_path=native_output_dir / "trajectory.tum",
                raw_point_cloud_path=native_output_dir / "dense_points.ply",
            ),
            notes=[f"{method_id.display_name} is a mock interface in this repository."],
        )

    def infer(self, request: MethodRunRequest, *, execute: bool = True) -> MethodRunResult:
        result = self.plan(request)
        if execute:
            self._materialize_outputs(result)
            result.executed = True
        return result

    def _materialize_outputs(self, result: MethodRunResult) -> None:
        for path in (result.artifacts.normalized_trajectory_path, result.artifacts.raw_trajectory_path):
            if path is not None:
                self._write_mock_artifact(path, _MOCK_TRAJECTORY)
        for path in (result.artifacts.normalized_point_cloud_path, result.artifacts.raw_point_cloud_path):
            if path is not None:
                self._write_mock_artifact(path, _MOCK_POINT_CLOUD)

    @staticmethod
    def _write_mock_artifact(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.resolve()
