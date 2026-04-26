"""Tests for reconstruction artifact Plotly figure builders."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d
import pytest

from prml_vslam.interfaces import FrameTransform
from prml_vslam.plotting.reconstruction import (
    build_reference_reconstruction_figure,
    build_slam_reference_comparison_figure,
)
from prml_vslam.utils.geometry import write_tum_trajectory


def test_build_reference_reconstruction_figure_from_tiny_plys(tmp_path: Path) -> None:
    artifact_root = _write_tiny_reconstruction_artifacts(tmp_path)

    figure, summary = build_reference_reconstruction_figure(
        artifact_root,
        max_points=2,
        target_triangles=1,
        mesh_color="#7b1fa2",
        mesh_opacity=0.8,
    )

    assert summary.point_count == 4
    assert summary.plotted_point_count == 2
    assert summary.vertex_count == 3
    assert summary.triangle_count == 1
    assert summary.plotted_triangle_count == 1
    assert figure.layout.title.text == "Reference Reconstruction"
    assert [trace.type for trace in figure.data] == ["mesh3d", "scatter3d"]
    assert figure.data[0].color == "#7b1fa2"
    assert figure.data[0].opacity == 0.8


def test_build_reference_reconstruction_figure_can_render_cloud_only(tmp_path: Path) -> None:
    artifact_root = _write_tiny_reconstruction_artifacts(tmp_path)

    figure, summary = build_reference_reconstruction_figure(
        artifact_root,
        show_mesh=False,
        max_points=2,
    )

    assert [trace.type for trace in figure.data] == ["scatter3d"]
    assert summary.point_count == 4
    assert summary.plotted_point_count == 2
    assert summary.vertex_count == 0
    assert summary.triangle_count == 0
    assert summary.plotted_triangle_count == 0


def test_build_reference_reconstruction_figure_can_render_mesh_only(tmp_path: Path) -> None:
    artifact_root = _write_tiny_reconstruction_artifacts(tmp_path)

    figure, summary = build_reference_reconstruction_figure(
        artifact_root,
        show_point_cloud=False,
        target_triangles=1,
    )

    assert [trace.type for trace in figure.data] == ["mesh3d"]
    assert summary.point_count == 0
    assert summary.plotted_point_count == 0
    assert summary.vertex_count == 3
    assert summary.triangle_count == 1
    assert summary.plotted_triangle_count == 1


def test_build_reference_reconstruction_figure_rejects_empty_modality_selection(tmp_path: Path) -> None:
    artifact_root = _write_tiny_reconstruction_artifacts(tmp_path)

    with pytest.raises(ValueError, match="Select at least one"):
        build_reference_reconstruction_figure(
            artifact_root,
            show_point_cloud=False,
            show_mesh=False,
        )


def test_build_slam_reference_comparison_figure_includes_selected_modalities(tmp_path: Path) -> None:
    artifact_root = _write_tiny_reconstruction_artifacts(tmp_path)
    _write_tiny_slam_artifacts(artifact_root)

    figure, summary = build_slam_reference_comparison_figure(
        artifact_root,
        slam_max_points=2,
        reference_max_points=2,
        target_triangles=1,
    )

    assert [trace.name.split(" (")[0] for trace in figure.data] == [
        "SLAM cloud",
        "Reference cloud",
        "Reference mesh",
        "SLAM trajectory",
        "Reference trajectory",
    ]
    assert summary.slam_point_count == 3
    assert summary.plotted_slam_point_count == 2
    assert summary.reference_point_count == 4
    assert summary.plotted_reference_point_count == 2
    assert summary.reference_triangle_count == 1
    assert summary.plotted_reference_triangle_count == 1
    assert summary.slam_trajectory_poses == 2
    assert summary.reference_trajectory_poses == 2


def _write_tiny_reconstruction_artifacts(tmp_path: Path) -> Path:
    artifact_root = tmp_path / "run"
    reference_dir = artifact_root / "reference"
    reference_dir.mkdir(parents=True)

    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
    )
    assert o3d.io.write_point_cloud(str(reference_dir / "reference_cloud.ply"), point_cloud, write_ascii=True)

    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices = o3d.utility.Vector3dVector(
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            dtype=np.float64,
        )
    )
    mesh.triangles = o3d.utility.Vector3iVector(np.asarray([[0, 1, 2]], dtype=np.int32))
    assert o3d.io.write_triangle_mesh(str(reference_dir / "reference_mesh.ply"), mesh, write_ascii=True)
    return artifact_root


def _write_tiny_slam_artifacts(artifact_root: Path) -> None:
    slam_dir = artifact_root / "slam"
    benchmark_dir = artifact_root / "benchmark"
    slam_dir.mkdir(parents=True, exist_ok=True)
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    point_cloud = o3d.geometry.PointCloud()
    point_cloud.points = o3d.utility.Vector3dVector(
        np.asarray(
            [
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [2.0, 0.0, 0.0],
            ],
            dtype=np.float64,
        )
    )
    assert o3d.io.write_point_cloud(str(slam_dir / "point_cloud.ply"), point_cloud, write_ascii=True)
    poses = [
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=0.0, tz=0.0),
    ]
    write_tum_trajectory(slam_dir / "trajectory.tum", poses=poses, timestamps=[0.0, 1.0])
    write_tum_trajectory(benchmark_dir / "ground_truth.tum", poses=poses, timestamps=[0.0, 1.0])
