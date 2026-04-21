"""Transport-safe backend event contracts.

This module exists because the method layer and the pipeline layer care about
different kinds of runtime payloads. Method wrappers naturally emit rich
backend-facing :class:`SlamUpdate` objects that may include NumPy arrays,
backend-local semantics, and live visualization payloads. The pipeline,
however, needs a smaller transport-safe vocabulary that can be embedded inside
:class:`prml_vslam.pipeline.contracts.events.BackendNoticeReceived`, persisted
in runtime event streams, and projected into
:class:`prml_vslam.pipeline.contracts.runtime.RunSnapshot`.

In other words: :class:`SlamUpdate` is the wrapper-facing live update surface,
while :class:`BackendEvent` is the pipeline-facing live notice surface. This
module is the explicit translation boundary between those two worlds.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.transport import TransportModel


class PoseEstimated(TransportModel):
    """Report one canonical pose estimate emitted by a streaming backend."""

    kind: Literal["pose.estimated"] = "pose.estimated"
    seq: int
    timestamp_ns: int
    source_seq: int | None = None
    source_timestamp_ns: int | None = None
    pose: FrameTransform
    pose_updated: bool = True


class KeyframeAccepted(TransportModel):
    """Report that the backend accepted one frame as a keyframe."""

    kind: Literal["keyframe.accepted"] = "keyframe.accepted"
    seq: int
    timestamp_ns: int
    keyframe_index: int | None = None
    accepted_keyframes: int | None = None
    backend_fps: float | None = None


class KeyframeVisualizationReady(TransportModel):
    """Expose transient visualization payload handles for one accepted keyframe.

    The method layer may have arrays for previews, images, depth, or pointmaps
    in hand, but the pipeline should only see opaque handles plus the minimal
    metadata needed to log or project them safely.
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


class MapStatsUpdated(TransportModel):
    """Report current map-size counters from a streaming backend.

    This keeps lightweight progress telemetry in the event stream even when the
    durable output boundary remains the final :class:`SlamArtifacts` bundle.
    """

    kind: Literal["map.stats"] = "map.stats"
    seq: int
    timestamp_ns: int
    num_sparse_points: int = 0
    num_dense_points: int = 0


class BackendWarning(TransportModel):
    """Carry a non-fatal backend warning through the transport-safe event layer."""

    kind: Literal["backend.warning"] = "backend.warning"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


class BackendError(TransportModel):
    """Carry a fatal or actionable backend error through the event layer."""

    kind: Literal["backend.error"] = "backend.error"
    message: str
    seq: int | None = None
    timestamp_ns: int | None = None


class SessionClosed(TransportModel):
    """Record that a streaming backend session has closed.

    This is a live transport notice rather than the durable end-of-run result.
    The durable boundary is still the final :class:`SlamArtifacts` bundle that
    reaches the pipeline through stage completion.
    """

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


def translate_slam_update(
    *,
    update: SlamUpdate,
    accepted_keyframes: int | None = None,
    backend_fps: float | None = None,
    preview_handle: PreviewHandle | None = None,
    image_handle: ArrayHandle | None = None,
    depth_handle: ArrayHandle | None = None,
    pointmap_handle: ArrayHandle | None = None,
) -> list[BackendEvent]:
    """Translate one wrapper-facing :class:`SlamUpdate` into pipeline-facing notices.

    This function is the key boundary between :mod:`prml_vslam.methods` and
    :mod:`prml_vslam.pipeline` during streaming execution.

    Why the translation exists:
    - :class:`SlamUpdate` is convenient for backend wrappers because it can
      describe one incremental backend step in method-owned terms.
    - the pipeline event stream needs smaller, explicit, transport-safe records
      that can be embedded into runtime events, projected into snapshots, and
      forwarded without exposing backend-specific payload structure.

    The translator therefore explodes one coarse update into a sequence of
    domain-specific notices such as :class:`PoseEstimated`,
    :class:`KeyframeAccepted`, :class:`KeyframeVisualizationReady`, and
    :class:`MapStatsUpdated`. Callers should update this function whenever the
    meaning of :class:`SlamUpdate` changes so the pipeline transport vocabulary
    remains aligned with the method-layer telemetry surface.
    """
    events: list[BackendEvent] = []
    seq = int(update.seq)
    timestamp_ns = int(update.timestamp_ns)
    source_seq = update.source_seq
    source_timestamp_ns = update.source_timestamp_ns
    pose = update.pose
    for message in update.backend_warnings:
        events.append(
            BackendWarning(
                message=message,
                seq=seq,
                timestamp_ns=timestamp_ns,
            )
        )
    if pose is not None:
        events.append(
            PoseEstimated(
                seq=seq,
                timestamp_ns=timestamp_ns,
                source_seq=source_seq,
                source_timestamp_ns=source_timestamp_ns,
                pose=pose,
                pose_updated=update.pose_updated,
            )
        )
    if update.is_keyframe:
        events.append(
            KeyframeAccepted(
                seq=seq,
                timestamp_ns=timestamp_ns,
                keyframe_index=update.keyframe_index,
                accepted_keyframes=accepted_keyframes,
                backend_fps=backend_fps,
            )
        )
    if (
        update.is_keyframe
        and update.keyframe_index is not None
        and pose is not None
        and (
            preview_handle is not None
            or image_handle is not None
            or depth_handle is not None
            or pointmap_handle is not None
            or update.camera_intrinsics is not None
        )
    ):
        events.append(
            KeyframeVisualizationReady(
                seq=seq,
                timestamp_ns=timestamp_ns,
                source_seq=source_seq,
                source_timestamp_ns=source_timestamp_ns,
                keyframe_index=update.keyframe_index,
                pose=pose,
                preview=preview_handle,
                image=image_handle,
                depth=depth_handle,
                pointmap=pointmap_handle,
                camera_intrinsics=update.camera_intrinsics,
            )
        )
    events.append(
        MapStatsUpdated(
            seq=seq,
            timestamp_ns=timestamp_ns,
            num_sparse_points=int(update.num_sparse_points),
            num_dense_points=int(update.num_dense_points),
        )
    )
    return events


__all__ = [
    "BackendError",
    "BackendEvent",
    "BackendWarning",
    "KeyframeAccepted",
    "KeyframeVisualizationReady",
    "MapStatsUpdated",
    "PoseEstimated",
    "SessionClosed",
    "translate_slam_update",
]
