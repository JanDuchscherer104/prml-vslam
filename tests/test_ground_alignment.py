"""Focused tests for derived ground-plane alignment."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np

from prml_vslam.alignment import GroundAlignmentMetadata, GroundAlignmentService
from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory


def _artifact_ref(path: Path, *, kind: str) -> SimpleNamespace:
    return SimpleNamespace(path=path.resolve(), kind=kind, fingerprint=f"{kind}:{path.name}")


def _identity_pose(*, tx: float, ty: float, tz: float) -> FrameTransform:
    return FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=tx, ty=ty, tz=tz)


def _slam_artifacts_from_scene(
    tmp_path: Path,
    *,
    points_xyz_world: np.ndarray,
    camera_positions_xyz_world: np.ndarray,
) -> SimpleNamespace:
    point_cloud_path = write_point_cloud_ply(tmp_path / "point_cloud.ply", points_xyz_world)
    poses = [
        _identity_pose(tx=float(position[0]), ty=float(position[1]), tz=float(position[2]))
        for position in camera_positions_xyz_world
    ]
    trajectory_path = write_tum_trajectory(
        tmp_path / "trajectory.tum",
        poses=poses,
        timestamps=[float(index) for index in range(len(poses))],
    )
    return SimpleNamespace(
        trajectory_tum=_artifact_ref(trajectory_path, kind="tum"),
        dense_points_ply=_artifact_ref(point_cloud_path, kind="ply"),
    )


def _floor_and_wall_scene(*, floor_points: int, wall_points: int) -> np.ndarray:
    floor_side = int(np.sqrt(floor_points))
    wall_side = int(np.sqrt(wall_points))
    floor_x, floor_z = np.meshgrid(
        np.linspace(-3.0, 3.0, floor_side, dtype=np.float64),
        np.linspace(-5.0, 5.0, floor_side, dtype=np.float64),
        indexing="xy",
    )
    floor = np.stack([floor_x.reshape(-1), np.zeros(floor_x.size, dtype=np.float64), floor_z.reshape(-1)], axis=1)

    wall_y, wall_z = np.meshgrid(
        np.linspace(-0.2, 2.5, wall_side, dtype=np.float64),
        np.linspace(-5.0, 5.0, wall_side, dtype=np.float64),
        indexing="xy",
    )
    wall = np.stack([np.ones(wall_y.size, dtype=np.float64), wall_y.reshape(-1), wall_z.reshape(-1)], axis=1)
    return np.concatenate([floor, wall], axis=0)


def _camera_positions(*, count: int) -> np.ndarray:
    z_positions = np.linspace(-4.0, 4.0, count, dtype=np.float64)
    return np.stack(
        [
            np.zeros(count, dtype=np.float64),
            np.full(count, -1.6, dtype=np.float64),
            z_positions,
        ],
        axis=1,
    )


def test_ground_alignment_service_selects_floor_plane_for_balanced_scene(tmp_path: Path) -> None:
    slam = _slam_artifacts_from_scene(
        tmp_path,
        points_xyz_world=_floor_and_wall_scene(floor_points=2500, wall_points=400),
        camera_positions_xyz_world=_camera_positions(count=12),
    )

    metadata = GroundAlignmentService().estimate_from_slam_artifacts(slam=slam)

    assert metadata.applied is True
    assert metadata.ground_plane_world is not None
    normal_xyz_world = np.asarray(metadata.ground_plane_world.normal_xyz_world, dtype=np.float64)
    assert np.isclose(abs(normal_xyz_world[1]), 1.0, atol=1e-2)
    assert metadata.yaw_source == "trajectory_pca"


def test_ground_alignment_service_skips_wall_dominant_scene(tmp_path: Path) -> None:
    slam = _slam_artifacts_from_scene(
        tmp_path,
        points_xyz_world=_floor_and_wall_scene(floor_points=225, wall_points=6400),
        camera_positions_xyz_world=_camera_positions(count=12),
    )

    metadata = GroundAlignmentService().estimate_from_slam_artifacts(slam=slam)

    assert metadata.applied is False
    assert metadata.skip_reason is not None
    assert metadata.confidence < 0.6


def test_ground_alignment_transform_maps_plane_to_y_zero_and_up(tmp_path: Path) -> None:
    slam = _slam_artifacts_from_scene(
        tmp_path,
        points_xyz_world=_floor_and_wall_scene(floor_points=2500, wall_points=400),
        camera_positions_xyz_world=_camera_positions(count=12),
    )

    metadata = GroundAlignmentService().estimate_from_slam_artifacts(slam=slam)

    assert metadata.applied is True
    assert metadata.T_viewer_world_world is not None
    assert metadata.ground_plane_world is not None
    normal_xyz_world = np.asarray(metadata.ground_plane_world.normal_xyz_world, dtype=np.float64)
    plane_point_xyz_world = -metadata.ground_plane_world.offset_world * normal_xyz_world
    transform_viewer_world_world = metadata.T_viewer_world_world.as_matrix()
    plane_point_xyz_viewer = (
        transform_viewer_world_world[:3, :3] @ plane_point_xyz_world + transform_viewer_world_world[:3, 3]
    )
    normal_xyz_viewer = transform_viewer_world_world[:3, :3] @ normal_xyz_world

    assert abs(float(plane_point_xyz_viewer[1])) < 1e-6
    np.testing.assert_allclose(normal_xyz_viewer, np.array([0.0, 1.0, 0.0], dtype=np.float64), atol=1e-5)


def test_ground_alignment_visualization_patch_lies_on_detected_plane(tmp_path: Path) -> None:
    slam = _slam_artifacts_from_scene(
        tmp_path,
        points_xyz_world=_floor_and_wall_scene(floor_points=2500, wall_points=400),
        camera_positions_xyz_world=_camera_positions(count=12),
    )

    metadata = GroundAlignmentService().estimate_from_slam_artifacts(slam=slam)

    assert metadata.applied is True
    assert metadata.visualization is not None
    assert metadata.ground_plane_world is not None
    corners_xyz_world = np.asarray(metadata.visualization.corners_xyz_world, dtype=np.float64)
    normal_xyz_world = np.asarray(metadata.ground_plane_world.normal_xyz_world, dtype=np.float64)
    offset_world = metadata.ground_plane_world.offset_world

    assert corners_xyz_world.shape == (4, 3)
    assert np.all(np.isfinite(corners_xyz_world))
    signed_distances = corners_xyz_world @ normal_xyz_world + offset_world
    np.testing.assert_allclose(signed_distances, np.zeros(4, dtype=np.float64), atol=5e-3)


def test_ground_alignment_yaw_falls_back_to_identity_for_degenerate_trajectory(tmp_path: Path) -> None:
    slam = _slam_artifacts_from_scene(
        tmp_path,
        points_xyz_world=_floor_and_wall_scene(floor_points=2500, wall_points=400),
        camera_positions_xyz_world=np.repeat(_camera_positions(count=1), repeats=4, axis=0),
    )

    metadata = GroundAlignmentService().estimate_from_slam_artifacts(slam=slam)

    assert metadata.applied is True
    assert metadata.yaw_source == "identity"


def test_ground_alignment_metadata_json_keeps_explicit_frame_semantics() -> None:
    metadata = GroundAlignmentMetadata(
        applied=True,
        confidence=0.9,
        point_cloud_source="dense_points_ply",
        T_viewer_world_world=FrameTransform(
            target_frame="viewer_world",
            source_frame="world",
            qx=0.0,
            qy=0.0,
            qz=0.0,
            qw=1.0,
            tx=0.0,
            ty=1.0,
            tz=0.0,
        ),
    )

    payload = metadata.model_dump_json()

    assert "viewer_world" in payload
    assert '"source_frame":"world"' in payload
