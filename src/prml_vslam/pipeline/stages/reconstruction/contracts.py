"""Stage-local contracts for bounded reconstruction execution."""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.utils import BaseData, RunArtifactPaths


class ReconstructionRuntimeInput(BaseData):
    """Inputs required to build one offline reference reconstruction.

    The current input is compatibility-shaped around benchmark reference policy.
    The target ``reconstruction`` stage should receive reconstruction stage
    config plus reconstruction-owned backend config, while continuing to consume
    prepared RGB-D observation references from source/benchmark preparation.
    """

    run_config: RunConfig
    """Current run config carrying reference-reconstruction policy."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark inputs containing one RGB-D observation sequence."""


__all__ = ["ReconstructionRuntimeInput"]
