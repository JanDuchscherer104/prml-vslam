"""Alignment algorithms and pipeline stages: gravity detection, Sim(3) trajectory, ICP point cloud."""

from .gravity import (
    GroundAlignmentConfig,
    GroundAlignmentRuntime,
    GroundAlignmentService,
    GroundAlignmentStageConfig,
    GroundAlignmentStageInput,
)
from .icp import CloudAlignmentService
from .trajectory_sim3 import (
    align_estimate_sim3,
    is_gravity_aligned_target,
    sim3_up_axis_tilt_deg,
    trajectory_supports_sim3,
)

__all__ = [
    "CloudAlignmentService",
    "GroundAlignmentConfig",
    "GroundAlignmentRuntime",
    "GroundAlignmentService",
    "GroundAlignmentStageConfig",
    "GroundAlignmentStageInput",
    "align_estimate_sim3",
    "is_gravity_aligned_target",
    "sim3_up_axis_tilt_deg",
    "trajectory_supports_sim3",
]
