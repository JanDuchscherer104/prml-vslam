"""Tests for shared geometry primitives."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from pytransform3d.rotations import check_matrix

from prml_vslam.interfaces import (
    CameraIntrinsics,
    CameraIntrinsicsSample,
    CameraIntrinsicsSeries,
    DepthMap,
    FrameTransform,
    PointCloud,
    PointMap,
)
from prml_vslam.interfaces.camera import (
    center_crop_resize_intrinsics,
    crop_camera_intrinsics,
    load_camera_intrinsics_yaml,
    scale_camera_intrinsics,
)
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.utils.geometry import (
    load_point_cloud_ply,
    load_point_cloud_ply_with_colors,
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
    assert "K = \\begin{bmatrix}" in intrinsics.to_latex()


def test_camera_intrinsics_from_column_major_flat_k() -> None:
    flat_k = [525.0, 0.0, 0.0, 0.0, 530.0, 0.0, 320.0, 240.0, 1.0]

    intrinsics = CameraIntrinsics.from_column_major_flat_k(flat_k)

    assert intrinsics == CameraIntrinsics(fx=525.0, fy=530.0, cx=320.0, cy=240.0)


def test_camera_intrinsics_series_round_trips_json() -> None:
    series = CameraIntrinsicsSeries(
        raster_space="vista_model",
        source="native/intrinsics.npy",
        method_id="vista",
        width_px=224,
        height_px=224,
        samples=[
            CameraIntrinsicsSample(
                index=0,
                keyframe_index=0,
                timestamp_ns=123,
                view_name="frame_000000",
                intrinsics=CameraIntrinsics(fx=280.0, fy=281.0, cx=112.0, cy=112.0, width_px=224, height_px=224),
            )
        ],
        metadata={"preprocessing": "center_crop_resize"},
    )

    restored = CameraIntrinsicsSeries.model_validate_json(series.model_dump_json())

    assert restored == series


def test_camera_intrinsics_series_from_matrices() -> None:
    matrices = np.asarray(
        [
            [[10.0, 0.0, 5.0], [0.0, 11.0, 6.0], [0.0, 0.0, 1.0]],
            [[12.0, 0.0, 5.5], [0.0, 13.0, 6.5], [0.0, 0.0, 1.0]],
        ],
        dtype=np.float64,
    )

    series = CameraIntrinsicsSeries.from_matrices(
        matrices,
        raster_space="vista_model",
        source="native/intrinsics.npy",
        method_id="vista",
        width_px=224,
        height_px=224,
        keyframe_indices=[0, 3],
        timestamps_ns=[100, 200],
        view_names=["a", "b"],
        metadata={"fallback": True},
    )

    assert series.raster_space == "vista_model"
    assert series.samples[1].keyframe_index == 3
    assert series.samples[1].timestamp_ns == 200
    assert series.samples[1].view_name == "b"
    assert series.samples[1].intrinsics == CameraIntrinsics(
        fx=12.0,
        fy=13.0,
        cx=5.5,
        cy=6.5,
        width_px=224,
        height_px=224,
    )


def test_load_camera_intrinsics_yaml(tmp_path: Path) -> None:
    path = tmp_path / "intrinsics.yaml"
    _write_intrinsics_yaml(path)

    intrinsics = load_camera_intrinsics_yaml(path)

    assert intrinsics == CameraIntrinsics(
        fx=517.3,
        fy=516.5,
        cx=318.6,
        cy=255.3,
        width_px=640,
        height_px=480,
        distortion_model="radial-tangential",
        distortion_coefficients=(0.2624, -0.9531, -0.0054, 0.0026, 1.1633),
    )


def test_camera_intrinsics_scale_crop_and_center_crop_resize_helpers() -> None:
    source = CameraIntrinsics(fx=517.3, fy=516.5, cx=318.6, cy=255.3, width_px=640, height_px=480)

    scaled = scale_camera_intrinsics(source, scale_x=0.5, scale_y=0.25)
    cropped = crop_camera_intrinsics(source, left_px=10.0, top_px=20.0, width_px=320, height_px=240)
    vista_model = center_crop_resize_intrinsics(
        source,
        output_width_px=224,
        output_height_px=224,
        border_x_px=10,
        border_y_px=10,
    )

    assert scaled == CameraIntrinsics(fx=258.65, fy=129.125, cx=159.3, cy=63.825, width_px=320, height_px=120)
    assert cropped == CameraIntrinsics(fx=517.3, fy=516.5, cx=308.6, cy=235.3, width_px=320, height_px=240)
    assert vista_model.width_px == 224
    assert vista_model.height_px == 224
    assert vista_model.fx == pytest.approx(251.90, abs=1e-2)
    assert vista_model.fy == pytest.approx(251.51, abs=1e-2)
    assert vista_model.cx == pytest.approx(112.27, abs=1e-2)
    assert vista_model.cy == pytest.approx(119.45, abs=1e-2)


def test_frame_transform_roundtrips_through_matrix() -> None:
    pose = FrameTransform(
        qx=0.0,
        qy=0.0,
        qz=math.sin(math.pi / 4.0),
        qw=math.cos(math.pi / 4.0),
        tx=1.5,
        ty=-2.0,
        tz=0.25,
    )

    roundtripped = FrameTransform.from_matrix(pose.as_matrix())

    assert np.allclose(roundtripped.as_matrix(), pose.as_matrix())
    assert np.allclose(roundtripped.translation_xyz(), np.array([1.5, -2.0, 0.25], dtype=np.float64))


def test_frame_transform_to_tum_fields() -> None:
    pose = FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0)

    assert pose.to_tum_fields() == (1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 1.0)


def test_project_rotation_to_so3_normalizes_small_perturbations() -> None:
    rotation = FrameTransform(
        qx=0.0,
        qy=0.0,
        qz=math.sin(math.pi / 8.0),
        qw=math.cos(math.pi / 8.0),
        tx=0.0,
        ty=0.0,
        tz=0.0,
    ).as_matrix()[:3, :3]
    perturbed = rotation.copy()
    perturbed[0, 0] += 1e-5
    perturbed[1, 2] -= 2e-5

    projected = project_rotation_to_so3(perturbed)

    check_matrix(projected)
    np.testing.assert_allclose(projected, rotation, atol=1e-4)


def test_project_rotation_to_so3_rejects_non_finite_input() -> None:
    rotation = np.eye(3, dtype=np.float64)
    rotation[0, 0] = np.nan

    with pytest.raises(ValueError, match="must contain only finite values"):
        project_rotation_to_so3(rotation)


def test_project_rotation_to_so3_rejects_non_3x3_input() -> None:
    with pytest.raises(ValueError, match="Expected a 3x3 rotation matrix"):
        project_rotation_to_so3(np.eye(4, dtype=np.float64))


def test_project_rotation_to_so3_rejects_rotations_that_are_too_far_away() -> None:
    rotation = np.diag([2.0, 0.5, 0.25]).astype(np.float64)

    with pytest.raises(ValueError, match="too far from SO\\(3\\)"):
        project_rotation_to_so3(rotation)


def test_tum_trajectory_roundtrips_through_shared_helpers(tmp_path: Path) -> None:
    path = tmp_path / "trajectory.tum"
    poses = [
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=1.0, ty=2.0, tz=3.0),
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=4.0, ty=5.0, tz=6.0),
    ]

    write_tum_trajectory(path, poses, [0.0, 1.0])
    trajectory = load_tum_trajectory(path)

    assert np.allclose(trajectory.timestamps, np.array([0.0, 1.0], dtype=np.float64))
    assert np.allclose(trajectory.positions_xyz, np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], dtype=np.float64))


def test_load_tum_trajectory_normalizes_rounded_quaternions(tmp_path: Path) -> None:
    path = tmp_path / "rounded.tum"
    path.write_text(
        "\n".join(
            [
                "0.0 1.0 2.0 3.0 0.7907 0.4393 -0.1770 -0.3879",
                "1.0 4.0 5.0 6.0 0.7911 0.4393 -0.1768 -0.3872",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    trajectory = load_tum_trajectory(path)

    assert np.allclose(np.linalg.norm(trajectory.orientations_quat_wxyz, axis=1), 1.0)


def test_empty_tum_trajectory_roundtrips_through_shared_helpers(tmp_path: Path) -> None:
    path = tmp_path / "trajectory.tum"

    write_tum_trajectory(path, [], [])
    with pytest.raises(ValueError, match="empty"):
        load_tum_trajectory(path)


def test_pointmap_from_depth_uses_intrinsics_and_stride() -> None:
    pointmap = pointmap_from_depth(
        np.full((4, 4), 2.0, dtype=np.float32),
        CameraIntrinsics(fx=2.0, fy=4.0, cx=1.0, cy=2.0, width_px=4, height_px=4),
        stride_px=2,
    )

    assert pointmap.shape == (2, 2, 3)
    assert np.allclose(pointmap[0, 0], np.array([-1.0, -1.0, 2.0], dtype=np.float32))
    assert np.allclose(pointmap[1, 1], np.array([1.0, 0.0, 2.0], dtype=np.float32))


def test_pointmap_from_depth_rejects_sampled_nonfinite_depth() -> None:
    depth = np.ones((4, 4), dtype=np.float32)
    depth[2, 2] = np.nan

    with pytest.raises(ValueError, match="finite"):
        pointmap_from_depth(
            depth,
            CameraIntrinsics(fx=2.0, fy=4.0, cx=1.0, cy=2.0, width_px=4, height_px=4),
            stride_px=2,
        )


def test_transform_points_world_camera_applies_pose_translation() -> None:
    points_world = transform_points_world_camera(
        np.array([[0.0, 0.0, 1.0], [1.0, 2.0, 3.0]], dtype=np.float32),
        FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=10.0, ty=20.0, tz=30.0),
    )

    assert np.allclose(points_world, np.array([[10.0, 20.0, 31.0], [11.0, 22.0, 33.0]], dtype=np.float64))


def test_point_cloud_ply_roundtrips_through_open3d_helpers(tmp_path: Path) -> None:
    points_xyz = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]], dtype=np.float64)

    path = write_point_cloud_ply(tmp_path / "points.ply", points_xyz)
    restored = load_point_cloud_ply(path)

    assert restored.dtype == np.float64
    assert restored.shape == (2, 3)
    np.testing.assert_allclose(restored, points_xyz)


def test_point_cloud_ply_roundtrips_optional_colors(tmp_path: Path) -> None:
    points_xyz = np.array([[0.0, 1.0, 2.0], [3.0, 4.0, 5.0]], dtype=np.float64)
    colors_rgb = np.array([[255, 0, 128], [0, 255, 64]], dtype=np.uint8)

    path = write_point_cloud_ply(tmp_path / "colored.ply", points_xyz, colors_rgb=colors_rgb)
    restored_points, restored_colors = load_point_cloud_ply_with_colors(path)

    np.testing.assert_allclose(restored_points, points_xyz)
    assert restored_colors is not None
    np.testing.assert_allclose(restored_colors, colors_rgb.astype(np.float64) / 255.0, atol=1 / 255.0)


def test_point_cloud_contract_rejects_raster_pointmap_shape() -> None:
    with pytest.raises(ValueError, match="point cloud shape"):
        PointCloud(points_xyz=np.zeros((2, 2, 3), dtype=np.float32), frame="camera")


def test_pointmap_contract_rejects_sparse_point_cloud_shape() -> None:
    with pytest.raises(ValueError, match="pointmap shape"):
        PointMap(points_xyz_camera=np.zeros((5, 3), dtype=np.float32), camera_frame="camera")


def test_depth_map_contract_requires_matching_intrinsics_shape() -> None:
    with pytest.raises(ValueError, match="does not match depth width"):
        DepthMap(
            depth_m=np.ones((2, 3), dtype=np.float32),
            intrinsics=CameraIntrinsics(fx=1.0, fy=1.0, cx=1.0, cy=1.0, width_px=4, height_px=2),
        )


def test_world_placeable_geometry_transform_source_frame_must_match() -> None:
    with pytest.raises(ValueError, match="source_frame must match"):
        PointCloud(
            points_xyz=np.zeros((2, 3), dtype=np.float32),
            frame="advio_tango_raw_depth_sensor",
            T_world_frame=FrameTransform(
                target_frame="advio_tango_raw_world",
                source_frame="camera",
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=0.0,
                tz=0.0,
            ),
        )


def _write_intrinsics_yaml(path: Path) -> None:
    path.write_text(
        """
cameras:
- camera:
    image_height: 480
    image_width: 640
    intrinsics:
      data: [517.3, 516.5, 318.6, 255.3]
    distortion:
      type: radial-tangential
      parameters:
        data: [0.2624, -0.9531, -0.0054, 0.0026, 1.1633]
""".strip(),
        encoding="utf-8",
    )
