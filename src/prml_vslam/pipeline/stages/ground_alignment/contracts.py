"""Stage-local contracts for bounded ground-alignment execution."""

from __future__ import annotations

from prml_vslam.interfaces.slam import SlamArtifacts
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData, RunArtifactPaths


class GroundAlignmentRuntimeInput(BaseData):
    """Inputs required to derive ground-alignment metadata from SLAM outputs."""

    # TODO(pipeline-refactor/WP-09): Replace RunRequest with target RunConfig
    # stage policy once bounded runtimes are constructed from stage configs.
    request: RunRequest
    """Current run request carrying alignment policy."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    slam: SlamArtifacts
    """Normalized SLAM artifact bundle consumed by the alignment service."""


__all__ = ["GroundAlignmentRuntimeInput"]
