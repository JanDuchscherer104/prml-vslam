"""Repo-wide source-provider protocol seams."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from prml_vslam.benchmark import PreparedBenchmarkInputs
from prml_vslam.pipeline.contracts.sequence import SequenceManifest

from .runtime import FramePacketStream


@runtime_checkable
class OfflineSequenceSource(Protocol):
    """Protocol for sources that can materialize the normalized offline boundary."""

    label: str

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize or resolve the normalized sequence boundary for one run."""


@runtime_checkable
class BenchmarkInputSource(Protocol):
    """Optional protocol for sources that can prepare benchmark-side inputs."""

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs | None:
        """Materialize prepared benchmark inputs for one run."""


@runtime_checkable
class StreamingSequenceSource(OfflineSequenceSource, Protocol):
    """Protocol for replay or live sources used by streaming pipeline sessions."""

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the frame stream consumed by the SLAM session."""


__all__ = [
    "BenchmarkInputSource",
    "OfflineSequenceSource",
    "StreamingSequenceSource",
]
