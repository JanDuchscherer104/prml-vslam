"""Translate method-owned live updates into pipeline-facing backend notices.

This module exists because the method layer and the pipeline layer care about
different runtime payloads. Method wrappers naturally emit rich
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

from prml_vslam.interfaces.slam import (
    BackendEvent,
    BackendWarning,
    KeyframeAccepted,
    KeyframeVisualizationReady,
    MapStatsUpdated,
    PoseEstimated,
    SlamUpdate,
)
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle


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


__all__ = ["translate_slam_update"]
