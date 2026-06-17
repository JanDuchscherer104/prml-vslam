"""Source-stage runtime input and output contracts."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.sources.contracts import PreparedBenchmarkInputs, SequenceManifest
from prml_vslam.utils import BaseData


class SourceStageInput(BaseData):
    """Run-scoped input required to prepare one normalized source stage."""

    artifact_root: Path
    """Root directory for run-owned source artifacts."""

    mode: PipelineMode
    frame_stride: int = 1
    streaming_max_frames: int | None = None
    config_hash: str = ""
    input_fingerprint: str = ""


class SourceStageOutput(BaseData):
    """Bundle the normalized source result for downstream stages."""

    sequence_manifest: SequenceManifest
    benchmark_inputs: PreparedBenchmarkInputs | None = None


__all__ = ["SourceStageInput", "SourceStageOutput"]
