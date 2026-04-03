"""Tests for shared geometry primitives."""

from __future__ import annotations

import math

import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, SE3Pose


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
