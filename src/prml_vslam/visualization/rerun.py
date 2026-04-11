"""Repo-owned Rerun helpers.

The helpers in this module intentionally use lazy imports so the repository can
keep Rerun optional until the viewer workflow is enabled in a concrete run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.pipeline.contracts.sequence import SequenceManifest


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
    return rr.RecordingStream(app_id=app_id, recording_id=recording_id)


def attach_file_sink(recording_stream: Any, *, target_path: Path) -> None:
    """Attach a file sink or save path to an existing recording stream."""
    rr = _import_rerun()
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
            rotation=rr.Quaternion(xyzw=quaternion),
            from_parent=True,
        ),
    )


def export_viewer_recording(
    *,
    sequence_manifest: SequenceManifest,
    slam_artifacts: SlamArtifacts,
    output_path: Path,
    run_id: str,
) -> ArtifactRef:
    """Export a normalized repo-owned `.rrd` recording from repo-owned artifacts."""
    del sequence_manifest, slam_artifacts
    recording_stream = create_recording_stream(app_id="prml-vslam", recording_id=run_id)
    attach_file_sink(recording_stream, target_path=output_path)
    return ArtifactRef(path=output_path.resolve(), kind="rrd", fingerprint=f"viewer-rrd-{run_id}")


__all__ = [
    "attach_file_sink",
    "attach_grpc_sink",
    "create_recording_stream",
    "export_viewer_recording",
    "log_transform",
]
