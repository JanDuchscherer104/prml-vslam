"""Method-owned streaming session initialization contracts."""

from __future__ import annotations

from prml_vslam.benchmark import PreparedBenchmarkInputs, ReferenceSource
from prml_vslam.pipeline.contracts.sequence import SequenceManifest
from prml_vslam.utils import BaseData

# TODO: this is a dto / data model that should be defined in a shared model module!


class SlamSessionInit(BaseData):
    """Normalized context injected once when a streaming session starts."""

    sequence_manifest: SequenceManifest
    """Prepared normalized sequence boundary for the current run."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Prepared benchmark-side inputs available for the current run, when any."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Selected reference trajectory source for benchmark-aware backends."""


__all__ = ["SlamSessionInit"]
