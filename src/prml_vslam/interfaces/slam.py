"""SLAM artifact and live-update DTOs used at method/pipeline boundaries.

This module is the current compatibility home for normalized SLAM artifacts
and streaming notices. Durable outputs such as :class:`SlamArtifacts` are
shared repository semantics, while live DTOs such as :class:`SlamUpdate` and
the :data:`BackendEvent` union are migration contacts for the target
architecture described in
``docs/architecture/pipeline-stage-refactor-target.md``. New code should read
these docstrings together with :mod:`prml_vslam.methods.protocols`,
:mod:`prml_vslam.pipeline.stages.slam.runtime`, and
:mod:`prml_vslam.pipeline.stages.base.contracts` so it can distinguish
scientific artifacts from live observer telemetry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from prml_vslam.interfaces.camera import CameraIntrinsics
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.transport import TransportModel
from prml_vslam.utils import BaseData


# TODO(pipeline-refactor/WP-08/WP-10): Move this generic artifact reference out
# of SLAM-owned interfaces after artifact/provenance imports migrate.
class ArtifactRef(BaseData):
    """Reference one materialized repository artifact by path and fingerprint.

    This DTO is intentionally small: it identifies a durable output that lives
    under a run artifact root and can be named from manifests, events, and
    summaries. It is currently located in ``interfaces.slam`` for compatibility,
    but it is not SLAM-specific; the target refactor moves generic artifact
    references toward pipeline provenance or a shared artifact contract.
    """

    path: Path
    kind: str
    fingerprint: str


class SlamArtifacts(BaseData):
    """Normalize durable outputs produced by a SLAM backend.

    The bundle is the scientific handoff from method execution into evaluation,
    alignment, reconstruction, artifact inspection, and reporting. Paths should
    point at repo-normalized artifacts such as TUM trajectories and PLY point
    clouds; backend-native diagnostics belong in :attr:`extras` unless another
    package owns a typed artifact with explicit raster, frame, or metric
    semantics.
    """

    trajectory_tum: ArtifactRef
    sparse_points_ply: ArtifactRef | None = None
    dense_points_ply: ArtifactRef | None = None
    extras: dict[str, ArtifactRef] = Field(default_factory=dict)


# TODO(pipeline-refactor/WP-06): Move live SLAM update semantics to
# methods.contracts and keep transient refs out of pure domain DTOs.
class SlamUpdate(BaseData):
    """Represent one method-owned incremental SLAM update.

    Backends emit this rich in-memory object because it can carry arrays,
    camera intrinsics, keyframe markers, map counters, and the canonical
    ``T_world_camera`` pose together. It is not a durable event and should not
    embed pipeline payload handles. The current pipeline translates it through
    :func:`prml_vslam.methods.events.translate_slam_update`; the target runtime
    turns it into ``StageRuntimeUpdate`` semantic events plus neutral
    visualization items.
    """

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
    """Transport-safe pose notice derived from a live SLAM update.

    The pose follows the repo convention ``world <- camera`` through
    :class:`prml_vslam.interfaces.transforms.FrameTransform`. This notice is a
    current durable-event migration contact; target live status and observers
    should receive method semantic events through ``StageRuntimeUpdate``.
    """

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
    """Transport-safe notice that a backend accepted a keyframe.

    The notice carries counters and timing hints only. Keyframe rasters,
    depth, and pointmaps travel through separate visualization payload
    references so that transient arrays do not become durable event payloads.
    """

    kind: Literal["keyframe.accepted"] = "keyframe.accepted"
    seq: int
    timestamp_ns: int
    keyframe_index: int | None = None
    accepted_keyframes: int | None = None
    backend_fps: float | None = None


# TODO(pipeline-refactor/WP-07): Replace handle-bearing backend event with
# VisualizationItem values created by SlamVisualizationAdapter.
class KeyframeVisualizationReady(TransportModel):
    """Legacy handle-bearing visualization notice for one accepted keyframe.

    The handles point at transient runtime payloads, not durable artifacts.
    This is a compatibility bridge for the existing Rerun sink and snapshot
    projector. Target code should prefer
    :class:`prml_vslam.pipeline.stages.base.contracts.VisualizationItem` values
    created by :class:`prml_vslam.pipeline.stages.slam.visualization.SlamVisualizationAdapter`.
    """

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
    """Transport-safe map-size telemetry emitted by a streaming backend."""

    kind: Literal["map.stats"] = "map.stats"
    seq: int
    timestamp_ns: int
    num_sparse_points: int = 0
    num_dense_points: int = 0


# TODO(pipeline-refactor/WP-06): Move backend warning notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class BackendWarning(TransportModel):
    """Non-fatal backend warning surfaced without failing the active run."""

    kind: Literal["backend.warning"] = "backend.warning"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


# TODO(pipeline-refactor/WP-06): Move backend error notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class BackendError(TransportModel):
    """Fatal or actionable backend error surfaced from method execution."""

    kind: Literal["backend.error"] = "backend.error"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


# TODO(pipeline-refactor/WP-06): Move session terminal notices to method-owned
# semantic events carried by StageRuntimeUpdate.
class SessionClosed(TransportModel):
    """Terminal backend-session notice listing newly available artifact keys."""

    kind: Literal["session.closed"] = "session.closed"
    artifact_keys: list[str] = Field(default_factory=list)


# TODO(pipeline-refactor/WP-08/WP-10): Retire this legacy durable backend-event
# union after live SLAM semantics route through StageRuntimeUpdate.
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
    "SlamUpdate",
]
