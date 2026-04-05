"""Current protocol seams for the pipeline streaming and tracking runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.contracts import MethodId
from prml_vslam.pipeline.contracts import (
    SequenceManifest,
    TrackingArtifacts,
    TrackingConfig,
    TrackingUpdate,
)
from prml_vslam.protocols import FramePacketStream


class StreamingSequenceSource(Protocol):
    """Protocol for replay or live sources used by streaming pipeline sessions."""

    label: str

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        """Materialize or resolve the normalized sequence boundary for one run."""

    def open_stream(self, *, loop: bool) -> FramePacketStream:
        """Open the frame stream consumed by the tracking session."""


class OfflineTrackerBackend(Protocol):
    """Protocol for backends that run over a materialized sequence offline."""

    method_id: MethodId

    def run_sequence(
        self,
        sequence: SequenceManifest,
        cfg: TrackingConfig,
        artifact_root: Path,
    ) -> TrackingArtifacts:
        """Run the backend over a materialized sequence and persist artifacts."""


class StreamingTrackerBackend(Protocol):
    """Protocol for backends that can consume live or replayed frames incrementally."""

    method_id: MethodId

    def open(self, cfg: TrackingConfig, artifact_root: Path) -> None:
        """Prepare the backend for streaming updates."""

    def step(self, frame: FramePacket) -> TrackingUpdate:
        """Consume one frame and return an incremental tracking update."""

    def close(self) -> TrackingArtifacts:
        """Finalize the backend and return the persisted tracking artifacts."""


__all__ = [
    "OfflineTrackerBackend",
    "StreamingSequenceSource",
    "StreamingTrackerBackend",
]
