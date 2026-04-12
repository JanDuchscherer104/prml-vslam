"""Project package for the PRML VSLAM benchmark scaffold."""

from .interfaces import CameraIntrinsics, FramePacket, FrameTransform

__all__ = [
    "CameraIntrinsics",
    "FrameTransform",
    "FramePacket",
    "__version__",
]

__version__ = "0.1.0"
