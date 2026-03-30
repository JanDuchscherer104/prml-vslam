"""Burr actions that implement the VSLAM pipeline steps.

Each ``@action`` is a pure function that reads from / writes to Burr
:class:`~burr.core.state.State`.  Heavy-lifting is delegated to bound
objects (*video_source*, *slam_backend*) so the actions stay thin.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from burr.core import State, action

from prml_vslam.pipeline.messages import (
    FramePayload,
    MapUpdatePayload,
    MessageKind,
    PosePayload,
    PreviewPayload,
    make_envelope,
    pose_from_matrix,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


# ---------------------------------------------------------------------------
# Offline: decode frames from a video source iterator
# ---------------------------------------------------------------------------


@action(reads=[], writes=["current_frame", "frame_index", "ts_ns", "frames_remaining"])
def decode_frame(state: State, video_source: Iterator[dict[str, Any]]) -> tuple[dict, State]:
    """Pull the next frame from *video_source* (bound at build time).

    When the iterator is exhausted, ``frames_remaining`` flips to ``False``
    and the transition to the *export* action fires.
    """
    try:
        frame = FramePayload.model_validate(next(video_source)).model_dump(mode="python")
        return frame, state.update(
            current_frame=frame,
            frame_index=frame.get("frame_index", 0),
            ts_ns=frame.get("ts_ns", 0),
            frames_remaining=True,
        )
    except StopIteration:
        return {}, state.update(frames_remaining=False)


# ---------------------------------------------------------------------------
# Streaming: accept an externally-pushed frame payload
# ---------------------------------------------------------------------------


@action(reads=[], writes=["current_frame", "frame_index", "ts_ns"])
def ingest_frame(state: State, frame_payload: dict[str, Any]) -> tuple[dict, State]:
    """Accept a single frame pushed by the caller via ``app.run(inputs=…)``.

    *frame_payload* is passed as a runtime input on every ``step`` / ``run``
    call, keeping the streaming path symmetric with the offline decode action.
    """
    frame = FramePayload.model_validate(frame_payload).model_dump(mode="python")
    return frame, state.update(
        current_frame=frame,
        frame_index=frame.get("frame_index", 0),
        ts_ns=frame.get("ts_ns", 0),
    )


# ---------------------------------------------------------------------------
# SLAM processing step (shared between offline and streaming)
# ---------------------------------------------------------------------------


@action(reads=["frame_index", "ts_ns"], writes=["step_outputs"])
def slam_step(state: State, slam_backend: Any) -> tuple[dict, State]:
    """Run one SLAM step and materialise typed :class:`Envelope` outputs.

    The *slam_backend* (bound at build time) satisfies the
    :class:`SlamBackend` protocol, keeping this action agnostic of the
    concrete method.
    """
    frame_index: int = state["frame_index"]
    ts_ns: int = state.get("ts_ns", 0)
    session_id: str = state.get("session_id", "unknown")

    result = slam_backend.step(frame_index, ts_ns=ts_ns)

    envelopes = []
    if result.pose is not None:
        envelopes.append(
            make_envelope(
                session_id=session_id,
                seq=frame_index,
                kind=MessageKind.POSE_UPDATE,
                payload=PosePayload.from_matrix(
                    result.pose,
                    timestamp_s=result.timestamp_s,
                    is_keyframe=result.is_keyframe,
                ).model_dump(mode="json"),
                ts_ns=ts_ns,
            )
        )

    if result.map_points is not None:
        envelopes.append(
            make_envelope(
                session_id=session_id,
                seq=frame_index,
                kind=MessageKind.MAP_UPDATE,
                payload=MapUpdatePayload(
                    num_points=result.num_map_points,
                ).model_dump(mode="json"),
                ts_ns=ts_ns,
            )
        )

    if result.preview_trajectory is not None:
        latest = pose_from_matrix(result.pose) if result.pose is not None else None
        envelopes.append(
            make_envelope(
                session_id=session_id,
                seq=frame_index,
                kind=MessageKind.PREVIEW,
                payload=PreviewPayload(
                    trajectory_so_far=result.preview_trajectory,
                    num_map_points=result.num_map_points,
                    latest_pose=latest,
                ).model_dump(mode="json"),
                ts_ns=ts_ns,
            )
        )

    return {"envelopes": envelopes}, state.update(step_outputs=envelopes)


# ---------------------------------------------------------------------------
# Export final artifacts to disk
# ---------------------------------------------------------------------------


@action(reads=[], writes=["export_done"])
def export_artifacts(state: State, slam_backend: Any, artifact_root: str) -> tuple[dict, State]:
    """Write trajectory + point-cloud artifacts via the bound backend."""
    from pathlib import Path

    slam_backend.export_artifacts(Path(artifact_root))
    return {"artifact_root": artifact_root}, state.update(export_done=True)
