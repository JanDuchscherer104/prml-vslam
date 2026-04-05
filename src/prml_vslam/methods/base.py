from __future__ import annotations

from pathlib import Path

from pydantic import field_validator

from prml_vslam.methods.contracts import (
    MethodId,
    MethodRunRequest,
    MethodRunResult,
)
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

    def infer(self, request: MethodRunRequest, *, execute: bool = True) -> MethodRunResult:
        source_path = request.input_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input path '{source_path}' does not exist.")
        artifact_root = request.artifact_root.expanduser().resolve()
        result = MethodRunResult(
            method=self.config.method_id,
            normalized_trajectory_path=artifact_root / "slam" / "trajectory.tum",
            normalized_point_cloud_path=artifact_root / "dense" / "dense_points.ply",
        )
        if execute:
            for path, content in (
                (result.normalized_trajectory_path, _MOCK_TRAJECTORY),
                (result.normalized_point_cloud_path, _MOCK_POINT_CLOUD),
            ):
                self._write_mock_artifact(path, content)
            result.executed = True
        return result

    @staticmethod
    def _write_mock_artifact(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.resolve()
