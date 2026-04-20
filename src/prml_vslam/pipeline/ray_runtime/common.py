"""Shared Ray runtime contracts and helpers."""

from __future__ import annotations

import time
import uuid
from collections import deque
from pathlib import Path
from typing import TypeAlias

import numpy as np
import ray

from prml_vslam.interfaces.slam import ArtifactRef, SlamArtifacts
from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.methods.contracts import SlamBackendConfig
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.finalization import stable_hash
from prml_vslam.pipeline.placement import RayActorOptions

EVENT_RING_LIMIT = 400
HANDLE_LIMIT = 256
FPS_WINDOW = 20
DEFAULT_MAX_FRAMES_IN_FLIGHT = 2
HandlePayload: TypeAlias = ray.ObjectRef[np.ndarray] | np.ndarray


def coordinator_actor_name(run_id: str) -> str:
    """Return the stable Ray actor name for one pipeline run."""
    return f"prml-vslam-run-{run_id}"


def put_array_handle(array: np.ndarray | None) -> tuple[ArrayHandle | None, ray.ObjectRef[np.ndarray] | None]:
    """Store one array payload in Ray and return the public handle."""
    if array is None:
        return None, None
    payload = np.asarray(array)
    handle = ArrayHandle(
        handle_id=uuid.uuid4().hex,
        shape=tuple(int(dim) for dim in payload.shape),
        dtype=str(payload.dtype),
    )
    return handle, ray.put(payload)


def put_preview_handle(array: np.ndarray | None) -> tuple[PreviewHandle | None, ray.ObjectRef[np.ndarray] | None]:
    """Store one preview image payload in Ray and return the public handle."""
    if array is None:
        return None, None
    payload = np.asarray(array)
    height, width = int(payload.shape[0]), int(payload.shape[1])
    channels = 1 if payload.ndim == 2 else int(payload.shape[2])
    handle = PreviewHandle(
        handle_id=uuid.uuid4().hex,
        width=width,
        height=height,
        channels=channels,
        dtype=str(payload.dtype),
    )
    return handle, ray.put(payload)


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


def backend_config_payload(request: RunRequest) -> SlamBackendConfig:
    """Build the executable backend-config model expected by current backends."""
    if request.slam.backend.kind == "vista":
        from prml_vslam.methods import VistaSlamBackendConfig

        payload = request.slam.backend.model_dump(mode="python")
        payload.pop("kind")
        return VistaSlamBackendConfig.model_validate(payload)
    from prml_vslam.methods.contracts import SlamBackendConfig

    return SlamBackendConfig(max_frames=request.slam.backend.max_frames)


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
    "backend_config_payload",
    "clean_actor_options",
    "coordinator_actor_name",
    "put_array_handle",
    "put_preview_handle",
    "rolling_fps",
    "slam_artifacts_map",
    "ts_ns",
    "visualization_artifact_map",
]
