"""PyAV-backed video replay source."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Iterator
from fractions import Fraction
from pathlib import Path
from typing import Any

import av
import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform, Observation, ObservationProvenance
from prml_vslam.interfaces.observation import ObservationIndexEntry

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


class VideoSequenceObservationSource:
    """Replay a normalized RGB video synchronized to observation-index rows."""

    def __init__(
        self,
        *,
        video_path: Path,
        payload_root: Path,
        rows: list[ObservationIndexEntry],
        loop: bool = False,
        replay_mode: ReplayMode = ReplayMode.FAST_AS_POSSIBLE,
        include_depth: bool = True,
        depth_loader: Callable[[Path], NDArray[np.float32]] | None = None,
    ) -> None:
        self.video_path = video_path
        self.payload_root = payload_root
        self.rows = rows
        self.loop = loop
        self.include_depth = include_depth
        self.depth_loader = depth_loader
        self._clock = ReplayClock(replay_mode)
        self._container: av.container.InputContainer | None = None
        self._frames: Iterator[av.VideoFrame] | None = None
        self._row_index = 0
        self._video_frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0

    def connect(self) -> Path:
        """Open the normalized RGB video and reset replay state."""
        self.disconnect()
        self._container = av.open(str(self.video_path))
        if next(iter(self._container.streams.video), None) is None:
            self.disconnect()
            raise ValueError(f"No video stream found in {self.video_path}.")
        self._frames = self._container.decode(video=0)
        self._row_index = 0
        self._video_frame_index = 0
        self._emitted_seq = 0
        self._loop_index = 0
        self._clock.reset()
        return self.video_path

    def disconnect(self) -> None:
        """Release PyAV resources."""
        if self._container is not None:
            self._container.close()
        self._container = None
        self._frames = None

    def wait_for_observation(self, timeout_seconds: float | None = None) -> Observation:
        """Decode the next row-selected video frame."""
        del timeout_seconds
        self._require_connected()
        while True:
            if self._row_index >= len(self.rows):
                if not self.loop:
                    raise EOFError(f"Reached the end of {self.video_path}")
                self._restart()
                continue
            row = self.rows[self._row_index]
            target_video_index = row.rgb_video_frame_index if row.rgb_video_frame_index is not None else row.seq
            rgb = self._decode_until(target_video_index)
            self._row_index += 1
            self._clock.wait_until(row.timestamp_ns)
            depth_m = self._load_depth(row)
            observation_source_frame_index = (
                row.provenance.source_frame_index
                if row.provenance.source_frame_index is not None
                else target_video_index
            )
            observation = Observation(
                seq=self._emitted_seq,
                timestamp_ns=row.timestamp_ns,
                source_frame_index=observation_source_frame_index,
                loop_index=self._loop_index,
                arrival_timestamp_s=time.time(),
                rgb=rgb,
                depth_m=depth_m,
                intrinsics=row.intrinsics,
                T_world_camera=row.T_world_camera,
                provenance=row.provenance.model_copy(update={"source_frame_index": observation_source_frame_index}),
            )
            self._emitted_seq += 1
            return observation

    def _require_connected(self) -> None:
        if self._container is None or self._frames is None:
            raise RuntimeError(
                "VideoSequenceObservationSource.connect() must be called before requesting observations."
            )

    def _restart(self) -> None:
        self.disconnect()
        self._container = av.open(str(self.video_path))
        self._frames = self._container.decode(video=0)
        self._row_index = 0
        self._video_frame_index = 0
        self._loop_index += 1
        self._clock.reset()

    def _decode_until(self, target_video_index: int) -> NDArray[np.uint8]:
        self._require_connected()
        if target_video_index < self._video_frame_index:
            raise ValueError("Video-backed observation rows must be sorted by rgb_video_frame_index.")
        while True:
            try:
                frame = next(self._frames)
            except StopIteration as exc:
                raise EOFError(f"Video '{self.video_path}' ended before frame index {target_video_index}.") from exc
            current_index = self._video_frame_index
            self._video_frame_index += 1
            if current_index == target_video_index:
                return np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)

    def _load_depth(self, row: ObservationIndexEntry) -> NDArray[np.float32] | None:
        if not self.include_depth or row.depth_path is None:
            return None
        if self.depth_loader is None:
            raise RuntimeError("A depth loader is required when include_depth=True and a row has a depth path.")
        return self.depth_loader(_resolve_video_payload(row.depth_path, self.payload_root)) * row.depth_scale_to_m


def write_rgb_video(path: Path, frames: Iterable[NDArray[np.uint8]], *, fps: float = 15.0) -> Path:
    """Encode RGB frames into a compact normalized video payload."""
    iterator = iter(frames)
    try:
        first_frame = _as_rgb_frame(next(iterator))
    except StopIteration:
        raise ValueError("Cannot write an empty RGB video.") from None
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), mode="w") as container:
        stream = container.add_stream("mpeg4", rate=Fraction(max(float(fps), 1.0)).limit_denominator(1000))
        stream.width = int(first_frame.shape[1])
        stream.height = int(first_frame.shape[0])
        stream.pix_fmt = "yuv420p"
        _encode_rgb_frame(container, stream, first_frame)
        for frame in iterator:
            _encode_rgb_frame(container, stream, _as_rgb_frame(frame))
        for packet in stream.encode():
            container.mux(packet)
    return path.resolve()


def iter_rgb_video_frames(video_path: Path, frame_indices: Iterable[int] | None = None) -> Iterator[NDArray[np.uint8]]:
    """Yield RGB frames from a video, optionally filtering by zero-based frame index."""
    requested = None if frame_indices is None else set(frame_indices)
    with av.open(str(video_path)) as container:
        for frame_index, frame in enumerate(container.decode(video=0)):
            if requested is None or frame_index in requested:
                yield np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)


def _encode_rgb_frame(
    container: av.container.OutputContainer, stream: av.video.stream.VideoStream, rgb: NDArray[np.uint8]
) -> None:
    video_frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
    for packet in stream.encode(video_frame):
        container.mux(packet)


def _as_rgb_frame(frame: NDArray[np.uint8]) -> NDArray[np.uint8]:
    rgb = np.asarray(frame, dtype=np.uint8)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"Expected RGB video frame shape (H, W, 3), got {rgb.shape}.")
    return np.ascontiguousarray(rgb)


def _resolve_video_payload(path: Path, root: Path) -> Path:
    return path if path.is_absolute() else root / path


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


__all__ = [
    "PyAvVideoObservationSource",
    "VideoSequenceObservationSource",
    "iter_rgb_video_frames",
    "read_video_rotation_degrees",
    "write_rgb_video",
]
