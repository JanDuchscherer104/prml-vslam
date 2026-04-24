"""Stage-local contracts for bounded reconstruction execution."""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs
from prml_vslam.pipeline.stages.reconstruction.config import ReconstructionBackend
from prml_vslam.utils import BaseData, RunArtifactPaths


class ReconstructionRuntimeInput(BaseData):
    """Inputs required to build one offline reference reconstruction.

    The current stage mode consumes prepared RGB-D observation references from
    source preparation and a reconstruction-owned backend config.
    """

    backend: ReconstructionBackend
    """Concrete reconstruction backend config."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark inputs containing one RGB-D observation sequence."""


__all__ = ["ReconstructionRuntimeInput"]
