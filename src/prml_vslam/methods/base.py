from __future__ import annotations

from pathlib import Path

from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import ArtifactRef, SlamArtifacts
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
    @property
    def target_type(self) -> type[MockMethodRuntime]:
        return MockMethodRuntime

    @property
    def method_id(self) -> MethodId:
        raise NotImplementedError


class MockMethodRuntime:
    def __init__(self, config: MockMethodConfig) -> None:
        self.config = config

    def infer(self, input_path: Path, artifact_root: Path, *, execute: bool = True) -> SlamArtifacts:
        """Materialize deterministic mock artifacts on the pipeline-owned surface."""
        source_path = input_path.expanduser().resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Input path '{source_path}' does not exist.")
        resolved_artifact_root = artifact_root.expanduser().resolve()
        artifacts = SlamArtifacts(
            trajectory_tum=_artifact_ref(
                resolved_artifact_root / "slam" / "trajectory.tum",
                kind="tum",
                fingerprint=f"{self.config.method_id.value}-mock-trajectory",
            ),
            dense_points_ply=_artifact_ref(
                resolved_artifact_root / "dense" / "dense_points.ply",
                kind="ply",
                fingerprint=f"{self.config.method_id.value}-mock-dense-points",
            ),
        )
        if execute:
            for path, content in (
                (artifacts.trajectory_tum.path, _MOCK_TRAJECTORY),
                (artifacts.dense_points_ply.path, _MOCK_POINT_CLOUD),
            ):
                self._write_mock_artifact(path, content)
        return artifacts

    @staticmethod
    def _write_mock_artifact(path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.resolve()


def _artifact_ref(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
    return ArtifactRef(path=path, kind=kind, fingerprint=fingerprint)
