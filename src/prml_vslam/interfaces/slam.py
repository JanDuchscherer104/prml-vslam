"""Canonical SLAM-stage DTOs shared across methods and pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.utils import BaseData


class ArtifactRef(BaseData):
    """Reference to one materialized artifact owned by the repository."""

    path: Path
    kind: str
    fingerprint: str


class SlamArtifacts(BaseData):
    """Materialized outputs produced by the SLAM stage."""

    trajectory_tum: ArtifactRef
    sparse_points_ply: ArtifactRef | None = None
    dense_points_ply: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-06): Replace with a private SlamStageRuntime start
# input or method-owned init DTO once streaming SLAM is behind the stage runtime.
class SlamSessionInit(BaseData):
    """Normalized context injected once when a streaming session starts."""

    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None
    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH


# TODO(pipeline-refactor/WP-06): Move live SLAM update semantics to
# methods.contracts and keep transient refs out of pure domain DTOs.
class SlamUpdate(BaseData):
    """Incremental SLAM update emitted by streaming-capable backends."""

    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    is_keyframe: bool = False
    keyframe_index: int | None = None
    pose: FrameTransform | None = None
    num_sparse_points: int = 0
    num_dense_points: int = 0
    pointmap: NDArray[np.float32] | None = None
    camera_intrinsics: CameraIntrinsics | None = None
    image_rgb: NDArray[np.uint8] | None = None
    depth_map: NDArray[np.float32] | None = None
    preview_rgb: NDArray[np.uint8] | None = None
    pose_updated: bool = False
    backend_warnings: list[str] = Field(default_factory=list)


# TODO(pipeline-refactor/WP-06): Move backend notice variants to method-owned
# semantic events carried by StageRuntimeUpdate.
class PoseEstimated(TransportModel):
    """Pose estimate emitted by a streaming backend."""

    kind: Literal["pose.estimated"] = "pose.estimated"
    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    pose: FrameTransform
    pose_updated: bool = True


# TODO(pipeline-refactor/WP-06): Move backend notice variants to method-owned
# semantic events carried by StageRuntimeUpdate.
class KeyframeAccepted(TransportModel):
    """Keyframe-acceptance notice emitted by a streaming backend."""

    kind: Literal["keyframe.accepted"] = "keyframe.accepted"
    seq: int
    timestamp_ns: int
    keyframe_index: int | None = None
    accepted_keyframes: int | None = None
    backend_fps: float | None = None


# TODO(pipeline-refactor/WP-07): Replace handle-bearing backend event with
# VisualizationItem values created by SlamVisualizationAdapter.
class KeyframeVisualizationReady(TransportModel):
    """Visualization payload handles emitted for one accepted keyframe."""

    kind: Literal["keyframe.visualization_ready"] = "keyframe.visualization_ready"
    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    keyframe_index: int
    pose: FrameTransform
    preview: PreviewHandle | None = None
    image: ArrayHandle | None = None
    depth: ArrayHandle | None = None
    pointmap: ArrayHandle | None = None
    camera_intrinsics: CameraIntrinsics | None = None


# TODO(pipeline-refactor/WP-06): Move backend notice variants to method-owned
# semantic events carried by StageRuntimeUpdate.
class MapStatsUpdated(TransportModel):
    """Map-size telemetry emitted by a streaming backend."""

    kind: Literal["map.stats"] = "map.stats"
    seq: int
    timestamp_ns: int
    num_sparse_points: int = 0
    num_dense_points: int = 0


# TODO(pipeline-refactor/WP-06): Move backend warning notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class BackendWarning(TransportModel):
    """Non-fatal backend warning."""

    kind: Literal["backend.warning"] = "backend.warning"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


# TODO(pipeline-refactor/WP-06): Move backend error notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class BackendError(TransportModel):
    """Fatal or actionable backend error."""

    kind: Literal["backend.error"] = "backend.error"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


# TODO(pipeline-refactor/WP-06): Move session terminal notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class SessionClosed(TransportModel):
    """Terminal backend-session notice."""

    kind: Literal["session.closed"] = "session.closed"
    artifact_keys: list[str] = Field(default_factory=list)


BackendEvent = Annotated[
    PoseEstimated
    | KeyframeAccepted
    | KeyframeVisualizationReady
    | MapStatsUpdated
    | BackendWarning
    | BackendError
    | SessionClosed,
    Field(discriminator="kind"),
]


__all__ = [
    "ArtifactRef",
    "BackendError",
    "BackendEvent",
    "BackendWarning",
    "KeyframeAccepted",
    "KeyframeVisualizationReady",
    "MapStatsUpdated",
    "PoseEstimated",
    "SessionClosed",
    "SlamArtifacts",
    "SlamSessionInit",
    "SlamUpdate",
]
