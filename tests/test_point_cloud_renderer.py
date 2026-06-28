"""Tests for headless point-cloud view rendering and metric pairing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from prml_vslam.eval.image_metrics import compute_image_metrics
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.rendering import (
    PointCloudRenderer,
    RenderConfig,
    poses_from_tum_trajectory,
    render_trajectory_views,
)
from prml_vslam.utils.geometry import write_point_cloud_ply, write_tum_trajectory

_INTRINSICS = CameraIntrinsics(fx=100.0, fy=100.0, cx=32.0, cy=32.0, width_px=64, height_px=64)
_IDENTITY_POSE = FrameTransform.from_matrix(np.eye(4), target_frame="world", source_frame="camera_rdf")


def _plane_cloud(*, color: tuple[int, int, int] = (255, 0, 0), z: float = 2.0, n: int = 80, half: float = 0.5):
    xs = np.linspace(-half, half, n)
    ys = np.linspace(-half, half, n)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.stack([grid_x.ravel(), grid_y.ravel(), np.full(grid_x.size, z)], axis=1).astype(np.float64)
    colors = np.tile(np.array(color, dtype=np.uint8), (points.shape[0], 1))
    return points, colors


def test_render_colored_plane_at_known_depth() -> None:
    points, colors = _plane_cloud()
    view = PointCloudRenderer(points, colors).render(intrinsics=_INTRINSICS, pose=_IDENTITY_POSE)
    assert view.rgb.shape == (64, 64, 3)
    assert view.rgb.dtype == np.uint8
    assert view.depth_m.dtype == np.float32
    assert view.coverage.dtype == np.bool_
    assert view.coverage[32, 32]
    assert tuple(int(channel) for channel in view.rgb[32, 32]) == (255, 0, 0)
    assert view.depth_m[32, 32] == pytest.approx(2.0, abs=1e-3)
    assert view.coverage_fraction() > 0.0
    # Pixels no point reached stay at the background colour with zero depth.
    assert tuple(int(channel) for channel in view.rgb[0, 0]) == (0, 0, 0)
    assert view.depth_m[0, 0] == 0.0


def test_render_without_colors_uses_default_gray() -> None:
    points, _ = _plane_cloud()
    view = PointCloudRenderer(points, None).render(intrinsics=_INTRINSICS, pose=_IDENTITY_POSE)
    assert view.coverage[32, 32]
    assert tuple(int(channel) for channel in view.rgb[32, 32]) == (128, 128, 128)


def test_render_requires_raster_size() -> None:
    points, colors = _plane_cloud()
    renderer = PointCloudRenderer(points, colors)
    with pytest.raises(ValueError, match="width_px"):
        renderer.render(intrinsics=CameraIntrinsics(fx=100.0, fy=100.0, cx=32.0, cy=32.0), pose=_IDENTITY_POSE)


def test_empty_cloud_rejected() -> None:
    with pytest.raises(ValueError, match="empty point cloud"):
        PointCloudRenderer(np.empty((0, 3), dtype=np.float64))


def test_bad_color_shape_rejected() -> None:
    points, _ = _plane_cloud(n=10)
    with pytest.raises(ValueError, match="Expected point colors shape"):
        PointCloudRenderer(points, np.zeros((5, 3), dtype=np.uint8))


def test_from_ply_round_trip(tmp_path: Path) -> None:
    points, colors = _plane_cloud()
    ply_path = write_point_cloud_ply(tmp_path / "cloud.ply", points, colors_rgb=colors)
    view = PointCloudRenderer.from_ply(ply_path).render(intrinsics=_INTRINSICS, pose=_IDENTITY_POSE)
    assert view.coverage[32, 32]
    assert int(view.rgb[32, 32][0]) > 200  # red channel survives the PLY colour round trip
    assert int(view.rgb[32, 32][1]) < 50


def test_render_many_matches_input_length() -> None:
    points, colors = _plane_cloud()
    views = PointCloudRenderer(points, colors).render_many([(_INTRINSICS, _IDENTITY_POSE)] * 3)
    assert len(views) == 3
    assert all(view.coverage[32, 32] for view in views)


def test_dilation_fills_holes_in_sparse_projection() -> None:
    points, colors = _plane_cloud(n=20)  # sparse enough to leave gaps at 64px
    raw = PointCloudRenderer(points, colors, config=RenderConfig(dilation_px=0)).render(
        intrinsics=_INTRINSICS, pose=_IDENTITY_POSE
    )
    filled = PointCloudRenderer(points, colors, config=RenderConfig(dilation_px=2)).render(
        intrinsics=_INTRINSICS, pose=_IDENTITY_POSE
    )
    assert int(filled.coverage.sum()) > int(raw.coverage.sum())


def test_rendered_view_pairs_with_image_metrics() -> None:
    points, colors = _plane_cloud()
    view = PointCloudRenderer(points, colors).render(intrinsics=_INTRINSICS, pose=_IDENTITY_POSE)
    metrics = compute_image_metrics(view.rgb, view.rgb, mask=view.coverage)
    assert metrics.l1 == 0.0
    assert metrics.psnr == float("inf")
    assert metrics.ssim == pytest.approx(1.0)
    assert metrics.coverage == pytest.approx(view.coverage_fraction())


def test_projection_respects_camera_translation() -> None:
    # A dense green patch centered at world (1, 0, 3).
    xs = np.linspace(0.9, 1.1, 40)
    ys = np.linspace(-0.1, 0.1, 40)
    grid_x, grid_y = np.meshgrid(xs, ys)
    points = np.stack([grid_x.ravel(), grid_y.ravel(), np.full(grid_x.size, 3.0)], axis=1)
    colors = np.tile(np.array([0, 255, 0], dtype=np.uint8), (points.shape[0], 1))
    renderer = PointCloudRenderer(points, colors)

    # A camera translated to world (1, 0, 0) looks straight at the patch: it lands dead center at depth 3.
    camera_at_x1 = np.eye(4)
    camera_at_x1[:3, 3] = [1.0, 0.0, 0.0]
    centered = renderer.render(
        intrinsics=_INTRINSICS,
        pose=FrameTransform.from_matrix(camera_at_x1, target_frame="world", source_frame="camera_rdf"),
    )
    assert centered.coverage[32, 32]
    assert centered.depth_m[32, 32] == pytest.approx(3.0, abs=1e-3)
    assert tuple(int(channel) for channel in centered.rgb[32, 32]) == (0, 255, 0)

    # From the origin the same patch (x≈1) projects to u≈65, off a 64px raster — proving the
    # world->camera extrinsic sign is applied, not ignored.
    from_origin = renderer.render(intrinsics=_INTRINSICS, pose=_IDENTITY_POSE)
    assert not from_origin.coverage[32, 32]


def test_poses_from_tum_round_trip(tmp_path: Path) -> None:
    angle = 0.3
    rotated = np.eye(4)
    rotated[:3, :3] = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    rotated[:3, 3] = [0.1, -0.2, 0.3]
    poses_in = [
        _IDENTITY_POSE,
        FrameTransform.from_matrix(rotated, target_frame="world", source_frame="camera_rdf"),
    ]
    trajectory_path = write_tum_trajectory(tmp_path / "trajectory.tum", poses_in, [0.0, 0.1])

    loaded = poses_from_tum_trajectory(trajectory_path)
    assert len(loaded) == 2
    first_timestamp, first_pose = loaded[0]
    assert first_timestamp == pytest.approx(0.0)
    np.testing.assert_allclose(first_pose.as_matrix(), np.eye(4), atol=1e-6)
    np.testing.assert_allclose(loaded[1][1].as_matrix(), rotated, atol=1e-6)


def test_render_trajectory_views_writes_frames(tmp_path: Path) -> None:
    points, colors = _plane_cloud()
    renderer = PointCloudRenderer(points, colors)
    output_dir = tmp_path / "frames"
    paths = render_trajectory_views(
        renderer,
        intrinsics=_INTRINSICS,
        poses=[_IDENTITY_POSE, _IDENTITY_POSE],
        output_dir=output_dir,
    )
    assert [path.name for path in paths] == ["000000.png", "000001.png"]
    assert all(path.exists() for path in paths)
