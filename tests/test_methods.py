"""Tests for external method adapters."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from prml_vslam.methods import MethodId, MethodRunRequest, MSTRMethodConfig, ViewerId, VISTAMethodConfig
from prml_vslam.methods.io import write_tum_trajectory
from prml_vslam.methods.visualization import write_plotly_scene_html
from prml_vslam.utils import SE3Pose


def _write_rgb_image(path: Path, rgb_value: int) -> None:
    image = np.full((8, 8, 3), rgb_value, dtype=np.uint8)
    assert cv2.imwrite(path.as_posix(), image)


def _write_point_cloud(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "ply",
                "format ascii 1.0",
                "element vertex 2",
                "property float x",
                "property float y",
                "property float z",
                "property uchar red",
                "property uchar green",
                "property uchar blue",
                "end_header",
                "0.0 0.0 0.0 255 0 0",
                "1.0 0.5 0.25 0 128 255",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_method_id_is_str_enum() -> None:
    assert issubclass(MethodId, str)
    assert MethodId.VISTA.display_name == "ViSTA-SLAM"
    assert MethodId.MSTR.display_name == "MASt3R-SLAM"


def test_vista_plan_materializes_images_and_builds_command(tmp_path: Path) -> None:
    repo_path = tmp_path / "vista-slam"
    (repo_path / "configs").mkdir(parents=True)
    (repo_path / "configs" / "default.yaml").write_text("dummy: true\n", encoding="utf-8")

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    _write_rgb_image(image_dir / "input_000.png", 10)
    _write_rgb_image(image_dir / "input_001.png", 20)
    _write_rgb_image(image_dir / "input_002.png", 30)

    runtime = VISTAMethodConfig(repo_path=repo_path).setup_target()
    assert runtime is not None

    result = runtime.infer(
        MethodRunRequest(
            input_path=image_dir,
            artifact_root=tmp_path / "artifacts" / "demo" / "vista",
            frame_stride=2,
            viewer=ViewerId.NONE,
        ),
        execute=False,
    )

    assert result.command.argv[:2] == ["python", "run.py"]
    assert result.prepared_input.frames_dir is not None
    assert result.prepared_input.frames_dir.exists()
    assert result.prepared_input.manifest is not None
    assert len(result.prepared_input.manifest.frames) == 2
    assert (
        result.prepared_input.manifest_path
        == (tmp_path / "artifacts" / "demo" / "vista" / "input" / "capture_manifest.json").resolve()
    )
    assert result.artifacts.raw_trajectory_path is not None
    assert result.artifacts.raw_trajectory_path.name == "trajectory.npy"
    assert (
        result.artifacts.normalized_trajectory_path
        == (tmp_path / "artifacts" / "demo" / "vista" / "slam" / "trajectory.tum").resolve()
    )
    assert (
        result.artifacts.plotly_html_path
        == (tmp_path / "artifacts" / "demo" / "vista" / "visualization" / "vista_scene.html").resolve()
    )


def test_vista_infer_normalizes_native_outputs(tmp_path: Path, monkeypatch) -> None:
    repo_path = tmp_path / "vista-slam"
    (repo_path / "configs").mkdir(parents=True)
    (repo_path / "configs" / "default.yaml").write_text("dummy: true\n", encoding="utf-8")

    image_dir = tmp_path / "images"
    image_dir.mkdir()
    _write_rgb_image(image_dir / "input_000.png", 10)
    _write_rgb_image(image_dir / "input_001.png", 20)

    runtime = VISTAMethodConfig(repo_path=repo_path).setup_target()
    assert runtime is not None

    planned = runtime.infer(
        MethodRunRequest(
            input_path=image_dir,
            artifact_root=tmp_path / "artifacts" / "demo" / "vista",
            viewer=ViewerId.NONE,
        ),
        execute=False,
    )
    assert planned.prepared_input.manifest is not None
    native_dir = planned.artifacts.native_output_dir
    native_dir.mkdir(parents=True, exist_ok=True)
    _write_point_cloud(native_dir / "pointcloud.ply")
    second_pose = SE3Pose(
        qx=0.0,
        qy=0.0,
        qz=np.sqrt(0.5),
        qw=np.sqrt(0.5),
        tx=1.0,
        ty=0.5,
        tz=0.25,
    )
    np.save(native_dir / "trajectory.npy", np.stack([np.eye(4), second_pose.as_matrix()], axis=0))
    np.savez(
        native_dir / "view_graph.npz",
        view_graph={0: [1], 1: [0]},
        view_names=np.asarray(
            [frame.image_path.name for frame in planned.prepared_input.manifest.frames], dtype=object
        ),
    )

    monkeypatch.setattr(runtime, "_run_command", lambda command: None)
    result = runtime.infer(
        MethodRunRequest(
            input_path=image_dir,
            artifact_root=tmp_path / "artifacts" / "demo" / "vista",
            viewer=ViewerId.NONE,
        ),
        execute=True,
    )

    trajectory_lines = result.artifacts.normalized_trajectory_path.read_text(encoding="utf-8").strip().splitlines()
    assert result.executed is True
    assert result.artifacts.normalized_point_cloud_path.exists()
    assert len(trajectory_lines) == 2
    assert trajectory_lines[0].startswith("0.000000 ")
    assert trajectory_lines[1] == "1.000000 1.000000 0.500000 0.250000 0.000000 0.000000 0.707107 0.707107"


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


def test_mstr_plan_builds_headless_command(tmp_path: Path) -> None:
    repo_path = tmp_path / "MASt3R-SLAM"
    (repo_path / "config").mkdir(parents=True)
    (repo_path / "config" / "base.yaml").write_text("dummy: true\n", encoding="utf-8")

    image_dir = tmp_path / "sequence"
    image_dir.mkdir()
    _write_rgb_image(image_dir / "frame_000.png", 42)

    runtime = MSTRMethodConfig(repo_path=repo_path).setup_target()
    assert runtime is not None

    result = runtime.infer(
        MethodRunRequest(
            input_path=image_dir,
            artifact_root=tmp_path / "artifacts" / "demo" / "mstr",
            viewer=ViewerId.NONE,
        ),
        execute=False,
    )

    assert result.command.argv[:2] == ["python", "main.py"]
    assert "--save-as" in result.command.argv
    assert "--no-viz" in result.command.argv
    assert result.artifacts.raw_trajectory_path is not None
    assert result.artifacts.raw_trajectory_path.name == "sequence.txt"
    assert (
        result.artifacts.normalized_point_cloud_path
        == (tmp_path / "artifacts" / "demo" / "mstr" / "dense" / "dense_points.ply").resolve()
    )
    assert (
        result.artifacts.plotly_html_path
        == (tmp_path / "artifacts" / "demo" / "mstr" / "visualization" / "mstr_scene.html").resolve()
    )


def test_write_plotly_scene_html_generates_html(tmp_path: Path) -> None:
    point_cloud_path = tmp_path / "dense_points.ply"
    trajectory_path = tmp_path / "trajectory.tum"
    html_path = tmp_path / "scene.html"

    _write_point_cloud(point_cloud_path)
    trajectory_path.write_text(
        "\n".join(
            [
                "0.000000 0.0 0.0 0.0 0.0 0.0 0.0 1.0",
                "1.000000 1.0 0.5 0.25 0.0 0.0 0.0 1.0",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = write_plotly_scene_html(
        output_path=html_path,
        point_cloud_path=point_cloud_path,
        trajectory_path=trajectory_path,
    )

    assert output_path.exists()
    assert "plotly" in output_path.read_text(encoding="utf-8").lower()
