"""Timestamped image-sequence replay source."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import Observation, ObservationIndexEntry

from .clock import ReplayClock, ReplayMode

DepthLoader = Callable[[Path], NDArray[np.float32]]


class ImageSequenceObservationSource:
    """Replay pre-indexed timestamped image frames as a live observation stream.

    This source acts as an adapter for disk-backed multimodal datasets. It iterates
    over an index of frames, waits for an emulated clock to reach each frame's
    timestamp, and yields :class:`~prml_vslam.interfaces.Observation` objects with
    aligned intrinsic and extrinsic metadata. Use this abstraction to test SLAM algorithms
    against stable file-based benchmarks as if they were live hardware.
    """

    def __init__(
        self,
        *,
        sequence_dir: Path,
        rows: list[ObservationIndexEntry],
        stride: int = 1,
        loop: bool = False,
        replay_mode: ReplayMode = ReplayMode.FAST_AS_POSSIBLE,
        include_depth: bool = True,
        depth_loader: DepthLoader | None = None,
    ) -> None:
        """Initialize the sequence playback state.

        Args:
            sequence_dir: The base directory containing sequence image payloads.
            rows: Ordered metadata entries defining the frame schedule.
            stride: The frame sampling step size. Must be >= 1.
            loop: Whether to wrap around seamlessly when the sequence ends.
            replay_mode: The time-sync strategy used to pace the replay clock.
            include_depth: Whether to eagerly decode depth payloads when available.
            depth_loader: A callable that decodes depth paths into ``(H, W)`` arrays
                in meters. Required if ``include_depth=True`` and any row defines a depth path.
        """
        if stride < 1:
            raise ValueError("stride must be >= 1.")
        self.sequence_dir = sequence_dir
        self.rows = rows
        self.stride = stride
        self.loop = loop
        self.include_depth = include_depth
        self.depth_loader = depth_loader
        self._clock = ReplayClock(replay_mode)
        self._frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0

    def connect(self) -> Path:
        """Validate the sequence directory and prepare the replay clock.

        This method resets the read cursor and initializes the emulated clock before
        the first frame is requested. Call this explicitly prior to pulling observations.

        Returns:
            The validated ``sequence_dir`` payload root.

        Raises:
            FileNotFoundError: If the directory is missing.
        """
        if not self.sequence_dir.is_dir():
            raise FileNotFoundError(f"Image sequence directory is missing: {self.sequence_dir}")
        self._frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0
        self._clock.reset()
        return self.sequence_dir

    def disconnect(self) -> None:
        """Release sequence resources and halt playback.

        For this source, this is a no-op as payloads are loaded lazily.
        """
        return None

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Load and return the next sampled observation aligned to the replay clock.

        This method blocks until the emulated clock reaches the scheduled dataset
        timestamp of the next requested frame. When ``stride > 1``, intermediate
        frames are skipped transparently.

        Args:
            timeout_seconds: An optional wait maximum. Unused and ignored
                by this implementation.

        Returns:
            The next valid, time-aligned observation.

        Raises:
            EOFError: When the sequence is exhausted and ``loop=False``.
        """
        del timeout_seconds
        while True:
            if self._frame_index >= len(self.rows):
                if not self.loop:
                    raise EOFError(f"Reached the end of {self.sequence_dir}")
                self._frame_index = 0
                self._loop_index += 1
                self._clock.reset()
                continue
            source_frame_index = self._frame_index
            self._frame_index += 1
            if source_frame_index % self.stride != 0:
                continue
            row = self.rows[source_frame_index]
            self._clock.wait_until(row.timestamp_ns)
            depth_m = self._load_depth(row.depth_path) if row.T_world_camera is not None else None
            if row.rgb_path is None:
                raise ValueError(f"Image sequence row seq={row.seq} is missing an RGB payload.")
            observation = Observation(
                seq=self._emitted_seq,
                timestamp_ns=row.timestamp_ns,
                source_frame_index=(
                    row.provenance.source_frame_index
                    if row.provenance.source_frame_index is not None
                    else source_frame_index
                ),
                loop_index=self._loop_index,
                arrival_timestamp_s=time.time(),
                rgb=_load_rgb_image(_resolve_payload(row.rgb_path, self.sequence_dir)),
                depth_m=depth_m,
                intrinsics=row.intrinsics,
                T_world_camera=row.T_world_camera,
                provenance=row.provenance,
            )
            self._emitted_seq += 1
            return observation

    def _load_depth(self, path: Path | None) -> NDArray[np.float32] | None:
        if not self.include_depth or path is None:
            return None
        if self.depth_loader is None:
            raise RuntimeError("A depth loader is required when include_depth=True and a row has a depth path.")
        return self.depth_loader(_resolve_payload(path, self.sequence_dir))


def _resolve_payload(path: Path, payload_root: Path) -> Path:
    return path if path.is_absolute() else payload_root / path


def _load_rgb_image(path: Path) -> NDArray[np.uint8]:
    frame_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame_bgr is None:
        raise FileNotFoundError(f"Cannot read RGB image: {path}")
    return np.asarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


__all__ = ["ImageSequenceObservationSource"]
