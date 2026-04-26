"""Stage-local SLAM runtime input contracts.

These DTOs are private to the pipeline SLAM runtime boundary. They keep the
runtime protocol calls explicit without promoting stage-internal command shapes
to shared interfaces.
"""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.visualization import VisualizationArtifacts
from prml_vslam.methods.contracts import SlamArtifacts
from prml_vslam.methods.stage.backend_config import BackendConfig, SlamOutputPolicy
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, ReferenceSource, SequenceManifest
from prml_vslam.utils import BaseData, PathConfig


class SlamOfflineStageInput(BaseData):
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


class SlamStreamingStartStageInput(BaseData):
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


class SlamStageOutput(BaseData):
    """Terminal SLAM output consumed by downstream stage input builders."""

    artifacts: SlamArtifacts
    """Normalized durable artifacts produced by the SLAM backend."""

    visualization: VisualizationArtifacts | None = None
    """Optional native visualization artifacts collected during finalization."""


__all__ = ["SlamOfflineStageInput", "SlamStageOutput", "SlamStreamingStartStageInput"]
