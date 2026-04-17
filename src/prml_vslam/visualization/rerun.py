"""Repo-owned Rerun helpers built against the pinned `rerun-sdk==0.24.1` API."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rerun as rr  # type: ignore[import-not-found]
import rerun.blueprint as rrb  # type: ignore[import-not-found]

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.visualization.contracts import VisualizationArtifacts


def create_recording_stream(*, app_id: str, recording_id: str | None = None) -> rr.RecordingStream:
    """Create one explicit Rerun recording stream."""
    stream = rr.RecordingStream(application_id=app_id, recording_id=recording_id)
    blueprint = rrb.Blueprint(
        rrb.Horizontal(
            rrb.Spatial3DView(origin="world", name="3D Scene"),
            rrb.Spatial2DView(origin="world/live/camera/cam", name="Live Camera"),
        ),
    )
    stream.send_blueprint(blueprint)
    stream.log("world", rr.ViewCoordinates.RDF, static=True)
    return stream


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
) -> None:
    """Log a point cloud (and optionally colors) to the viewer."""
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
        rr.Points3D(positions=valid_positions, colors=valid_colors, radii=0.05),
    )


def log_points3d(
    recording_stream: rr.RecordingStream,
    *,
    entity_path: str,
    points_xyz: np.ndarray,
    colors: np.ndarray | None = None,
    radii: float = 0.05,
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


__all__ = [
    "attach_recording_sinks",
    "collect_native_visualization_artifacts",
    "create_recording_stream",
    "log_depth_image",
    "log_pinhole",
    "log_pointcloud",
    "log_points3d",
    "log_rgb_image",
    "log_transform",
]
