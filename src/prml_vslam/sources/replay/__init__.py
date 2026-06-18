"""Shared replay primitives for source-owned observation streams."""

from .clock import ReplayClock, ReplayMode
from .image_sequence import ImageSequenceObservationSource
from .protocols import ObservationStream
from .video import (
    PyAvVideoObservationSource,
    VideoSequenceObservationSource,
    iter_rgb_video_frames,
    read_video_rotation_degrees,
    write_rgb_video,
)

__all__ = [
    "ImageSequenceObservationSource",
    "PyAvVideoObservationSource",
    "VideoSequenceObservationSource",
    "iter_rgb_video_frames",
    "read_video_rotation_degrees",
    "write_rgb_video",
    "ReplayClock",
    "ReplayMode",
    "ObservationStream",
]
