"""Point-cloud alignment stage runtime input contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.utils import BaseData


class CloudAlignmentStageInput(BaseData):
    """Inputs required to refine a Sim(3)-aligned SLAM cloud against a reference cloud."""

    artifact_root: Path
    reference_cloud: ArtifactRef
    sim3_point_cloud: ArtifactRef
    max_correspondence_distance_m: float = 0.05


__all__ = ["CloudAlignmentStageInput"]
