"""Repo-owned Rerun helpers built against the pinned `rerun-sdk==0.24.1` API."""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import open3d as o3d
import rerun as rr  # type: ignore[import-not-found]
import rerun.blueprint as rrb  # type: ignore[import-not-found]
from pytransform3d.rotations import quaternion_from_matrix

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors

_LOGGER = logging.getLogger(__name__)

ROOT_WORLD_ENTITY_PATH = "world"
"""Canonical root entity path for repo-owned Rerun recordings."""
ROOT_WORLD_AXIS_LENGTH = 1.0
"""Visible axis length for the static root-world transform marker."""
SLAM_WORLD_ENTITY_PATH = "world/slam"
"""SLAM world root under the canonical Rerun world."""
SLAM_WORLD_AXIS_LENGTH = 0.25
"""Visible axis length for the fixed SLAM-origin marker."""
TRAJECTORY_START_AXIS_LENGTH = 0.18
"""Visible axis length for trajectory start-frame markers."""
MODEL_RGB_2D_ENTITY_PATH = "world/slam/live/model/diag/rgb"
"""Dedicated 2D-only live model RGB entity, separate from the 3D camera branch."""
GROUND_PLANE_ENTITY_PATH = "world/slam/alignment/ground_plane"
"""Root entity path for the derived dominant ground-plane visualization."""
EVALUATION_ENTITY_PATH = "world/evaluation/trajectory"
"""Root entity path for persisted trajectory-evaluation diagnostics."""
LIVE_MODEL_IMAGE_PLANE_DISTANCE = 0.35
"""Image-plane distance for the latest live model camera branch."""
KEYFRAME_IMAGE_PLANE_DISTANCE = 0.04
"""Image-plane distance for persistent historical keyframe frusta."""
SOURCE_IMAGE_PLANE_DISTANCE = 0.12
"""Image-plane distance for source camera frusta."""
POINT_CLOUD_RADII = 0.02
"""Default point cloud radii for repo-owned Rerun recordings."""
TRAJECTORY_LINE_RADII = 0.01
"""Default trajectory line radii for repo-owned Rerun recordings."""
GROUND_PLANE_OUTLINE_RADII = 0.02
"""Default outline radii for the derived ground-plane patch."""
GROUND_PLANE_FILL_RGBA = np.array([[80, 180, 120, 96]] * 4, dtype=np.uint8)
"""Semi-transparent per-vertex color for the ground-plane mesh patch."""
GROUND_PLANE_OUTLINE_RGBA = np.array([[24, 140, 84, 255]], dtype=np.uint8)
"""Opaque outline color for the ground-plane patch."""


def _rgb(hex_color: str) -> np.ndarray:
    stripped = hex_color.removeprefix("#")
    return np.array([int(stripped[index : index + 2], 16) for index in range(0, 6, 2)], dtype=np.uint8)


GT_GREEN_RGB = _rgb("#0f9d58")
ARKIT_REFERENCE_RGB = _rgb("#43a047")
ARCORE_REFERENCE_RGB = _rgb("#00897b")
SLAM_RAW_RGB = _rgb("#1368ce")
SLAM_ALIGNED_RGB = _rgb("#7b1fa2")
APE_LOW_RGB = _rgb("#2a9d8f")
APE_HIGH_RGB = _rgb("#c62828")
CORRESPONDENCE_RGB = _rgb("#ef6c00")
REFERENCE_SOURCE_COLORS_RGB = {
    "ground_truth": GT_GREEN_RGB,
    "gt": GT_GREEN_RGB,
    "arkit": ARKIT_REFERENCE_RGB,
    "arcore": ARCORE_REFERENCE_RGB,
}
"""Stable reference-source colors shared by Rerun trajectory diagnostics."""
DEFAULT_3D_SCENE_CONTENTS = (
    "+ world/slam/alignment/**",
    "+ world/evaluation/**",
    "+ world/reference/trajectory/**",
    "+ world/reference/points/**",
    "+ world/reconstruction/**",
    "+ world/slam",
    "+ world/slam/live/tracking/**",
    "+ world/slam/live/model",
    "+ world/slam/live/model/camera/image",
    "- world/slam/live/model/camera/image/depth",
    "- world/slam/live/model/camera/image/depth/**",
    "- world/slam/live/model/points",
    "- world/slam/live/model/points/**",
    "+ world/slam/keyframes/cameras/**",
    "+ world/slam/keyframes/points/**",
    "+ world/slam/point_cloud/raw",
    "+ world/slam/trajectory/raw/**",
    "+ world/aligned/**",
    "+ world/live/source/camera",
)
"""Default 3D view query: spatial map/history only, without 2D raster branches."""


class RerunEntityPaths:
    """Central entity tree used by repo-owned Rerun logging and blueprints."""

    root_world = ROOT_WORLD_ENTITY_PATH
    slam_world = SLAM_WORLD_ENTITY_PATH
    model_rgb_2d = MODEL_RGB_2D_ENTITY_PATH
    model_camera_image = "world/slam/live/model/camera/image"
    model_camera_depth = "world/slam/live/model/camera/image/depth"
    source_rgb = "world/live/source/rgb"
    source_camera_image = "world/live/source/camera/image"
    diagnostic_preview = "world/slam/live/model/diag/preview"
    default_3d_scene_contents = DEFAULT_3D_SCENE_CONTENTS

    @staticmethod
    def evaluation_metric_root(metric_id: str, reference_source: str) -> str:
        return f"{EVALUATION_ENTITY_PATH}/{_entity_token(reference_source)}/{_entity_token(metric_id)}"


RERUN_ENTITY_PATHS = RerunEntityPaths()
"""Shared entity registry for logging and blueprint construction."""


def build_default_blueprint(
    *,
    show_source_rgb: bool = False,
    show_diagnostic_preview: bool = False,
) -> rrb.Blueprint:
    """Build the default repo-owned Rerun blueprint."""
    views = [
        rrb.Spatial2DView(
            origin=RERUN_ENTITY_PATHS.model_rgb_2d,
            contents=RERUN_ENTITY_PATHS.model_rgb_2d,
            name="Model RGB",
        ),
        rrb.Spatial2DView(
            origin=RERUN_ENTITY_PATHS.model_camera_image,
            contents=RERUN_ENTITY_PATHS.model_camera_depth,
            name="Model Depth",
        ),
    ]
    if show_source_rgb:
        views.insert(
            0,
            rrb.Spatial2DView(
                origin=RERUN_ENTITY_PATHS.source_rgb,
                contents=RERUN_ENTITY_PATHS.source_rgb,
                name="Source RGB",
            ),
        )
        views.insert(
            1,
            rrb.Spatial2DView(
                origin=RERUN_ENTITY_PATHS.source_camera_image,
                contents=RERUN_ENTITY_PATHS.source_camera_image,
                name="Source Camera",
            ),
        )
    if show_diagnostic_preview:
        views.append(
            rrb.Spatial2DView(
                origin=RERUN_ENTITY_PATHS.diagnostic_preview,
                contents=RERUN_ENTITY_PATHS.diagnostic_preview,
                name="Preview",
            )
        )
    return rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial3DView(
                origin=RERUN_ENTITY_PATHS.root_world,
                name="3D Scene",
                contents=list(RERUN_ENTITY_PATHS.default_3d_scene_contents),
            ),
            rrb.Tabs(*views, name="2D Views"),
        ),
    )


def create_recording_stream(
    *,
    app_id: str,
    recording_id: str | None = None,
    show_source_rgb: bool = False,
    show_diagnostic_preview: bool = False,
    view_coordinates: str = "RDF",
) -> rr.RecordingStream:
    """Create one explicit Rerun recording stream."""
    stream = rr.RecordingStream(application_id=app_id, recording_id=recording_id)
    blueprint = build_default_blueprint(
        show_source_rgb=show_source_rgb,
        show_diagnostic_preview=show_diagnostic_preview,
    )
    stream.send_blueprint(blueprint)
    log_root_world_transform(stream, view_coordinates=view_coordinates)
    log_slam_world_transform(stream)
    return stream


def log_root_world_transform(
    recording_stream: rr.RecordingStream,
    *,
    view_coordinates: str = "RDF",
) -> None:
    """Declare one explicit world root for repo-owned recordings.

    The root stays geometrically neutral via an identity ``Transform3D`` while
    using ``axis_length`` to keep one visible world-frame marker at the origin.
    It also declares ``world`` with the requested ``view_coordinates`` so the 3D
    viewer/grid matches the logged scene semantics.
    """
    log_transform_axes(
        recording_stream,
        entity_path=ROOT_WORLD_ENTITY_PATH,
        axis_length=ROOT_WORLD_AXIS_LENGTH,
        static=True,
    )
    recording_stream.log(ROOT_WORLD_ENTITY_PATH, _view_coordinates_from_name(view_coordinates), static=True)


def log_slam_world_transform(recording_stream: rr.RecordingStream) -> None:
    """Declare one fixed SLAM-origin marker without moving child SLAM geometry."""
    log_transform_axes(
        recording_stream,
        entity_path=SLAM_WORLD_ENTITY_PATH,
        axis_length=SLAM_WORLD_AXIS_LENGTH,
        static=True,
    )


def _view_coordinates_from_name(view_coordinates: str) -> rr.components.ViewCoordinates:
    match view_coordinates:
        case "RDF":
            return rr.ViewCoordinates.RDF
        case "RFU":
            return rr.ViewCoordinates.RFU
        case _:
            raise ValueError(f"Unsupported Rerun view_coordinates '{view_coordinates}'. Expected 'RDF' or 'RFU'.")


def attach_recording_sinks(
    recording_stream: rr.RecordingStream,
    *,
    grpc_url: str | None = None,
    target_path: Path | None = None,
) -> None:
    """Configure all requested Rerun sinks on one recording stream."""
    if target_path is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            target_path.unlink()
    if grpc_url is not None and target_path is not None:
        recording_stream.set_sinks(rr.GrpcSink(grpc_url), rr.FileSink(str(target_path)))
        return
    if grpc_url is not None:
        recording_stream.set_sinks(rr.GrpcSink(grpc_url))
        return
    if target_path is not None:
        recording_stream.set_sinks(rr.FileSink(str(target_path)))
        return


def log_sim3_transform(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    rotation_matrix: np.ndarray,
    translation_xyz: np.ndarray,
    scale: float = 1.0,
    axis_length: float | None = None,
    static: bool = False,
) -> None:
    """Log one explicit Sim(3) transform (rotation, translation, and scale)."""
    log_transform_axes(
        recording_stream,
        entity_path=entity_path,
        translation_xyz=translation_xyz,
        rotation_matrix=rotation_matrix,
        scale=scale,
        relation=rr.TransformRelation.ParentFromChild,
        axis_length=axis_length,
        static=static,
    )


def log_transform_axes(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    translation_xyz: np.ndarray | list[float] | None = None,
    quaternion_xyzw: np.ndarray | list[float] | None = None,
    rotation_matrix: np.ndarray | None = None,
    scale: float | None = None,
    relation: rr.TransformRelation | None = None,
    axis_length: float | None = None,
    static: bool = False,
) -> None:
    """Log one Transform3D axes marker using the repo-owned transform convention."""
    if quaternion_xyzw is not None and rotation_matrix is not None:
        raise ValueError("Specify either quaternion_xyzw or rotation_matrix, not both.")
    transform_kwargs = {}
    if translation_xyz is not None:
        transform_kwargs["translation"] = np.asarray(translation_xyz, dtype=np.float32).tolist()
    if quaternion_xyzw is not None:
        transform_kwargs["quaternion"] = rr.Quaternion(xyzw=np.asarray(quaternion_xyzw, dtype=np.float64).tolist())
    if rotation_matrix is not None:
        transform_kwargs["rotation"] = rr.Quaternion(
            xyzw=quaternion_from_matrix(rotation_matrix)[[1, 2, 3, 0]].tolist()
        )
    if scale is not None:
        transform_kwargs["scale"] = scale
    if relation is not None:
        transform_kwargs["relation"] = relation
    transform_kwargs["axis_length"] = axis_length
    recording_stream.log(
        entity_path,
        rr.Transform3D(**transform_kwargs),
        static=static,
    )


def log_transform(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    transform: FrameTransform,
    axis_length: float | None = None,
    static: bool = False,
) -> None:
    """Log one explicit transform using repo-owned direction semantics."""
    log_transform_axes(
        recording_stream,
        entity_path=entity_path,
        translation_xyz=transform.translation_xyz(),
        quaternion_xyzw=transform.quaternion_xyzw(),
        relation=rr.TransformRelation.ParentFromChild,
        axis_length=axis_length,
        static=static,
    )


def log_pinhole(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    intrinsics: CameraIntrinsics,
    image_plane_distance: float | None = None,
) -> None:
    """Log one pinhole camera model using repo-owned intrinsics semantics."""
    if intrinsics.width_px is None or intrinsics.height_px is None:
        raise ValueError("Rerun pinhole logging requires explicit image width and height.")
    recording_stream.log(
        entity_path,
        rr.Pinhole(
            image_from_camera=intrinsics.as_matrix(),
            resolution=[intrinsics.width_px, intrinsics.height_px],
            camera_xyz=rr.ViewCoordinates.RDF,
            image_plane_distance=image_plane_distance,
        ),
    )


def log_rgb_image(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    image_rgb: np.ndarray,
) -> None:
    """Log one RGB image to the viewer."""
    recording_stream.log(entity_path, rr.Image(np.asarray(image_rgb)))


def log_depth_image(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    depth_m: np.ndarray,
) -> None:
    """Log one metric depth image to the viewer."""
    recording_stream.log(entity_path, rr.DepthImage(np.asarray(depth_m, dtype=np.float32), meter=1.0))


def log_pointcloud(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    pointmap: np.ndarray,
    colors: np.ndarray | None = None,
    point_cloud_radii: float = POINT_CLOUD_RADII,
    decimation_keep_ratio: float = 1.0,
    decimation_seed: int = 0,
) -> None:
    """Log one point cloud payload without reinterpreting its frame semantics.

    The current ViSTA live path uses this helper for camera-local pointmaps
    that inherit world placement from a posed parent entity. Exported
    world-space dense clouds are a different product surface and should be
    logged on world-space branches directly instead of being treated as the same
    payload type.
    """
    positions = np.asarray(pointmap).reshape(-1, 3)
    valid_mask = (positions[:, 2] > 0) & np.isfinite(positions[:, 2])
    valid_positions = positions[valid_mask]

    if len(valid_positions) == 0:
        return

    valid_colors = None
    if colors is not None:
        c = np.asarray(colors).reshape(-1, 3)
        if len(c) == len(positions):
            valid_colors = c[valid_mask]

    valid_positions, valid_colors = _decimate_rows(
        valid_positions,
        valid_colors,
        keep_ratio=decimation_keep_ratio,
        seed=decimation_seed,
    )

    recording_stream.log(
        entity_path,
        rr.Points3D(positions=valid_positions, colors=valid_colors, radii=point_cloud_radii),
    )


def log_arrows3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    origins_xyz: np.ndarray,
    vectors_xyz: np.ndarray,
    colors_rgba: np.ndarray | None = None,
    radii: float = 0.01,
    static: bool = False,
) -> None:
    """Log one or more 3D arrows."""
    recording_stream.log(
        entity_path,
        rr.Arrows3D(
            origins=np.asarray(origins_xyz, dtype=np.float32).reshape(-1, 3),
            vectors=np.asarray(vectors_xyz, dtype=np.float32).reshape(-1, 3),
            colors=None if colors_rgba is None else np.asarray(colors_rgba, dtype=np.uint8),
            radii=[radii],
        ),
        static=static,
    )


def log_line_strip3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    positions_xyz: np.ndarray,
    radii: float = TRAJECTORY_LINE_RADII,
    color_rgb: np.ndarray | None = None,
    static: bool = False,
) -> None:
    """Log one 3D line strip to the viewer."""
    positions = np.asarray(positions_xyz, dtype=np.float32).reshape(-1, 3)
    if len(positions) == 0:
        return
    colors = None if color_rgb is None else np.asarray(color_rgb, dtype=np.uint8).reshape(1, 3)
    recording_stream.log(entity_path, rr.LineStrips3D([positions], radii=[radii], colors=colors), static=static)


def log_scalar_series(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    timestamps_s: np.ndarray,
    values: np.ndarray,
    timeline: str = "trajectory_time",
    static: bool = False,
) -> None:
    """Log one timestamped scalar series."""
    timestamps = np.asarray(timestamps_s, dtype=np.float64).reshape(-1)
    scalars = np.asarray(values, dtype=np.float64).reshape(-1)
    if len(timestamps) != len(scalars):
        raise ValueError(f"Expected matching scalar timestamps and values, got {len(timestamps)} and {len(scalars)}.")
    previous_timeline = None
    for timestamp_s, value in zip(timestamps, scalars, strict=True):
        recording_stream.set_time(timeline, timestamp=float(timestamp_s))
        recording_stream.log(entity_path, rr.Scalars([float(value)]), static=static)
        previous_timeline = timeline
    if previous_timeline is not None:
        recording_stream.reset_time()


def log_correspondence_strips3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    reference_positions_xyz: np.ndarray,
    estimate_positions_xyz: np.ndarray,
    radii: float = TRAJECTORY_LINE_RADII * 0.5,
    color_rgb: np.ndarray = CORRESPONDENCE_RGB,
    static: bool = True,
) -> None:
    """Log pairwise reference-to-estimate correspondence strips."""
    reference_positions = np.asarray(reference_positions_xyz, dtype=np.float32).reshape(-1, 3)
    estimate_positions = np.asarray(estimate_positions_xyz, dtype=np.float32).reshape(-1, 3)
    pair_count = min(len(reference_positions), len(estimate_positions))
    if pair_count == 0:
        return
    strips = np.stack([reference_positions[:pair_count], estimate_positions[:pair_count]], axis=1)
    colors = np.repeat(np.asarray(color_rgb, dtype=np.uint8).reshape(1, 3), pair_count, axis=0)
    recording_stream.log(entity_path, rr.LineStrips3D(strips, radii=[radii], colors=colors), static=static)


def _ape_error_colors(error_values: np.ndarray) -> np.ndarray:
    values = np.asarray(error_values, dtype=np.float64).reshape(-1)
    if len(values) == 0:
        return np.empty((0, 3), dtype=np.uint8)
    min_error = float(np.min(values))
    max_error = float(np.max(values))
    if max_error == min_error:
        weights = np.zeros_like(values)
    else:
        weights = (values - min_error) / (max_error - min_error)
    low = APE_LOW_RGB.astype(np.float64)
    high = APE_HIGH_RGB.astype(np.float64)
    return np.clip(low + (high - low) * weights[:, None], 0, 255).astype(np.uint8)


def log_mesh3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    vertex_positions_xyz: np.ndarray,
    triangle_indices: np.ndarray,
    vertex_colors_rgba: np.ndarray | None = None,
    static: bool = False,
) -> None:
    """Log one 3D triangle mesh."""
    positions = np.asarray(vertex_positions_xyz, dtype=np.float32).reshape(-1, 3)
    triangles = np.asarray(triangle_indices, dtype=np.uint32).reshape(-1, 3)
    color_payload = None if vertex_colors_rgba is None else np.asarray(vertex_colors_rgba, dtype=np.uint8)
    recording_stream.log(
        entity_path,
        rr.Mesh3D(
            vertex_positions=positions,
            triangle_indices=triangles,
            vertex_colors=color_payload,
        ),
        static=static,
    )


def log_ground_plane_patch(
    recording_stream: rr.RecordingStream,
    *,
    metadata: GroundAlignmentMetadata,
    static: bool = True,
) -> None:
    """Log the detected ground-plane patch as a filled mesh plus outline."""
    if metadata.visualization is None or not metadata.visualization.corners_xyz_world:
        return
    corners_xyz_world = np.asarray(metadata.visualization.corners_xyz_world, dtype=np.float32).reshape(-1, 3)
    if corners_xyz_world.shape != (4, 3):
        raise ValueError(f"Expected four ground-plane corners, got shape {corners_xyz_world.shape}.")
    if metadata.ground_plane_world is not None:
        normal_xyz_world = np.asarray(metadata.ground_plane_world.normal_xyz_world, dtype=np.float32)
    else:
        normal_xyz_world = np.cross(
            corners_xyz_world[1] - corners_xyz_world[0], corners_xyz_world[2] - corners_xyz_world[0]
        )
    first_triangle = np.array([0, 1, 2], dtype=np.uint32)
    first_normal = np.cross(corners_xyz_world[1] - corners_xyz_world[0], corners_xyz_world[2] - corners_xyz_world[0])
    if float(np.dot(first_normal, normal_xyz_world)) < 0.0:
        first_triangle = np.array([0, 2, 1], dtype=np.uint32)
    triangle_indices = np.stack([first_triangle, np.array([0, 2, 3], dtype=np.uint32)], axis=0)
    log_mesh3d(
        recording_stream,
        entity_path=f"{GROUND_PLANE_ENTITY_PATH}/fill",
        vertex_positions_xyz=corners_xyz_world,
        triangle_indices=triangle_indices,
        vertex_colors_rgba=GROUND_PLANE_FILL_RGBA,
        static=static,
    )
    loop_xyz_world = np.concatenate([corners_xyz_world, corners_xyz_world[:1]], axis=0)
    recording_stream.log(
        f"{GROUND_PLANE_ENTITY_PATH}/outline",
        rr.LineStrips3D(
            [loop_xyz_world],
            radii=[GROUND_PLANE_OUTLINE_RADII],
            colors=GROUND_PLANE_OUTLINE_RGBA,
        ),
        static=static,
    )
    # Log the normal vector as an arrow from the center of the patch.
    center_xyz_world = np.mean(corners_xyz_world, axis=0)
    log_arrows3d(
        recording_stream,
        entity_path=f"{GROUND_PLANE_ENTITY_PATH}/normal",
        origins_xyz=center_xyz_world,
        vectors_xyz=normal_xyz_world * 0.5,
        colors_rgba=np.array([[255, 255, 0, 255]], dtype=np.uint8),
        static=static,
    )


def log_clear(recording_stream: rr.RecordingStream, *, entity_path: str, recursive: bool) -> None:
    """Clear one entity subtree from latest-at viewer queries."""
    recording_stream.log(entity_path, rr.Clear(recursive=recursive))


def log_points3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    points_xyz: np.ndarray,
    colors: np.ndarray | None = None,
    radii: float = POINT_CLOUD_RADII,
    static: bool = False,
    decimation_keep_ratio: float = 1.0,
    decimation_seed: int = 0,
) -> None:
    """Log explicit XYZ rows to the viewer."""
    positions = np.asarray(points_xyz, dtype=np.float32).reshape(-1, 3)
    if len(positions) == 0:
        return
    color_payload = None if colors is None else np.asarray(colors)
    positions, color_payload = _decimate_rows(
        positions,
        color_payload,
        keep_ratio=decimation_keep_ratio,
        seed=decimation_seed,
    )
    recording_stream.log(
        entity_path, rr.Points3D(positions=positions, colors=color_payload, radii=radii), static=static
    )


def log_pointcloud_ply(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    path: Path,
    decimation_keep_ratio: float = 1.0,
    decimation_seed: int = 0,
) -> None:
    """Load and log one world-space PLY point cloud artifact."""
    points_xyz, colors = load_point_cloud_ply_with_colors(path)
    log_points3d(
        recording_stream,
        entity_path=entity_path,
        points_xyz=points_xyz,
        colors=colors,
        static=True,
        decimation_keep_ratio=decimation_keep_ratio,
        decimation_seed=decimation_seed,
    )


def log_mesh_ply(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    path: Path,
    decimation_keep_ratio: float = 1.0,
) -> None:
    """Load and log one world-space PLY triangle mesh artifact."""
    _validate_decimation_keep_ratio(decimation_keep_ratio)
    if not path.exists():
        raise FileNotFoundError(f"Mesh artifact '{path}' does not exist.")
    mesh = o3d.io.read_triangle_mesh(path)
    triangle_count = len(mesh.triangles)
    if decimation_keep_ratio < 1.0 and triangle_count > 0:
        target_triangle_count = max(1, int(np.floor(triangle_count * decimation_keep_ratio)))
        if target_triangle_count < triangle_count:
            mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangle_count)
    vertices_xyz = np.asarray(mesh.vertices, dtype=np.float32)
    triangles = np.asarray(mesh.triangles, dtype=np.uint32)
    if vertices_xyz.ndim != 2 or vertices_xyz.shape[1] != 3:
        raise ValueError(f"Expected mesh vertices with shape (N, 3), got {vertices_xyz.shape}.")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError(f"Expected mesh triangles with shape (N, 3), got {triangles.shape}.")
    if len(vertices_xyz) == 0 or len(triangles) == 0:
        return
    vertex_colors = None
    if mesh.has_vertex_colors():
        colors = np.asarray(mesh.vertex_colors, dtype=np.float32)
        vertex_colors = np.clip(colors * 255.0, 0.0, 255.0).astype(np.uint8)
    log_mesh3d(
        recording_stream,
        entity_path=entity_path,
        vertex_positions_xyz=vertices_xyz,
        triangle_indices=triangles,
        vertex_colors_rgba=vertex_colors,
        static=True,
    )


def _decimate_rows(
    positions: np.ndarray,
    colors: np.ndarray | None,
    *,
    keep_ratio: float,
    seed: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    _validate_decimation_keep_ratio(keep_ratio)
    if keep_ratio >= 1.0 or len(positions) == 0:
        return positions, colors
    keep_count = max(1, int(np.floor(len(positions) * keep_ratio)))
    if keep_count >= len(positions):
        return positions, colors
    rng = np.random.default_rng(seed)
    indices = np.sort(rng.choice(len(positions), size=keep_count, replace=False))
    sampled_colors = None if colors is None else np.asarray(colors)[indices]
    return positions[indices], sampled_colors


def _validate_decimation_keep_ratio(keep_ratio: float) -> None:
    if not 0.0 < keep_ratio <= 1.0:
        raise ValueError(f"Expected decimation keep ratio in (0, 1], got {keep_ratio}.")


def _entity_token(value: str) -> str:
    stripped = value.strip().replace(" ", "_")
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in stripped) or "reference"


def collect_native_visualization_artifacts(
    *,
    native_output_dir: Path,
    preserve_native_rerun: bool,
) -> VisualizationArtifacts | None:
    """Collect visualization-owned artifacts produced by an external backend."""
    if not native_output_dir.exists():
        return None
    native_rerun_path = native_output_dir / "rerun_recording.rrd"
    return VisualizationArtifacts(
        native_rerun_rrd=(
            None
            if not preserve_native_rerun or not native_rerun_path.exists()
            else ArtifactRef(
                path=native_rerun_path.resolve(),
                kind="rrd",
                fingerprint=f"{native_rerun_path.name}-native",
            )
        ),
        native_output_dir=ArtifactRef(
            path=native_output_dir.resolve(),
            kind="dir",
            fingerprint=f"{native_output_dir.name}-native-output",
        ),
    )


def merge_recordings(*, target_path: Path, overlay_path: Path) -> None:
    """Merge one overlay recording into an existing target recording."""
    rerun_bin = shutil.which("rerun")
    if rerun_bin is None:
        candidate = Path(sys.executable).with_name("rerun")
        rerun_bin = str(candidate) if candidate.exists() else None
    if rerun_bin is None:
        raise RuntimeError("Could not locate the `rerun` CLI needed to merge overlay recordings.")
    if not target_path.exists():
        raise FileNotFoundError(f"Target Rerun recording does not exist: '{target_path}'.")
    if not overlay_path.exists():
        raise FileNotFoundError(f"Overlay Rerun recording does not exist: '{overlay_path}'.")
    with tempfile.NamedTemporaryFile(suffix=".rrd", delete=False, dir=target_path.parent) as handle:
        merged_path = Path(handle.name)
    try:
        subprocess.run(
            [rerun_bin, "rrd", "merge", "-o", str(merged_path), str(target_path), str(overlay_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        merged_path.replace(target_path)
    finally:
        if merged_path.exists():
            merged_path.unlink()


def augment_viewer_recording_with_ground_plane(
    *,
    metadata: GroundAlignmentMetadata,
    viewer_recording_path: Path,
    recording_id: str,
) -> None:
    """Merge a ground-plane overlay into the repo-owned viewer recording."""
    if metadata.visualization is None or not metadata.visualization.corners_xyz_world:
        return
    overlay_stream = rr.RecordingStream(application_id="prml-vslam", recording_id=recording_id)
    log_ground_plane_patch(overlay_stream, metadata=metadata)
    overlay_bytes = overlay_stream.memory_recording().drain_as_bytes()
    with tempfile.NamedTemporaryFile(suffix=".rrd", delete=False, dir=viewer_recording_path.parent) as handle:
        overlay_path = Path(handle.name)
    try:
        overlay_path.write_bytes(overlay_bytes)
        merge_recordings(target_path=viewer_recording_path, overlay_path=overlay_path)
    finally:
        if overlay_path.exists():
            overlay_path.unlink()


__all__ = [
    "augment_viewer_recording_with_ground_plane",
    "attach_recording_sinks",
    "build_default_blueprint",
    "collect_native_visualization_artifacts",
    "create_recording_stream",
    "GROUND_PLANE_ENTITY_PATH",
    "GT_GREEN_RGB",
    "KEYFRAME_IMAGE_PLANE_DISTANCE",
    "LIVE_MODEL_IMAGE_PLANE_DISTANCE",
    "log_depth_image",
    "log_clear",
    "log_arrows3d",
    "log_correspondence_strips3d",
    "log_line_strip3d",
    "log_ground_plane_patch",
    "log_mesh3d",
    "log_mesh_ply",
    "log_pinhole",
    "log_pointcloud",
    "log_pointcloud_ply",
    "log_points3d",
    "log_rgb_image",
    "log_root_world_transform",
    "log_scalar_series",
    "log_slam_world_transform",
    "log_transform",
    "log_transform_axes",
    "REFERENCE_SOURCE_COLORS_RGB",
    "RERUN_ENTITY_PATHS",
    "ROOT_WORLD_ENTITY_PATH",
    "SLAM_ALIGNED_RGB",
    "SLAM_RAW_RGB",
    "SLAM_WORLD_AXIS_LENGTH",
    "SLAM_WORLD_ENTITY_PATH",
    "SOURCE_IMAGE_PLANE_DISTANCE",
    "TRAJECTORY_START_AXIS_LENGTH",
]
