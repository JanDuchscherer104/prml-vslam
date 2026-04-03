"""Project package for the PRML VSLAM benchmark scaffold."""

from .interfaces import CameraIntrinsics, FramePacket, FramePacketStream, SE3Pose, TimedPoseTrajectory

__all__ = [
    "CameraIntrinsics",
    "FramePacket",
    "FramePacketStream",
    "SE3Pose",
    "TimedPoseTrajectory",
    "__version__",
]

__version__ = "0.1.0"
