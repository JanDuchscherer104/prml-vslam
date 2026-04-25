"""Ground-alignment stage runtime input contracts."""

from __future__ import annotations

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.utils import BaseData, RunArtifactPaths


class GroundAlignmentStageInput(BaseData):
    """Inputs required to derive ground-alignment metadata from SLAM outputs."""

    config: GroundAlignmentConfig
    run_paths: RunArtifactPaths
    slam: SlamArtifacts


__all__ = ["GroundAlignmentStageInput"]
