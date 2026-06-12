"""Ground-alignment stage runtime input contracts."""

from __future__ import annotations

from typing import Self

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, model_validator

from prml_vslam.alignment.contracts import GroundAlignmentConfig
from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.utils import BaseData, RunArtifactPaths


class GroundAlignmentStageInput(BaseData):
    """Inputs required to derive ground-alignment metadata from SLAM outputs."""

    config: GroundAlignmentConfig
    run_paths: RunArtifactPaths
    slam: SlamArtifacts


class GroundAlignmentStreamingStartInput(BaseData):
    """Run-scoped payload used to start live ground alignment."""

    config: GroundAlignmentConfig
    run_paths: RunArtifactPaths


class GroundAlignmentKeyframeSample(BaseData):
    """Dense camera-local pointmap sample accepted from a SLAM keyframe update."""

    keyframe_index: int = Field(ge=0)
    T_world_camera: FrameTransform
    pointmap_xyz_camera: NDArray[np.float32]

    @model_validator(mode="after")
    def validate_pointmap_shape(self) -> Self:
        """Normalize and validate dense camera-local pointmap geometry."""
        pointmap = np.asarray(self.pointmap_xyz_camera, dtype=np.float32)
        if pointmap.ndim != 3 or pointmap.shape[-1] != 3:
            raise ValueError(f"Expected camera-local pointmap shape (H, W, 3), got {pointmap.shape}.")
        object.__setattr__(self, "pointmap_xyz_camera", pointmap)
        return self


__all__ = [
    "GroundAlignmentKeyframeSample",
    "GroundAlignmentStageInput",
    "GroundAlignmentStreamingStartInput",
]
