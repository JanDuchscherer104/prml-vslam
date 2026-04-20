"""Transport-safe backend event contracts.

This module contains the handoff between method-owned live updates and the
pipeline's event stream. It translates richer :class:`SlamUpdate` payloads into
transport-safe notices that can flow through runtime events and snapshots.
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
    """Expose transient visualization payload handles for one accepted keyframe."""

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
    """Report current map-size counters from a streaming backend."""

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
    """Record that a streaming backend session has closed."""

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
    """Translate one :class:`SlamUpdate` into explicit transport-safe backend events."""
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
