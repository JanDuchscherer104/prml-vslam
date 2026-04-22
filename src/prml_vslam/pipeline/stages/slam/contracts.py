"""Stage-local SLAM runtime input contracts.

These DTOs are private to the pipeline SLAM runtime boundary. They keep the
runtime protocol calls explicit without promoting stage-internal command shapes
to shared interfaces.
"""

from __future__ import annotations

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.interfaces.slam import SlamSessionInit
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData, PathConfig


class SlamOfflineInput(BaseData):
    """Input needed to run SLAM over one bounded normalized sequence."""

    request: RunRequest
    """Run request carrying backend, benchmark baseline, output, and visualization policy."""

    plan: RunPlan
    """Compiled run plan with artifact-root ownership."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence consumed by the SLAM backend."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared benchmark-side inputs used by method wrappers."""


class SlamStreamingStartInput(BaseData):
    """Input needed to start one incremental SLAM runtime session."""

    request: RunRequest
    """Run request carrying backend, output, and visualization policy."""

    plan: RunPlan
    """Compiled run plan with artifact-root ownership."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    session_init: SlamSessionInit
    """Method/session initialization payload kept as a WP-06 migration contact."""


class SlamFrameInput(BaseData):
    """One frame command submitted to a running streaming SLAM runtime."""

    frame: FramePacket
    """Normalized frame packet consumed by the method backend session."""


__all__ = ["SlamFrameInput", "SlamOfflineInput", "SlamStreamingStartInput"]
