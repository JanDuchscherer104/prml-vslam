"""Tests for shared geometry primitives."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, SE3Pose
from prml_vslam.utils.geometry import (
    load_tum_trajectory,
    pointmap_from_depth,
    transform_points_world_camera,
    write_point_cloud_ply,
    write_tum_trajectory,
)


def test_camera_intrinsics_roundtrip_from_matrix() -> None:
    matrix = [[525.0, 0.0, 320.0], [0.0, 530.0, 240.0], [0.0, 0.0, 1.0]]

    intrinsics = CameraIntrinsics.from_matrix(matrix)

    assert intrinsics == CameraIntrinsics(fx=525.0, fy=530.0, cx=320.0, cy=240.0)
    assert np.allclose(intrinsics.as_matrix(), np.asarray(matrix, dtype=np.float64))


def test_camera_intrinsics_from_column_major_flat_k() -> None:
    flat_k = [525.0, 0.0, 0.0, 0.0, 530.0, 0.0, 320.0, 240.0, 1.0]

    intrinsics = CameraIntrinsics.from_column_major_flat_k(flat_k)

    assert intrinsics == CameraIntrinsics(fx=525.0, fy=530.0, cx=320.0, cy=240.0)


def test_se3_pose_roundtrips_through_matrix() -> None:
    pose = SE3Pose(
        qx=0.0,
        qy=0.0,
        qz=math.sin(math.pi / 4.0),
        qw=math.cos(math.pi / 4.0),
        tx=1.5,
        ty=-2.0,
        tz=0.25,
    )

    roundtripped = SE3Pose.from_matrix(pose.as_matrix())

    assert np.allclose(roundtripped.as_matrix(), pose.as_matrix())
    assert np.allclose(roundtripped.translation_xyz(), np.array([1.5, -2.0, 0.25], dtype=np.float64))


def test_se3_pose_to_tum_fields() -> None:
    pose = SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0)

    assert pose.to_tum_fields() == (1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 1.0)


def test_tum_trajectory_roundtrips_through_shared_helpers(tmp_path: Path) -> None:
    path = tmp_path / "trajectory.tum"
    poses = [
        SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=4.0, ty=5.0, tz=6.0),
    ]

    write_tum_trajectory(path, poses, [0.0, 1.0])
    trajectory = load_tum_trajectory(path)

    assert np.allclose(trajectory.timestamps_s, np.array([0.0, 1.0], dtype=np.float64))
    assert np.allclose(trajectory.positions_xyz, np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64))


def test_empty_tum_trajectory_roundtrips_through_shared_helpers(tmp_path: Path) -> None:
    path = tmp_path / "trajectory.tum"

    write_tum_trajectory(path, [], [])
    trajectory = load_tum_trajectory(path)

    assert trajectory.timestamps_s.shape == (0,)
    assert trajectory.positions_xyz.shape == (0, 3)
    assert trajectory.quaternions_xyzw.shape == (0, 4)


def test_pointmap_from_depth_uses_intrinsics_and_stride() -> None:
    pointmap = pointmap_from_depth(
        np.full((4, 4), 2.0, dtype=np.float32),
        CameraIntrinsics(fx=2.0, fy=4.0, cx=1.0, cy=2.0, width_px=4, height_px=4),
        stride_px=2,
    )

    assert pointmap.shape == (2, 2, 3)
    assert np.allclose(pointmap[0, 0], np.array([-1.0, -1.0, 2.0], dtype=np.float32))
    assert np.allclose(pointmap[1, 1], np.array([1.0, 0.0, 2.0], dtype=np.float32))


def test_transform_points_world_camera_applies_pose_translation() -> None:
    points_world = transform_points_world_camera(
        np.array([[0.0, 0.0, 1.0], [1.0, 2.0, 3.0]], dtype=np.float32),
        SE3Pose(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=10.0, ty=20.0, tz=30.0),
    )

    assert np.allclose(points_world, np.array([[10.0, 20.0, 31.0], [11.0, 22.0, 33.0]], dtype=np.float64))


def test_write_point_cloud_ply_materializes_vertex_count(tmp_path: Path) -> None:
    path = write_point_cloud_ply(tmp_path / "points.ply", np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]]))

    lines = path.read_text(encoding="utf-8").splitlines()

    assert "element vertex 2" in lines
