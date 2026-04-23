"""Stage-local contracts for bounded ground-alignment execution."""

from __future__ import annotations

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.utils import BaseData, RunArtifactPaths


class GroundAlignmentRuntimeInput(BaseData):
    """Inputs required to derive ground-alignment metadata from SLAM outputs.

    The stage consumes completed SLAM artifacts and current alignment policy,
    then writes a derived metadata artifact. It does not alter the native
    trajectory or point cloud referenced by :attr:`slam`.
    """

    run_config: RunConfig
    """Current run config carrying alignment policy."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    slam: SlamArtifacts
    """Normalized SLAM artifact bundle consumed by the alignment service."""


__all__ = ["GroundAlignmentRuntimeInput"]
