"""Project package for the PRML VSLAM benchmark scaffold."""

from .interfaces import CameraIntrinsics, FramePacket, SE3Pose, TimedPoseTrajectory

__all__ = [
    "CameraIntrinsics",
    "FramePacket",
    "SE3Pose",
    "TimedPoseTrajectory",
    "__version__",
]

__version__ = "0.1.0"
