"""Stage-local SLAM runtime input contracts.

These DTOs are private to the pipeline SLAM runtime boundary. They keep the
runtime protocol calls explicit without promoting stage-internal command shapes
to shared interfaces.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.interfaces.runtime import FramePacket
from prml_vslam.pipeline.stages.slam.config import BackendConfig, SlamOutputPolicy
from prml_vslam.utils import BaseData, PathConfig


class SlamOfflineInput(BaseData):
    """Input needed to run SLAM over one bounded normalized sequence."""

    backend: BackendConfig
    """Concrete backend config used to construct the method adapter."""

    outputs: SlamOutputPolicy
    """SLAM output materialization policy."""

    artifact_root: Path
    """Run-owned artifact root where SLAM outputs are written."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Selected benchmark trajectory baseline used by replay helpers."""

    preserve_native_rerun: bool = False
    """Whether native Rerun outputs should be retained as durable artifacts."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence consumed by the SLAM backend."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared benchmark-side inputs used by method wrappers."""


class SlamStreamingStartInput(BaseData):
    """Input needed to start one incremental SLAM runtime."""

    backend: BackendConfig
    """Concrete backend config used to construct the method adapter."""

    outputs: SlamOutputPolicy
    """SLAM output materialization policy."""

    artifact_root: Path
    """Run-owned artifact root where SLAM outputs are written."""

    path_config: PathConfig
    """Repository path configuration for backend construction."""

    sequence_manifest: SequenceManifest
    """Normalized source sequence available before the first streaming frame."""

    benchmark_inputs: PreparedBenchmarkInputs | None = None
    """Optional prepared benchmark-side inputs available at stream start."""

    baseline_source: ReferenceSource = ReferenceSource.GROUND_TRUTH
    """Selected benchmark trajectory baseline used by backend replay helpers."""

    log_diagnostic_preview: bool = False
    """Whether live preview images should be emitted in runtime updates."""

    preserve_native_rerun: bool = False
    """Whether native Rerun outputs should be retained as durable artifacts."""


class SlamFrameInput(BaseData):
    """One frame command submitted to a running streaming SLAM runtime."""

    frame: FramePacket
    """Normalized frame packet consumed by the method backend session."""


__all__ = ["SlamFrameInput", "SlamOfflineInput", "SlamStreamingStartInput"]
