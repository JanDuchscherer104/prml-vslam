"""Repo-owned Rerun helpers built against the pinned `rerun-sdk==0.24.1` API."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import rerun as rr  # type: ignore[import-not-found]
import rerun.blueprint as rrb  # type: ignore[import-not-found]

from prml_vslam.interfaces.alignment import GroundAlignmentMetadata
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.interfaces.visualization import VisualizationArtifacts

ROOT_WORLD_ENTITY_PATH = "world"
"""Canonical root entity path for repo-owned Rerun recordings."""
ROOT_WORLD_AXIS_LENGTH = 1.0
"""Visible axis length for the static root-world transform marker."""
MODEL_RGB_2D_ENTITY_PATH = "world/live/model/diag/rgb"
"""Dedicated 2D-only live model RGB entity, separate from the 3D camera branch."""
GROUND_PLANE_ENTITY_PATH = "world/alignment/ground_plane"
"""Root entity path for the derived dominant ground-plane visualization."""
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


def build_default_blueprint() -> rrb.Blueprint:
    """Build the default repo-owned Rerun blueprint."""
    return rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial3DView(
                origin="world",
                name="3D Scene",
                contents=[
                    "+ world/alignment/**",
                    "+ world/live/tracking/**",
                    "+ world/live/model/camera/**",
                    "- world/live/model/camera/image/depth",
                    "- world/live/model/camera/image/depth/**",
                    "- world/live/model/points",
                    "- world/live/model/points/**",
                    "- world/keyframes/cameras/**",
                    "+ world/keyframes/points/**",
                    "+ world/trajectory/tracking",
                ],
            ),
            rrb.Tabs(
                rrb.Spatial2DView(
                    origin="world/live/source/rgb",
                    contents="world/live/source/rgb",
                    name="Source RGB",
                ),
                rrb.Spatial2DView(
                    origin=MODEL_RGB_2D_ENTITY_PATH,
                    contents=MODEL_RGB_2D_ENTITY_PATH,
                    name="Model RGB",
                ),
                rrb.Spatial2DView(
                    origin="world/live/model/camera/image",
                    contents="world/live/model/camera/image/depth",
                    name="Model Depth",
                ),
                rrb.Spatial2DView(
                    origin="world/live/model/diag/preview",
                    contents="world/live/model/diag/preview",
                    name="Preview",
                ),
                name="2D Views",
            ),
        ),
    )


def create_recording_stream(*, app_id: str, recording_id: str | None = None) -> rr.RecordingStream:
    """Create one explicit Rerun recording stream."""
    stream = rr.RecordingStream(application_id=app_id, recording_id=recording_id)
    blueprint = build_default_blueprint()
    stream.send_blueprint(blueprint)
    log_root_world_transform(stream)
    return stream


def log_root_world_transform(recording_stream: rr.RecordingStream) -> None:
    """Declare one explicit ViSTA-aligned world root for repo-owned recordings.

    The root stays geometrically neutral via an identity ``Transform3D`` while
    using ``axis_length`` to keep one visible world-frame marker at the origin.
    It also declares ``world`` as ``ViewCoordinates.RDF`` so the 3D viewer/grid
    uses the same right/down/forward semantics as the logged ViSTA-native
    scene. This does not rotate or normalize the data; it only makes the
    existing world basis explicit to the viewer.
    """
    recording_stream.log(
        ROOT_WORLD_ENTITY_PATH,
        rr.Transform3D(axis_length=ROOT_WORLD_AXIS_LENGTH),
        static=True,
    )
    recording_stream.log(ROOT_WORLD_ENTITY_PATH, rr.ViewCoordinates.RDF, static=True)


def attach_recording_sinks(
    recording_stream: rr.RecordingStream,
    *,
    grpc_url: str | None = None,
    target_path: Path | None = None,
) -> None:
    """Configure all requested Rerun sinks on one recording stream."""
    sinks: list[object] = []
    if grpc_url is not None:
        sinks.append(rr.GrpcSink(grpc_url))
    if target_path is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if target_path.exists():
            target_path.unlink()
        sinks.append(rr.FileSink(str(target_path)))
    if not sinks:
        return
    recording_stream.set_sinks(*sinks)


def log_transform(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    transform: FrameTransform,
    axis_length: float | None = None,
) -> None:
    """Log one explicit transform using repo-owned direction semantics."""
    translation = transform.translation_xyz().tolist()
    quaternion = transform.quaternion_xyzw().tolist()
    recording_stream.log(
        entity_path,
        rr.Transform3D(
            translation=translation,
            quaternion=rr.Quaternion(xyzw=quaternion),
            relation=rr.TransformRelation.ParentFromChild,
            axis_length=axis_length,
        ),
    )


def log_pinhole(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    intrinsics: CameraIntrinsics,
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

    recording_stream.log(
        entity_path,
        rr.Points3D(positions=valid_positions, colors=valid_colors, radii=point_cloud_radii),
    )


def log_line_strip3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    positions_xyz: np.ndarray,
    radii: float = TRAJECTORY_LINE_RADII,
) -> None:
    """Log one 3D line strip to the viewer."""
    positions = np.asarray(positions_xyz, dtype=np.float32).reshape(-1, 3)
    if len(positions) == 0:
        return
    recording_stream.log(entity_path, rr.LineStrips3D([positions], radii=[radii]))


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
) -> None:
    """Log explicit XYZ rows to the viewer."""
    positions = np.asarray(points_xyz, dtype=np.float32).reshape(-1, 3)
    if len(positions) == 0:
        return
    color_payload = None if colors is None else np.asarray(colors)
    recording_stream.log(entity_path, rr.Points3D(positions=positions, colors=color_payload, radii=radii))


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
    "log_depth_image",
    "log_clear",
    "log_line_strip3d",
    "log_ground_plane_patch",
    "log_mesh3d",
    "log_pinhole",
    "log_pointcloud",
    "log_points3d",
    "log_rgb_image",
    "log_root_world_transform",
    "log_transform",
    "ROOT_WORLD_ENTITY_PATH",
]
