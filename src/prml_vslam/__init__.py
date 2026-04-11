"""Project package for the PRML VSLAM benchmark scaffold."""

from .interfaces import CameraIntrinsics, FramePacket, FrameTransform, SE3Pose

__all__ = [
    "CameraIntrinsics",
    "FrameTransform",
    "FramePacket",
    "SE3Pose",
    "__version__",
]

__version__ = "0.1.0"
