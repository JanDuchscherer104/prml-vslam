"""Typed contracts for reusable pipeline planning surfaces."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import Field

from prml_vslam.utils import BaseConfig


class MethodId(str, Enum):
    """Supported external monocular VSLAM backends."""

    VISTA_SLAM = "vista_slam"
    MAST3R_SLAM = "mast3r_slam"


class RunPlanStageId(str, Enum):
    """Canonical stage identifiers in the benchmark planner."""

    INGEST = "ingest"
    SLAM = "slam"
    DENSE_MAPPING = "dense_mapping"
    ARCORE_COMPARISON = "arcore_comparison"
    REFERENCE_RECONSTRUCTION = "reference_reconstruction"


class RunPlanRequest(BaseConfig):
    """Input contract for planning a benchmark run."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    video_path: Path
    """Path to the input video that will be processed."""

    output_dir: Path
    """Root directory where planned artifacts should be written."""

    method: MethodId
    """External monocular VSLAM backend to use for the run."""

    frame_stride: int = 1
    """Frame subsampling stride applied during ingestion."""

    enable_dense_mapping: bool = True
    """Whether the plan should include dense map export."""

    compare_to_arcore: bool = True
    """Whether the plan should reserve an ARCore comparison stage."""

    build_ground_truth_cloud: bool = True
    """Whether the plan should include a reference reconstruction stage."""


class RunPlanStage(BaseConfig):
    """One typed stage in a benchmark run plan."""

    id: RunPlanStageId
    """Stable identifier for the stage."""

    title: str
    """Short human-readable stage title."""

    summary: str
    """Short description of the stage intent."""

    outputs: list[Path] = Field(default_factory=list)
    """Expected artifact paths for the stage."""


class RunPlan(BaseConfig):
    """Planner output returned to the CLI or UI layer."""

    experiment_name: str
    """Human-readable name for the benchmark run."""

    method: MethodId
    """External monocular VSLAM backend chosen for the run."""

    input_video: Path
    """Input video path associated with the run."""

    artifact_root: Path
    """Root directory for all run artifacts."""

    stages: list[RunPlanStage] = Field(default_factory=list)
    """Ordered execution stages for the benchmark run."""


__all__ = [
    "MethodId",
    "RunPlan",
    "RunPlanRequest",
    "RunPlanStage",
    "RunPlanStageId",
]
