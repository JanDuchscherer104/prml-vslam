"""Tests for the repository-local method mocks."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces import SE3Pose
from prml_vslam.methods import MethodId, MethodRunRequest, MSTRMethodConfig, VISTAMethodConfig
from prml_vslam.utils.geometry import write_tum_trajectory


def test_method_id_is_str_enum() -> None:
    assert issubclass(MethodId, str)
    assert MethodId.VISTA.display_name == "ViSTA-SLAM"
    assert MethodId.MSTR.display_name == "MASt3R-SLAM"


def test_vista_mock_plan_returns_typed_paths(tmp_path: Path) -> None:
    repo_path = tmp_path / "vista-slam"
    repo_path.mkdir()
    input_path = tmp_path / "input.mp4"
    input_path.write_text("mock\n", encoding="utf-8")

    runtime = VISTAMethodConfig(repo_path=repo_path).setup_target()
    assert runtime is not None

    result = runtime.infer(
        MethodRunRequest(
            input_path=input_path,
            artifact_root=tmp_path / "artifacts" / "demo" / "vista",
        ),
        execute=False,
    )

    assert result.executed is False
    assert result.prepared_input.resolved_input_path == input_path.resolve()
    assert result.command.argv[:2] == ["python", "<mock-vista>"]
    assert (
        result.artifacts.normalized_trajectory_path
        == (tmp_path / "artifacts" / "demo" / "vista" / "slam" / "trajectory.tum").resolve()
    )
    assert result.notes == ["ViSTA-SLAM is a mock interface in this repository."]


def test_method_mock_infer_materializes_placeholder_outputs(tmp_path: Path) -> None:
    repo_path = tmp_path / "MASt3R-SLAM"
    repo_path.mkdir()
    input_dir = tmp_path / "sequence"
    input_dir.mkdir()

    runtime = MSTRMethodConfig(repo_path=repo_path).setup_target()
    assert runtime is not None

    result = runtime.infer(
        MethodRunRequest(
            input_path=input_dir,
            artifact_root=tmp_path / "artifacts" / "demo" / "mstr",
        ),
        execute=True,
    )

    assert result.executed is True
    assert result.artifacts.normalized_trajectory_path.exists()
    assert result.artifacts.normalized_point_cloud_path.exists()


def test_write_tum_trajectory_consumes_se3_pose_objects(tmp_path: Path) -> None:
    trajectory_path = tmp_path / "trajectory.tum"
    poses = [
        SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
    ]

    write_tum_trajectory(trajectory_path, poses, [0.0, 1.0])

    assert trajectory_path.read_text(encoding="utf-8").splitlines() == [
        "0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 0.000000 1.000000",
        "1.000000 1.000000 2.000000 3.000000 0.000000 0.000000 0.000000 1.000000",
    ]
