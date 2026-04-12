"""Import native ViSTA-SLAM outputs into repo-owned artifact contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline.contracts.artifacts import ArtifactRef, SlamArtifacts
from prml_vslam.utils import RunArtifactPaths


def import_vista_artifacts(*, native_output_dir: Path, run_paths: RunArtifactPaths) -> SlamArtifacts:
    """Normalize native ViSTA outputs into repo-owned artifact contracts."""
    del run_paths
    trajectory_path = _require_existing_path(
        native_output_dir / "trajectory.tum",
        error_message="ViSTA-SLAM did not produce the expected `trajectory.tum` output.",
    )
    sparse_points_path = _optional_existing_path(native_output_dir / "sparse_points.ply")
    dense_points_path = _optional_existing_path(native_output_dir / "dense_points.ply")
    extras = {
        path.name: _artifact_ref(path, kind=path.suffix.lstrip(".") or "file", fingerprint=f"{path.name}-artifact")
        for path in sorted(native_output_dir.glob("*"))
        if path.is_file()
        and path.name not in {"trajectory.tum", "sparse_points.ply", "dense_points.ply", "rerun_recording.rrd"}
    }
    return SlamArtifacts(
        trajectory_tum=_artifact_ref(trajectory_path, kind="tum", fingerprint="vista-trajectory"),
        sparse_points_ply=(
            None
            if sparse_points_path is None
            else _artifact_ref(sparse_points_path, kind="ply", fingerprint="vista-sparse")
        ),
        dense_points_ply=(
            None
            if dense_points_path is None
            else _artifact_ref(dense_points_path, kind="ply", fingerprint="vista-dense")
        ),
        extras=extras,
    )


def _require_existing_path(path: Path, *, error_message: str) -> Path:
    if not path.exists():
        raise RuntimeError(error_message)
    return path.resolve()


def _optional_existing_path(path: Path) -> Path | None:
    return path.resolve() if path.exists() else None


def _artifact_ref(path: Path, *, kind: str, fingerprint: str) -> ArtifactRef:
    return ArtifactRef(path=path.resolve(), kind=kind, fingerprint=fingerprint)


__all__ = ["import_vista_artifacts"]
