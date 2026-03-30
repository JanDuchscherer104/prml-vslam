"""Session manager — thin wrapper around Burr ApplicationBuilder.

Replaces the custom LinearRunner with Burr's built-in application lifecycle:
``step`` / ``run`` / ``iterate``, state persistence, and tracking.
"""

from __future__ import annotations

import json
import logging
import shutil
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

import cv2
import numpy as np
from burr.core import ApplicationBuilder, default, when

from prml_vslam.pipeline.contracts import MethodId
from prml_vslam.pipeline.messages import Envelope
from prml_vslam.pipeline.methods.mast3r import MockMast3rBackend
from prml_vslam.pipeline.methods.vista import MockVistaBackend
from prml_vslam.pipeline.runtime.actions import (
    decode_frame,
    export_artifacts,
    ingest_frame,
    slam_step,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from burr.core import Application

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Video source (cv2 iterator)
# ---------------------------------------------------------------------------


def _video_source(
    video_path: Path,
    *,
    artifact_root: Path,
    stride: int = 1,
    max_frames: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield frame dicts from a video file using OpenCV."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        msg = f"Cannot open video: {video_path}"
        raise FileNotFoundError(msg)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_idx = 0
    decoded = 0
    frames_dir = artifact_root / "input" / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue
            if max_frames is not None and decoded >= max_frames:
                break
            h, w = frame.shape[:2]
            frame_path = frames_dir / f"{decoded:06d}.png"
            if not cv2.imwrite(str(frame_path), frame):
                msg = f"Failed to persist decoded frame to {frame_path}"
                raise OSError(msg)
            yield {
                "frame_index": frame_idx,
                "width": w,
                "height": h,
                "ts_ns": int(frame_idx / fps * 1e9),
                "image_path": str(frame_path),
            }
            decoded += 1
            frame_idx += 1
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# SLAM backend factory
# ---------------------------------------------------------------------------


def _build_slam_backend(method: MethodId) -> Any:
    """Return a :class:`SlamBackend`-compatible object for *method*."""
    match method:
        case MethodId.VISTA_SLAM:
            return MockVistaBackend()
        case MethodId.MAST3R_SLAM:
            return MockMast3rBackend()
        case _:  # pragma: no cover
            msg = f"Unknown method: {method}"
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Session / SessionManager
# ---------------------------------------------------------------------------


class Session:
    """Thin handle wrapping a Burr :class:`Application`."""

    def __init__(
        self,
        *,
        session_id: str,
        mode: str,
        method: MethodId,
        artifact_root: Path,
        burr_app: Application,
        slam_backend: Any,
        video_path: Path | None = None,
    ) -> None:
        self.session_id = session_id
        self.mode = mode
        self.method = method
        self.artifact_root = artifact_root
        self.burr_app = burr_app
        self.slam_backend = slam_backend
        self.video_path = video_path
        self._outputs: list[Envelope] = []
        self.capture_manifest_path = artifact_root / "input" / "capture_manifest.json"
        self.frames_dir = artifact_root / "input" / "frames"
        self.created_at_ns = time.time_ns()
        self._capture_entries: list[dict[str, Any]] = []
        self._persisted_frame_count = 0

    @property
    def outputs(self) -> list[Envelope]:
        return self._outputs


class SessionManager:
    """Creates and manages pipeline sessions backed by Burr."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    @property
    def active_sessions(self) -> dict[str, Session]:
        return dict(self._sessions)

    def create_session(
        self,
        *,
        mode: str,
        method: MethodId,
        artifact_root: Path,
        session_id: str | None = None,
        video_path: Path | None = None,
        frame_stride: int = 1,
        max_frames: int | None = None,
    ) -> Session:
        """Build a Burr Application and return a Session handle."""
        sid = session_id or uuid.uuid4().hex[:12]
        slam = _build_slam_backend(method)

        if mode == "offline":
            if video_path is None:
                msg = "video_path is required for offline mode"
                raise ValueError(msg)
            burr_app = self._build_offline_app(
                session_id=sid,
                slam=slam,
                artifact_root=artifact_root,
                video_path=video_path,
                frame_stride=frame_stride,
                max_frames=max_frames,
            )
        else:
            burr_app = self._build_streaming_app(
                session_id=sid,
                slam=slam,
            )

        sess = Session(
            session_id=sid,
            mode=mode,
            method=method,
            artifact_root=artifact_root,
            burr_app=burr_app,
            slam_backend=slam,
            video_path=video_path,
        )
        if mode == "streaming":
            self._ensure_stream_capture_paths(sess)
            self._write_stream_capture_manifest(sess)
        self._sessions[sid] = sess
        logger.info("Created session %s (mode=%s, method=%s)", sid, mode, method.value)
        return sess

    # -- streaming API -----------------------------------------------------

    def push(self, session_id: str, msgs: list[Envelope]) -> list[Envelope]:
        """Push frames through a streaming session, return new outputs."""
        sess = self._sessions[session_id]
        out: list[Envelope] = []
        for m in msgs:
            payload = self._prepare_stream_payload(sess, m)
            # run through ingest → slam, halt after slam
            _action, _result, state = sess.burr_app.run(
                halt_after=["slam"],
                inputs={"frame_payload": payload},
            )
            step_outputs: list[Envelope] = state.get("step_outputs", [])
            out.extend(step_outputs)
        self._write_stream_capture_manifest(sess)
        sess._outputs.extend(out)
        return out

    # -- offline API -------------------------------------------------------

    def run_offline(self, session_id: str) -> list[Envelope]:
        """Execute the full offline pipeline until export."""
        all_outputs: list[Envelope] = []

        # iterate gives us step-by-step results
        for _action_name, step_outputs, _frame_index in self.iterate_offline(session_id):
            all_outputs.extend(step_outputs)
        return all_outputs

    def iterate_offline(self, session_id: str) -> Iterator[tuple[str, list[Envelope], int]]:
        """Yield offline execution steps for callers that want live progress updates."""
        sess = self._sessions[session_id]
        for action, _result, state in sess.burr_app.iterate(halt_after=["export"]):
            step_outputs: list[Envelope] = list(state.get("step_outputs", []))
            if step_outputs:
                sess._outputs.extend(step_outputs)
            yield getattr(action, "name", str(action)), step_outputs, int(state.get("frame_index", -1))

    # -- lifecycle ---------------------------------------------------------

    def close_session(self, session_id: str) -> list[Envelope]:
        """Finalise a session: export artifacts and clean up."""
        sess = self._sessions.pop(session_id)
        if sess.mode == "streaming":
            self._write_stream_capture_manifest(sess)
        sess.slam_backend.export_artifacts(sess.artifact_root)
        logger.info("Closed session %s", session_id)
        return []

    @staticmethod
    def _ensure_stream_capture_paths(sess: Session) -> None:
        sess.frames_dir.mkdir(parents=True, exist_ok=True)
        sess.capture_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    def _prepare_stream_payload(self, sess: Session, envelope: Envelope) -> dict[str, Any]:
        self._ensure_stream_capture_paths(sess)

        payload = dict(envelope.payload)
        frame_index_raw = payload.get("frame_index", envelope.seq)
        frame_index = int(frame_index_raw) if frame_index_raw is not None else envelope.seq

        persisted_path = self._persist_stream_frame(sess, payload)
        payload.pop("jpeg_bytes", None)
        if persisted_path is not None:
            payload["image_path"] = str(persisted_path)

        width_raw = payload.get("width", 0)
        height_raw = payload.get("height", 0)
        width = int(width_raw) if width_raw else 0
        height = int(height_raw) if height_raw else 0

        sess._capture_entries.append(
            {
                "seq": envelope.seq,
                "frame_index": frame_index,
                "ts_ns": envelope.ts_ns,
                "width": width,
                "height": height,
                "image_path": (
                    persisted_path.relative_to(sess.artifact_root).as_posix() if persisted_path is not None else None
                ),
            }
        )
        sess._persisted_frame_count += 1

        payload.setdefault("frame_index", frame_index)
        payload["ts_ns"] = envelope.ts_ns
        return payload

    def _persist_stream_frame(self, sess: Session, payload: dict[str, Any]) -> Path | None:
        frame_stem = f"{sess._persisted_frame_count:06d}"
        jpeg_bytes = payload.get("jpeg_bytes")
        if isinstance(jpeg_bytes, bytes | bytearray):
            target_path = sess.frames_dir / f"{frame_stem}.jpg"
            target_path.write_bytes(bytes(jpeg_bytes))
            return target_path

        image_path_raw = payload.get("image_path")
        if image_path_raw is not None:
            source_path = Path(image_path_raw)
            if source_path.exists():
                suffix = source_path.suffix or ".bin"
                target_path = sess.frames_dir / f"{frame_stem}{suffix}"
                if source_path.resolve() != target_path.resolve():
                    shutil.copy2(source_path, target_path)
                return target_path

        width_raw = payload.get("width", 0)
        height_raw = payload.get("height", 0)
        width = int(width_raw) if width_raw else 0
        height = int(height_raw) if height_raw else 0
        if width <= 0 or height <= 0:
            return None

        target_path = sess.frames_dir / f"{frame_stem}.png"
        placeholder = np.zeros((height, width, 3), dtype=np.uint8)
        if not cv2.imwrite(str(target_path), placeholder):
            msg = f"Failed to persist streaming frame to {target_path}"
            raise OSError(msg)
        return target_path

    @staticmethod
    def _write_stream_capture_manifest(sess: Session) -> None:
        manifest = {
            "session_id": sess.session_id,
            "mode": sess.mode,
            "method": sess.method.value,
            "source": "stream",
            "output_root": sess.artifact_root.as_posix(),
            "num_frames": len(sess._capture_entries),
            "created_at_ns": sess.created_at_ns,
            "updated_at_ns": time.time_ns(),
            "entries": sess._capture_entries,
        }
        sess.capture_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # -- Burr app builders -------------------------------------------------

    @staticmethod
    def _build_offline_app(
        *,
        session_id: str,
        slam: Any,
        artifact_root: Path,
        video_path: Path,
        frame_stride: int,
        max_frames: int | None,
    ) -> Application:
        source = _video_source(
            video_path,
            artifact_root=artifact_root,
            stride=frame_stride,
            max_frames=max_frames,
        )
        return (
            ApplicationBuilder()
            .with_actions(
                decode=decode_frame.bind(video_source=source),
                slam=slam_step.bind(slam_backend=slam),
                export=export_artifacts.bind(slam_backend=slam, artifact_root=str(artifact_root)),
            )
            .with_transitions(
                ("decode", "slam", when(frames_remaining=True)),
                ("decode", "export", default),
                ("slam", "decode"),
            )
            .with_state(
                session_id=session_id,
                current_frame={},
                frame_index=-1,
                ts_ns=0,
                frames_remaining=True,
                step_outputs=[],
                export_done=False,
            )
            .with_entrypoint("decode")
            .build()
        )

    @staticmethod
    def _build_streaming_app(*, session_id: str, slam: Any) -> Application:
        return (
            ApplicationBuilder()
            .with_actions(
                ingest=ingest_frame,
                slam=slam_step.bind(slam_backend=slam),
            )
            .with_transitions(
                ("ingest", "slam"),
                ("slam", "ingest"),
            )
            .with_state(
                session_id=session_id,
                current_frame={},
                frame_index=-1,
                ts_ns=0,
                step_outputs=[],
            )
            .with_entrypoint("ingest")
            .build()
        )
