"""Stage-local SLAM runtime input contracts.

These DTOs are private to the pipeline SLAM runtime boundary. They keep the
runtime protocol calls explicit without promoting stage-internal command shapes
to shared interfaces.
"""

from __future__ import annotations

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.utils import BaseData, PathConfig


class SlamOfflineInput(BaseData):
    """Input needed to run SLAM over one bounded normalized sequence."""

    run_config: RunConfig
    """Run config carrying backend, benchmark baseline, output, and visualization policy."""

    plan: RunPlan
    """Compiled run plan with artifact-root ownership."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence consumed by the SLAM backend."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared benchmark-side inputs used by method wrappers."""


class SlamStreamingStartInput(BaseData):
    """Input needed to start one incremental SLAM runtime."""

    run_config: RunConfig
    """Run config carrying backend, output, and visualization policy."""

    plan: RunPlan
    """Compiled run plan with artifact-root ownership."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence available before the first streaming frame."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared benchmark-side inputs available at stream start."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Selected benchmark trajectory baseline used by backend replay helpers."""


class SlamFrameInput(BaseData):
    """One frame command submitted to a running streaming SLAM runtime."""

    frame: FramePacket
    """Normalized frame packet consumed by the method backend session."""


__all__ = ["SlamFrameInput", "SlamOfflineInput", "SlamStreamingStartInput"]
