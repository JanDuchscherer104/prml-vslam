"""Small protocol surface for pipeline backends and runners."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import FramePacket, SE3Pose
from prml_vslam.methods.interfaces import MethodId
from prml_vslam.pipeline.contracts import (
    CloudMetrics,
    DenseArtifacts,
    DenseConfig,
    ReferenceArtifacts,
    ReferenceConfig,
    SequenceManifest,
    TrackingArtifacts,
    TrackingConfig,
    TrajectoryMetrics,
)
from prml_vslam.utils import BaseData


class TrackingUpdate(BaseData):
    """Incremental tracking update emitted by streaming-capable backends."""

    seq: int
    """Frame sequence number associated with the update."""

    timestamp_ns: int
    """Timestamp in nanoseconds."""

    pose: SE3Pose | None = None
    """Optional canonical pose estimate."""

    num_map_points: int = 0
    """Current sparse map size when the backend exposes it."""

    num_dense_points: int = 0
    """Current cumulative dense-point count when the backend exposes reconstruction output."""

    pointmap: NDArray[np.float32] | None = None
    """Optional HxWx3 pointmap in camera coordinates for the current frame."""

    uncertainty: NDArray[np.float32] | None = None
    """Optional HxW uncertainty map for the current frame, aligned with the pointmap if present."""


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


class DenseBackend(Protocol):
    """Protocol for dense-reconstruction stages."""

    def run(self, track: TrackingArtifacts, cfg: DenseConfig, artifact_root: Path) -> DenseArtifacts:
        """Run dense reconstruction from tracking artifacts."""


class ReferenceBuilder(Protocol):
    """Protocol for reference-reconstruction stages."""

    def run(
        self,
        sequence: SequenceManifest,
        cfg: ReferenceConfig,
        artifact_root: Path,
    ) -> ReferenceArtifacts:
        """Build a reference reconstruction for the normalized sequence."""


class TrajectoryEvaluator(Protocol):
    """Protocol for trajectory-evaluation stages."""

    def run(
        self,
        track: TrackingArtifacts,
        sequence: SequenceManifest,
        artifact_root: Path,
    ) -> TrajectoryMetrics:
        """Evaluate the estimated trajectory against the normalized sequence."""


class CloudEvaluator(Protocol):
    """Protocol for dense-cloud evaluation stages."""

    def run(
        self,
        dense: DenseArtifacts,
        reference: ReferenceArtifacts,
        artifact_root: Path,
    ) -> CloudMetrics:
        """Evaluate the reconstructed dense cloud against the reference."""


__all__ = [
    "CloudEvaluator",
    "DenseBackend",
    "OfflineTrackerBackend",
    "ReferenceBuilder",
    "StreamingTrackerBackend",
    "TrackingUpdate",
    "TrajectoryEvaluator",
]
