"""OpenCV-backed frame replay source for local video samples.

This module owns the generic video replay path used by dataset adapters and
simple video-backed sources. It emits normalized runtime packets but does not
decide dataset semantics, pipeline stages, or backend behavior.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

import cv2
import numpy as np
from pydantic import Field

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FramePacketProvenance, FrameTransform
from prml_vslam.utils import BaseConfig, BaseData


class Cv2ReplayMode(StrEnum):
    """Select whether replay follows source timing or returns frames immediately."""

    FAST_AS_POSSIBLE = "fast_as_possible"
    REALTIME = "realtime"


class Cv2FramePayload(BaseData):
    """Carry optional non-RGB payloads injected through the shared replay path."""

    depth: np.ndarray | None = None
    confidence: np.ndarray | None = None
    pointmap: np.ndarray | None = None


class Cv2ProducerConfig(BaseConfig):
    """Configure one replayable local video sample and its optional side payloads."""

    video_path: Path
    """Path to the source video file."""

    frame_timestamps_ns: list[int] | None = None
    """Optional exact frame timestamps aligned to source frame indices."""

    stride: int = Field(default=1, ge=1)
    """Frame subsampling stride."""

    loop: bool = False
    """Whether playback should restart from the beginning after the last frame."""

    replay_mode: Cv2ReplayMode = Cv2ReplayMode.FAST_AS_POSSIBLE
    """Whether playback should follow dataset timing or return frames immediately."""

    intrinsics: CameraIntrinsics | None = None
    """Camera intrinsics associated with the replayed sample when known."""

    poses_by_frame: list[FrameTransform | None] | None = None
    """Optional per-frame camera poses aligned to source frame indices."""

    payload_provider: Callable[[int, int], Cv2FramePayload | None] | None = None
    """Optional provider for depth/confidence/pointmap payloads aligned by frame index and timestamp."""

    fps: float = 60.0
    """Target frames per second."""

    base_provenance: FramePacketProvenance = Field(default_factory=FramePacketProvenance)
    """Typed provenance copied into each emitted packet before frame-local fields are filled."""


class Cv2FrameProducer:
    """Replay one local video through the shared blocking packet-stream seam."""

    def __init__(self, config: Cv2ProducerConfig) -> None:
        self.config = config
        self._capture: cv2.VideoCapture | None = None
        self._frame_index = 0
        self._loop_index = 0
        self._stream_start_monotonic: float | None = None
        self._stream_start_timestamp_ns: int | None = None
        self._fps = self.config.fps

    def connect(self) -> Path:
        """Open the configured video file and prepare playback state."""
        self.disconnect()
        capture = cv2.VideoCapture(str(self.config.video_path))
        if not capture.isOpened():
            msg = f"Cannot open video: {self.config.video_path}"
            raise FileNotFoundError(msg)
        self._capture = capture
        self._frame_index = 0
        self._loop_index = 0
        self._stream_start_monotonic = None
        self._stream_start_timestamp_ns = None
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        if fps > 0.0:
            self._fps = fps
        return self.config.video_path

    def disconnect(self) -> None:
        """Release the underlying OpenCV capture if one is open."""
        if self._capture is not None:
            self._capture.release()
        self._capture = None

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        """Decode and return the next sampled RGB frame."""
        del timeout_seconds
        capture = self._require_capture()

        while True:
            ok, frame_bgr = capture.read()
            if not ok:
                if not self.config.loop:
                    raise EOFError(f"Reached the end of {self.config.video_path}")
                self._restart_capture(capture)
                continue

            source_frame_index = self._frame_index
            self._frame_index += 1
            if source_frame_index % self.config.stride != 0:
                continue

            timestamp_ns = self._timestamp_ns_for_frame(source_frame_index)
            self._apply_replay_timing(timestamp_ns)
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            payload = self._payload_for_frame(source_frame_index, timestamp_ns)
            return FramePacket(
                seq=source_frame_index,
                timestamp_ns=timestamp_ns,
                arrival_timestamp_s=time.time(),
                rgb=np.asarray(frame_rgb, dtype=np.uint8),
                depth=None if payload is None or payload.depth is None else np.asarray(payload.depth, dtype=np.float32),
                confidence=None
                if payload is None or payload.confidence is None
                else np.asarray(payload.confidence, dtype=np.float32),
                pointmap=None
                if payload is None or payload.pointmap is None
                else np.asarray(payload.pointmap, dtype=np.float32),
                intrinsics=self.config.intrinsics,
                pose=self._pose_for_frame(source_frame_index),
                provenance=self.config.base_provenance.model_copy(
                    update={
                        "loop_index": self._loop_index,
                        "source_frame_index": source_frame_index,
                    }
                ),
            )

    def _require_capture(self) -> cv2.VideoCapture:
        if self._capture is None:
            msg = "Cv2FrameProducer.connect() must be called before requesting frames."
            raise RuntimeError(msg)
        return self._capture

    def _restart_capture(self, capture: cv2.VideoCapture) -> None:
        if not capture.set(cv2.CAP_PROP_POS_FRAMES, 0):
            self.disconnect()
            self.connect()
        self._frame_index = 0
        self._loop_index += 1
        self._stream_start_monotonic = None
        self._stream_start_timestamp_ns = None

    def _timestamp_ns_for_frame(self, frame_index: int) -> int:
        timestamps_ns = self.config.frame_timestamps_ns
        if timestamps_ns is not None and frame_index < len(timestamps_ns):
            return int(timestamps_ns[frame_index])
        return int(frame_index / self._fps * 1e9)

    def _apply_replay_timing(self, timestamp_ns: int) -> None:
        if self.config.replay_mode is not Cv2ReplayMode.REALTIME:
            return
        if self._stream_start_timestamp_ns is None:
            self._stream_start_timestamp_ns = timestamp_ns
            self._stream_start_monotonic = time.monotonic()
            return
        if self._stream_start_monotonic is None:
            return
        target_elapsed_s = max(timestamp_ns - self._stream_start_timestamp_ns, 0) / 1e9
        actual_elapsed_s = time.monotonic() - self._stream_start_monotonic
        sleep_seconds = target_elapsed_s - actual_elapsed_s
        if sleep_seconds > 0.0:
            time.sleep(sleep_seconds)

    def _pose_for_frame(self, frame_index: int) -> FrameTransform | None:
        poses_by_frame = self.config.poses_by_frame
        if poses_by_frame is None or frame_index >= len(poses_by_frame):
            return None
        return poses_by_frame[frame_index]

    def _payload_for_frame(self, frame_index: int, timestamp_ns: int) -> Cv2FramePayload | None:
        payload_provider = self.config.payload_provider
        return None if payload_provider is None else payload_provider(frame_index, timestamp_ns)


__all__ = [
    "Cv2FrameProducer",
    "Cv2FramePayload",
    "Cv2ProducerConfig",
    "Cv2ReplayMode",
]
