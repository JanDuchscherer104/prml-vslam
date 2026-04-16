"""Repo-owned Rerun helpers.

The helpers in this module intentionally use lazy imports so the repository can
keep Rerun optional until the viewer workflow is enabled in a concrete run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef
from prml_vslam.visualization.contracts import VisualizationArtifacts


def _import_rerun() -> Any:
    try:
        import rerun as rr
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Rerun support requires the optional `rerun-sdk` dependency. Install it before enabling viewer export."
        ) from exc
    return rr


def create_recording_stream(*, app_id: str, recording_id: str | None = None) -> Any:
    """Create one explicit Rerun recording stream."""
    rr = _import_rerun()
    stream = rr.RecordingStream(application_id=app_id, recording_id=recording_id)

    try:
        import rerun.blueprint as rrb  # noqa: PLC0415

        blueprint = rrb.Blueprint(
            rrb.Horizontal(
                rrb.Spatial3DView(origin="world", name="3D Scene"),
                rrb.Spatial2DView(origin="world/live_camera/preview", name="Live Preview"),
            ),
        )
        stream.send_blueprint(blueprint)
    except (ImportError, AttributeError):
        pass

    return stream


def attach_file_sink(recording_stream: Any, *, target_path: Path) -> None:
    """Attach a file sink or save path to an existing recording stream."""
    rr = _import_rerun()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(rr, "FileSink") and hasattr(recording_stream, "add_sink"):
        recording_stream.add_sink(rr.FileSink(str(target_path)))
        return
    if hasattr(recording_stream, "save"):
        recording_stream.save(str(target_path))
        return
    raise RuntimeError("The installed Rerun SDK does not expose a supported file sink API.")


def attach_grpc_sink(recording_stream: Any, *, grpc_url: str) -> None:
    """Attach a gRPC sink to an existing recording stream."""
    rr = _import_rerun()
    if hasattr(rr, "GrpcSink") and hasattr(recording_stream, "add_sink"):
        recording_stream.add_sink(rr.GrpcSink(grpc_url))
        return
    if hasattr(recording_stream, "connect_grpc"):
        recording_stream.connect_grpc(grpc_url)
        return
    raise RuntimeError("The installed Rerun SDK does not expose a supported gRPC sink API.")


def attach_recording_sinks(
    recording_stream: Any,
    *,
    grpc_url: str | None = None,
    target_path: Path | None = None,
) -> None:
    """Attach all requested Rerun sinks without replacing earlier sinks."""
    rr = _import_rerun()
    sinks: list[Any] = []
    if grpc_url is not None:
        if not hasattr(rr, "GrpcSink"):
            raise RuntimeError("The installed Rerun SDK does not expose `GrpcSink`.")
        sinks.append(rr.GrpcSink(grpc_url))
    if target_path is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if not hasattr(rr, "FileSink"):
            raise RuntimeError("The installed Rerun SDK does not expose `FileSink`.")
        sinks.append(rr.FileSink(str(target_path)))
    if not sinks:
        return
    if not hasattr(recording_stream, "set_sinks"):
        raise RuntimeError("The installed Rerun SDK does not expose the multi-sink `set_sinks` API.")
    recording_stream.set_sinks(*sinks)


def log_transform(recording_stream: Any, *, entity_path: str, transform: FrameTransform) -> None:
    """Log one explicit transform using repo-owned direction semantics."""
    rr = _import_rerun()
    translation = transform.translation_xyz().tolist()
    quaternion = transform.quaternion_xyzw().tolist()
    if not hasattr(rr, "Transform3D"):
        raise RuntimeError("The installed Rerun SDK does not expose `Transform3D`.")
    recording_stream.log(
        entity_path,
        rr.Transform3D(
            translation=translation,
            quaternion=rr.Quaternion(xyzw=quaternion),
            relation=rr.TransformRelation.ChildFromParent,
        ),
    )


def log_pointcloud(
    recording_stream: Any,
    *,
    entity_path: str,
    pointmap: np.ndarray,
    colors: np.ndarray | None = None,
) -> None:
    """Log a point cloud (and optionally colors) to the viewer."""

    rr = _import_rerun()
    if not hasattr(rr, "Points3D"):
        raise RuntimeError("The installed Rerun SDK does not expose `Points3D`.")

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
    recording_stream: Any,
    *,
    entity_path: str,
    points_xyz: np.ndarray,
    colors: np.ndarray | None = None,
    radii: float = 0.05,
) -> None:
    """Log explicit XYZ rows to the viewer."""
    rr = _import_rerun()
    if not hasattr(rr, "Points3D"):
        raise RuntimeError("The installed Rerun SDK does not expose `Points3D`.")
    positions = np.asarray(points_xyz, dtype=np.float32).reshape(-1, 3)
    if len(positions) == 0:
        return
    color_payload = None if colors is None else np.asarray(colors)
    recording_stream.log(entity_path, rr.Points3D(positions=positions, colors=color_payload, radii=radii))


def log_preview_image(recording_stream: Any, *, entity_path: str, image_rgb: np.ndarray) -> None:
    """Log an RGB image to the viewer."""
    rr = _import_rerun()
    if not hasattr(rr, "Image"):
        raise RuntimeError("The installed Rerun SDK does not expose `Image`.")
    recording_stream.log(entity_path, rr.Image(image_rgb))


def set_time_sequence(recording_stream: Any, *, timeline: str, sequence: int) -> None:
    """Set the current integer sequence time on the recording when supported."""
    del recording_stream
    rr = _import_rerun()
    setter = getattr(rr, "set_time_sequence", None)
    if setter is None:
        return
    setter(timeline, sequence)


def log_y_up_view_coordinates(recording_stream: Any, *, entity_path: str) -> None:
    """Declare a Y-up world coordinate frame when the installed Rerun SDK supports it."""
    rr = _import_rerun()
    view_coordinates = getattr(rr, "ViewCoordinates", None)
    if view_coordinates is None:
        return
    coordinate_value = (
        getattr(view_coordinates, "RIGHT_HAND_Y_UP", None)
        or getattr(view_coordinates, "RUB", None)
        or getattr(view_coordinates, "RUF", None)
    )
    if coordinate_value is None:
        return
    recording_stream.log(entity_path, coordinate_value)


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
    "attach_file_sink",
    "attach_grpc_sink",
    "attach_recording_sinks",
    "collect_native_visualization_artifacts",
    "create_recording_stream",
    "log_pointcloud",
    "log_points3d",
    "log_preview_image",
    "log_transform",
    "log_y_up_view_coordinates",
    "set_time_sequence",
]
