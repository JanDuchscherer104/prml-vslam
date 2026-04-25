"""PyAV-backed video replay source."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import av
import numpy as np

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform, Observation, ObservationProvenance

from .clock import ReplayClock, ReplayMode


class PyAvVideoObservationSource:
    """Stream a local video iteratively as if it were a live camera source.

    This source acts as an adapter for disk-backed video media using ``pyav``.
    It waits for an emulated clock to pace the video's presentation timestamps
    (or dataset-provided frame timestamps), unpacks geometry transformations,
    and handles automatic orientation normalization for upright rendering. Use
    this abstraction to evaluate algorithms against pre-recorded continuous video
    in the same pipeline designed for live hardware.
    """

    def __init__(
        self,
        *,
        video_path: Path,
        frame_timestamps_ns: list[int] | None = None,
        stride: int = 1,
        loop: bool = False,
        replay_mode: ReplayMode = ReplayMode.FAST_AS_POSSIBLE,
        intrinsics: CameraIntrinsics | None = None,
        poses_by_frame: list[FrameTransform | None] | None = None,
        allow_synthetic_timestamps: bool = False,
        synthetic_fps: float | None = None,
        base_provenance: ObservationProvenance | None = None,
        normalize_video_orientation: bool = True,
    ) -> None:
        """Initialize the video playback state.

        Args:
            video_path: The file path to the continuous media payload.
            frame_timestamps_ns: An optional sequence of explicit nanosecond
                timestamps. If provided, overrides PyAV presentation times.
            stride: The frame sampling step size. Must be >= 1.
            loop: Whether to wrap around seamlessly when the video ends.
            replay_mode: The time-sync pacing strategy applied when a frame is read.
            intrinsics: Emulated camera geometry to attach to observations.
            poses_by_frame: Indexed frame-to-world metrics, such as ground truth
                trajectories from benchmarks.
            allow_synthetic_timestamps: Whether to generate timestamps synthetically
                if the video lacks them.
            synthetic_fps: The framerate to assume when calculating synthetic
                timestamps. Required if ``allow_synthetic_timestamps=True``.
            base_provenance: A shared metadata footprint applied to all emitted
                observations to record the video origin.
            normalize_video_orientation: Whether to rotate out metadata-encoded
                display orientations before emitting the frame.
        """
        if stride < 1:
            raise ValueError("stride must be >= 1.")
        self.video_path = video_path
        self.frame_timestamps_ns = frame_timestamps_ns
        self.stride = stride
        self.loop = loop
        self.intrinsics = intrinsics
        self.poses_by_frame = poses_by_frame
        self.allow_synthetic_timestamps = allow_synthetic_timestamps
        self.synthetic_fps = synthetic_fps
        self.base_provenance = base_provenance or ObservationProvenance()
        self.normalize_video_orientation = normalize_video_orientation
        self._clock = ReplayClock(replay_mode)
        self._container: av.container.InputContainer | None = None
        self._frames = None
        self._frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0
        self._rotation_degrees = 0

    def connect(self) -> Path:
        """Open the configured video and prepare playback state.

        This method initializes PyAV decoding decoders, parses stream
        metadata for orientation hints, and resets the replay clock.
        Must be called prior to requesting observations.

        Returns:
            The validated video file path.

        Raises:
            ValueError: When no valid video stream is detected.
        """
        self.disconnect()
        self._container = av.open(str(self.video_path))
        stream = next(iter(self._container.streams.video), None)
        if stream is None:
            self.disconnect()
            raise ValueError(f"No video stream found in {self.video_path}.")
        self._rotation_degrees = read_video_rotation_degrees(self.video_path) if self.normalize_video_orientation else 0
        self._frames = self._container.decode(video=0)
        self._frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0
        self._clock.reset()
        return self.video_path

    def disconnect(self) -> None:
        """Release sequence resources and halt PyAV container playback.

        This method acts safely as a no-op if the session is uninitialized
        or already closed.
        """
        if self._container is not None:
            self._container.close()
        self._container = None
        self._frames = None

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Decode and return the next sampled RGB observation seamlessly.

        This method blocks until the emulated clock matches the actual payload timestamp
        for the frame. It decodes the next valid raster, normalizes display orientation
        if configured to do so, rotates any supplied intrinsic camera models symmetrically,
        and constructs an :class:`~prml_vslam.interfaces.Observation` struct.

        Args:
            timeout_seconds: An optional wait maximum. Unused and ignored
                by this implementation.

        Returns:
            The fully synced observation payload.

        Raises:
            RuntimeError: If playback has not been initialized with ``connect()``.
            EOFError: If decoding finishes and ``loop`` is false.
        """
        del timeout_seconds
        self._require_connected()
        while True:
            try:
                frame = next(self._frames)
            except StopIteration:
                if not self.loop:
                    raise EOFError(f"Reached the end of {self.video_path}") from None
                self._restart()
                continue
            source_frame_index = self._frame_index
            self._frame_index += 1
            if source_frame_index % self.stride != 0:
                continue
            timestamp_ns = self._timestamp_ns_for_frame(source_frame_index, frame)
            self._clock.wait_until(timestamp_ns)
            rgb = np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)
            original_height, original_width = rgb.shape[:2]
            intrinsics = self.intrinsics
            if self._rotation_degrees:
                rgb = _rotate_rgb(rgb, self._rotation_degrees)
                intrinsics = _rotate_intrinsics(intrinsics, self._rotation_degrees)
            pose = self._pose_for_frame(source_frame_index)
            observation = Observation(
                seq=self._emitted_seq,
                timestamp_ns=timestamp_ns,
                source_frame_index=source_frame_index,
                loop_index=self._loop_index,
                arrival_timestamp_s=time.time(),
                rgb=rgb,
                intrinsics=intrinsics,
                T_world_camera=pose,
                provenance=self.base_provenance.model_copy(
                    update={
                        "video_rotation_degrees": self._rotation_degrees,
                        "original_width": int(original_width),
                        "original_height": int(original_height),
                    }
                ),
            )
            self._emitted_seq += 1
            return observation

    def _require_connected(self) -> None:
        if self._container is None or self._frames is None:
            raise RuntimeError("PyAvVideoObservationSource.connect() must be called before requesting observations.")

    def _restart(self) -> None:
        self.disconnect()
        self._container = av.open(str(self.video_path))
        self._frames = self._container.decode(video=0)
        self._frame_index = 0
        self._loop_index += 1
        self._clock.reset()

    def _timestamp_ns_for_frame(self, frame_index: int, frame: av.VideoFrame) -> int:
        if self.frame_timestamps_ns is not None and frame_index < len(self.frame_timestamps_ns):
            return int(self.frame_timestamps_ns[frame_index])
        if frame.time is not None:
            return int(round(float(frame.time) * 1e9))
        if self.allow_synthetic_timestamps and self.synthetic_fps is not None:
            return int(round(frame_index / self.synthetic_fps * 1e9))
        raise ValueError(
            f"Video frame {frame_index} in {self.video_path} has no dataset timestamp or PyAV presentation time."
        )

    def _pose_for_frame(self, frame_index: int) -> FrameTransform | None:
        poses_by_frame = self.poses_by_frame
        if poses_by_frame is None or frame_index >= len(poses_by_frame):
            return None
        return poses_by_frame[frame_index]


def read_video_rotation_degrees(video_path: Path) -> int:
    """Read display rotation metadata from a video file.

    Extracts the angle encoded by smartphones (or other video devices) using PyAV tools
    to inspect container properties, streams, and side data. If PyAV fails, falls back
    to OpenCV's orientation metadata capture.

    Args:
        video_path: The file path to the video.

    Returns:
        The normalized rotation in degrees (e.g., ``0, 90, 180, 270``), constrained
        to valid right-angle increments.

    Raises:
        ValueError: If no video stream is found or if PyAV abruptly raises
            container initialization errors without a fallback possible.
    """
    pyav_rotation: int | None = None
    try:
        with av.open(str(video_path)) as container:
            stream = next(iter(container.streams.video), None)
            if stream is None:
                raise ValueError("No video stream found.")
            if (rotation := _rotation_from_metadata(getattr(stream, "metadata", {}))) is not None:
                pyav_rotation = rotation
            if pyav_rotation in (None, 0):
                for frame in container.decode(video=0):
                    pyav_rotation = _rotation_from_frame(frame)
                    break
    except Exception as exc:
        raise ValueError(f"Failed to read video rotation metadata from {video_path}: {exc}") from exc
    if pyav_rotation not in (None, 0):
        return pyav_rotation
    cv2_rotation = _rotation_from_cv2(video_path)
    if cv2_rotation is not None:
        return cv2_rotation
    return 0 if pyav_rotation is None else pyav_rotation


def _rotation_from_metadata(metadata: dict[str, str] | None) -> int | None:
    for key in ("rotate", "rotation"):
        try:
            return None if metadata is None or metadata.get(key) is None else _normalize_rotation(float(metadata[key]))
        except (KeyError, TypeError, ValueError):
            continue
    return None


def _rotation_from_frame(frame: av.VideoFrame) -> int | None:
    return next(
        (
            rotation
            for side_data in getattr(frame, "side_data", ())
            if "display" in str(getattr(side_data, "type", "")).lower()
            and (rotation := _rotation_from_side_data(side_data)) is not None
        ),
        None,
    )


def _rotation_from_cv2(video_path: Path) -> int | None:
    import cv2

    orientation_meta = getattr(cv2, "CAP_PROP_ORIENTATION_META", None)
    if orientation_meta is None:
        return None
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            return None
        rotation = float(capture.get(orientation_meta))
    finally:
        capture.release()
    return None if not np.isfinite(rotation) else _normalize_rotation(rotation)


def _rotation_from_side_data(side_data: Any) -> int | None:
    for attr in ("rotation", "angle"):
        value = getattr(side_data, attr, None)
        if isinstance(value, str | int | float):
            try:
                return _normalize_rotation(float(value))
            except ValueError:
                return None
    to_ndarray = getattr(side_data, "to_ndarray", None)
    if not callable(to_ndarray):
        return None
    matrix = np.asarray(to_ndarray(), dtype=np.float64)
    if matrix.size < 4:
        return None
    matrix = matrix.reshape(3, 3) if matrix.size >= 9 else matrix.reshape(2, 2)
    return _normalize_rotation(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))


def _normalize_rotation(rotation_degrees: float) -> int:
    return int(np.rint(rotation_degrees / 90.0) * 90) % 360


def _rotate_rgb(rgb: np.ndarray, rotation_degrees: int) -> np.ndarray:
    quarter_turns = {90: 3, 180: 2, 270: 1}.get(rotation_degrees)
    return rgb if quarter_turns is None else np.ascontiguousarray(np.rot90(rgb, k=quarter_turns))


def _rotate_intrinsics(intrinsics: CameraIntrinsics | None, rotation_degrees: int) -> CameraIntrinsics | None:
    if intrinsics is None or rotation_degrees == 0:
        return intrinsics
    match rotation_degrees:
        case 90:
            update = {
                "width_px": intrinsics.height_px,
                "height_px": intrinsics.width_px,
                "fx": intrinsics.fy,
                "fy": intrinsics.fx,
                "cx": intrinsics.height_px - intrinsics.cy,
                "cy": intrinsics.cx,
            }
        case 180:
            update = {"cx": intrinsics.width_px - intrinsics.cx, "cy": intrinsics.height_px - intrinsics.cy}
        case 270:
            update = {
                "width_px": intrinsics.height_px,
                "height_px": intrinsics.width_px,
                "fx": intrinsics.fy,
                "fy": intrinsics.fx,
                "cx": intrinsics.cy,
                "cy": intrinsics.width_px - intrinsics.cx,
            }
        case _:
            return intrinsics
    return intrinsics.model_copy(update=update)


__all__ = ["PyAvVideoObservationSource", "read_video_rotation_degrees"]
