"""Headless point-cloud view rendering for image-quality evaluation.

This module rasterizes a colored world-space point cloud into an RGB-D view from
a given camera pose and intrinsics, producing the *generated* image that the
:mod:`prml_vslam.eval.image_metrics` module scores against a captured frame.

It uses Open3D's GL-free tensor projection
(:meth:`open3d.t.geometry.PointCloud.project_to_rgbd_image`) so it runs in
headless and CI environments without an OpenGL/Filament context. Sparse clouds
leave holes; every view therefore returns a ``coverage`` mask so downstream
metrics only score the pixels a point actually filled.

Frame convention: poses are ``world <- camera_rdf`` (camera-to-world), matching
:class:`prml_vslam.interfaces.transforms.FrameTransform`. The renderer is
frame-agnostic — it renders whatever world-frame the cloud and poses share — so
aligning an estimate cloud to a ground-truth frame is the caller's concern, not
the renderer's.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.rendering.contracts import RenderConfig, RenderedView
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, load_tum_trajectory

__all__ = [
    "PointCloudRenderer",
    "poses_from_tum_trajectory",
    "render_trajectory_views",
    "write_image_rgb",
]


class PointCloudRenderer:
    """Render views of one colored world-space point cloud.

    The cloud is uploaded to an Open3D tensor point cloud once on construction and
    reused across :meth:`render` calls, so rendering many poses of one cloud only
    pays the upload cost a single time.
    """

    def __init__(
        self,
        points_xyz: np.ndarray,
        colors_rgb: np.ndarray | None = None,
        *,
        config: RenderConfig | None = None,
    ) -> None:
        self.config = config or RenderConfig()
        points = np.asarray(points_xyz, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 3:
            raise ValueError(f"Expected point cloud shape (N, 3), got {points.shape}.")
        if len(points) == 0:
            raise ValueError("Cannot render an empty point cloud.")
        colors01 = self._resolve_colors(colors_rgb, point_count=len(points))
        self._point_cloud = o3d.t.geometry.PointCloud()
        self._point_cloud.point.positions = o3d.core.Tensor(points, o3d.core.float32)
        self._point_cloud.point.colors = o3d.core.Tensor(colors01, o3d.core.float32)

    @classmethod
    def from_ply(cls, path: Path, *, config: RenderConfig | None = None) -> PointCloudRenderer:
        """Build a renderer from a PLY cloud (for example ``slam/dense_points.ply``)."""
        points_xyz, colors_rgb = load_point_cloud_ply_with_colors(path)
        return cls(points_xyz, colors_rgb, config=config)

    def render(self, *, intrinsics: CameraIntrinsics, pose: FrameTransform) -> RenderedView:
        """Render one view from ``pose`` (``world <- camera``) at ``intrinsics``."""
        if intrinsics.width_px is None or intrinsics.height_px is None:
            raise ValueError("Rendering requires intrinsics with explicit width_px and height_px.")
        width = int(intrinsics.width_px)
        height = int(intrinsics.height_px)
        config = self.config

        intrinsic_tensor = o3d.core.Tensor(intrinsics.as_matrix(), o3d.core.float64)
        extrinsic_world_to_camera = np.linalg.inv(pose.as_matrix())
        extrinsic_tensor = o3d.core.Tensor(extrinsic_world_to_camera, o3d.core.float64)

        rgbd = self._point_cloud.project_to_rgbd_image(
            width,
            height,
            intrinsic_tensor,
            extrinsic_tensor,
            depth_scale=config.depth_scale,
            depth_max=config.depth_max_m,
        )
        color01 = np.asarray(rgbd.color.to_legacy(), dtype=np.float32)
        depth_scaled = np.asarray(rgbd.depth.to_legacy(), dtype=np.float32)

        rgb = np.clip(np.rint(color01 * 255.0), 0, 255).astype(np.uint8)
        coverage = depth_scaled > 0.0
        depth_m = (depth_scaled / config.depth_scale).astype(np.float32)

        if config.dilation_px > 0:
            rgb, depth_m, coverage = _hole_fill(rgb, depth_m, coverage, radius_px=config.dilation_px)

        rgb[~coverage] = np.asarray(config.background_rgb, dtype=np.uint8)
        depth_m[~coverage] = 0.0
        return RenderedView(rgb=rgb, depth_m=depth_m, coverage=coverage, intrinsics=intrinsics, pose=pose)

    def render_many(self, views: Iterable[tuple[CameraIntrinsics, FrameTransform]]) -> list[RenderedView]:
        """Render a sequence of ``(intrinsics, pose)`` views from the same cloud."""
        return [self.render(intrinsics=intrinsics, pose=pose) for intrinsics, pose in views]

    def _resolve_colors(self, colors_rgb: np.ndarray | None, *, point_count: int) -> np.ndarray:
        if colors_rgb is None:
            fallback = np.asarray(self.config.default_point_color_rgb, dtype=np.float64) / 255.0
            return np.tile(fallback.astype(np.float32), (point_count, 1))
        colors = np.asarray(colors_rgb)
        if colors.shape != (point_count, 3):
            raise ValueError(f"Expected point colors shape ({point_count}, 3), got {colors.shape}.")
        normalized = colors.astype(np.float32)
        if np.issubdtype(colors.dtype, np.integer):
            normalized = normalized / np.float32(255.0)
        elif normalized.size and float(normalized.max()) > 1.0 + 1e-4:
            # Mirror utils.geometry._normalize_point_colors: fail loud instead of
            # silently clipping a [0, 255] float cloud to white.
            raise ValueError("Float point colors must be in [0, 1]; pass uint8 for the [0, 255] convention.")
        return np.clip(normalized, 0.0, 1.0)


def _hole_fill(
    rgb: np.ndarray,
    depth_m: np.ndarray,
    coverage: np.ndarray,
    *,
    radius_px: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Coarsely fill 1-pixel gaps via morphological dilation.

    This is an approximate splat for sparse projections: per-channel dilation can
    tint hole borders, so it is opt-in and never enabled by default.
    """
    kernel = np.ones((2 * radius_px + 1, 2 * radius_px + 1), dtype=np.uint8)
    dilated_coverage = cv2.dilate(coverage.astype(np.uint8), kernel).astype(bool)
    dilated_rgb = cv2.dilate(rgb, kernel)
    dilated_depth = cv2.dilate(depth_m, kernel)
    filled = dilated_coverage & ~coverage
    rgb = np.where(filled[..., None], dilated_rgb, rgb)
    depth_m = np.where(filled, dilated_depth, depth_m).astype(np.float32)
    return rgb, depth_m, dilated_coverage


def poses_from_tum_trajectory(path: Path) -> list[tuple[float, FrameTransform]]:
    """Load a TUM trajectory into ``(timestamp_s, world <- camera_rdf)`` poses."""
    trajectory = load_tum_trajectory(path)
    positions_xyz = np.asarray(trajectory.positions_xyz, dtype=np.float64)
    quaternions_wxyz = np.asarray(trajectory.orientations_quat_wxyz, dtype=np.float64)
    timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    return [
        (
            float(timestamp),
            FrameTransform.from_quaternion_translation(
                quaternion_wxyz[[1, 2, 3, 0]],
                position,
                target_frame="world",
                source_frame="camera_rdf",
            ),
        )
        for timestamp, position, quaternion_wxyz in zip(timestamps_s, positions_xyz, quaternions_wxyz, strict=True)
    ]


def render_trajectory_views(
    renderer: PointCloudRenderer,
    *,
    intrinsics: CameraIntrinsics,
    poses: Sequence[FrameTransform],
    output_dir: Path,
) -> list[Path]:
    """Render one view per pose and write them as zero-padded PNG frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        write_image_rgb(output_dir / f"{index:06d}.png", renderer.render(intrinsics=intrinsics, pose=pose).rgb)
        for index, pose in enumerate(poses)
    ]


def write_image_rgb(path: Path, rgb: np.ndarray) -> Path:
    """Write an ``(H, W, 3)`` uint8 RGB image to disk via OpenCV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    bgr = cv2.cvtColor(np.asarray(rgb, dtype=np.uint8), cv2.COLOR_RGB2BGR)
    if not cv2.imwrite(str(path), bgr):
        raise RuntimeError(f"Failed to write image to '{path}'.")
    return path
