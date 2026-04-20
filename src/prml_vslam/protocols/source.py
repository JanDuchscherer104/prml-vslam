"""Repo-wide source-provider seams for offline and streaming execution.

These protocols define how dataset adapters, video adapters, and live sources
hand normalized data into :mod:`prml_vslam.pipeline`. They intentionally stop
at source preparation and streaming packet delivery; planning, stage order, and
artifact ownership remain in :mod:`prml_vslam.pipeline`.
"""

from __future__ import annotations

from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from prml_vslam.interfaces.ingest import PreparedBenchmarkInputs

from .runtime import FramePacketStream

if TYPE_CHECKING:
    from prml_vslam.interfaces.ingest import SequenceManifest


@runtime_checkable
class OfflineSequenceSource(Protocol):
    """Materialize the normalized offline input boundary for one run.

    Implementations are responsible for producing a
    :class:`prml_vslam.pipeline.contracts.sequence.SequenceManifest`, not for
    deciding which stages run next. This keeps source-specific setup in the
    source owner while leaving orchestration to :mod:`prml_vslam.pipeline`.
    """

    label: str

    @abstractmethod
    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize or resolve the normalized :class:`SequenceManifest` for one run."""


@runtime_checkable
class BenchmarkInputSource(Protocol):
    """Optionally materialize prepared benchmark-side reference inputs."""

    @abstractmethod
    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs | None:
        """Materialize prepared benchmark inputs that complement the offline sequence."""


@runtime_checkable
class StreamingSequenceSource(OfflineSequenceSource, Protocol):
    """Extend :class:`OfflineSequenceSource` with a live or replay packet stream.

    Streaming execution still relies on an offline-style normalized source
    manifest for session initialization, then consumes live
    :class:`prml_vslam.interfaces.FramePacket` values through
    :class:`prml_vslam.protocols.runtime.FramePacketStream`.
    """

    @abstractmethod
    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the frame stream that feeds the active SLAM session."""


__all__ = [
    "BenchmarkInputSource",
    "OfflineSequenceSource",
    "StreamingSequenceSource",
]
