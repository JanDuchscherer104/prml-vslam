"""Shared Ray runtime contracts and helpers."""

from __future__ import annotations

import time
import uuid
from collections import deque
from pathlib import Path
from typing import TypeAlias

import numpy as np
import ray

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.pipeline.contracts.provenance import ArtifactRef
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.placement import RayActorOptions
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef

EVENT_RING_LIMIT = 400
HANDLE_LIMIT = 256
FPS_WINDOW = 20
DEFAULT_MAX_FRAMES_IN_FLIGHT = 2
HandlePayload: TypeAlias = ray.ObjectRef[np.ndarray] | np.ndarray


def coordinator_actor_name(run_id: str) -> str:
    """Return the stable Ray actor name for one pipeline run."""
    return f"prml-vslam-run-{run_id}"


def put_transient_payload(
    array: np.ndarray | None,
    *,
    payload_kind: str,
    media_type: str,
    metadata: dict[str, str | int | float | bool | None] | None = None,
) -> tuple[TransientPayloadRef | None, ray.ObjectRef[np.ndarray] | None]:
    """Store one transient array payload in Ray and return backend-neutral metadata."""
    if array is None:
        return None, None
    payload = np.asarray(array)
    ref = TransientPayloadRef(
        handle_id=uuid.uuid4().hex,
        payload_kind=payload_kind,
        media_type=media_type,
        shape=tuple(int(dim) for dim in payload.shape),
        dtype=str(payload.dtype),
        size_bytes=int(payload.nbytes),
        metadata={} if metadata is None else metadata,
    )
    return ref, ray.put(payload)


def rolling_fps(timestamps: deque[float]) -> float:
    """Compute a rolling frames-per-second estimate."""
    if len(timestamps) < 2:
        return 0.0
    elapsed = timestamps[-1] - timestamps[0]
    return 0.0 if elapsed <= 0.0 else (len(timestamps) - 1) / elapsed


def artifact_ref(path: Path, *, kind: str) -> ArtifactRef:
    """Build one stable artifact reference for a materialized path."""
    resolved_path = path.resolve()
    return ArtifactRef(
        path=resolved_path,
        kind=kind,
        fingerprint=stable_hash({"path": str(resolved_path), "kind": kind}),
    )


def slam_artifacts_map(slam: SlamArtifacts) -> dict[str, ArtifactRef]:
    """Flatten the typed SLAM artifact bundle into the stage artifact map."""
    artifacts = {"trajectory_tum": slam.trajectory_tum}
    if slam.sparse_points_ply is not None:
        artifacts["sparse_points_ply"] = slam.sparse_points_ply
    if slam.dense_points_ply is not None:
        artifacts["dense_points_ply"] = slam.dense_points_ply
    for key, artifact in slam.extras.items():
        artifacts[f"extra:{key}"] = artifact
    return artifacts


def visualization_artifact_map(visualization: VisualizationArtifacts | None) -> dict[str, ArtifactRef]:
    """Flatten visualization-owned output artifacts into the stage artifact map."""
    if visualization is None:
        return {}
    artifacts: dict[str, ArtifactRef] = {}
    if visualization.native_rerun_rrd is not None:
        artifacts["native_rerun_rrd"] = visualization.native_rerun_rrd
    if visualization.native_output_dir is not None:
        artifacts["native_output_dir"] = visualization.native_output_dir
    for key, artifact in visualization.extras.items():
        artifacts[f"visualization:{key}"] = artifact
    return artifacts


def clean_actor_options(options: RayActorOptions) -> RayActorOptions:
    """Remove empty Ray actor options before `.options(...)`."""
    return {key: value for key, value in options.items() if value is not None and value != {}}


def ts_ns() -> int:
    """Return the current wall-clock timestamp in nanoseconds."""
    return time.time_ns()


__all__ = [
    "DEFAULT_MAX_FRAMES_IN_FLIGHT",
    "EVENT_RING_LIMIT",
    "FPS_WINDOW",
    "HANDLE_LIMIT",
    "HandlePayload",
    "artifact_ref",
    "clean_actor_options",
    "coordinator_actor_name",
    "put_transient_payload",
    "rolling_fps",
    "slam_artifacts_map",
    "ts_ns",
    "visualization_artifact_map",
]
