"""Pipeline runtime snapshot contracts."""

from __future__ import annotations

from enum import StrEnum

import numpy as np
from pydantic import Field

from prml_vslam.interfaces import FramePacket
from prml_vslam.methods.updates import SlamUpdate
from prml_vslam.utils import BaseData

from .artifacts import SlamArtifacts
from .plan import RunPlan
from .provenance import RunSummary, StageManifest
from .sequence import SequenceManifest

_EMPTY_TRAJECTORY_POSITIONS_XYZ = np.empty((0, 3), dtype=np.float64)
_EMPTY_TRAJECTORY_TIMESTAMPS_S = np.empty((0,), dtype=np.float64)


class RunState(StrEnum):
    """Lifecycle states exposed by the pipeline run services."""

    IDLE = "idle"
    PREPARING = "preparing"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class RunSnapshot(BaseData):
    """Pipeline-generic snapshot shared by offline and streaming execution."""

    state: RunState = RunState.IDLE
    """Current lifecycle state."""

    plan: RunPlan | None = None
    """Resolved run plan for the current or most recent execution."""

    sequence_manifest: SequenceManifest | None = None
    """Normalized sequence manifest prepared by the ingest stage."""

    slam: SlamArtifacts | None = None
    """Persisted SLAM artifacts returned by the backend."""

    summary: RunSummary | None = None
    """Final persisted run summary."""

    stage_manifests: list[StageManifest] = Field(default_factory=list)
    """Executed stage manifests owned by this slice."""

    error_message: str = ""
    """Last surfaced runtime error."""


class StreamingRunSnapshot(RunSnapshot):
    """Streaming-only runtime telemetry layered on top of the generic run snapshot."""

    latest_packet: FramePacket | None = None
    """Most recent frame packet, if any."""

    latest_slam_update: SlamUpdate | None = None
    """Most recent incremental SLAM update."""

    received_frames: int = 0
    """Number of processed packets since the current session started."""

    measured_fps: float = 0.0
    """Rolling measured packet rate."""

    accepted_keyframes: int = 0
    """Number of accepted keyframe poses reported by the backend."""

    backend_fps: float = 0.0
    """Rolling accepted-keyframe rate reported by the backend."""

    trajectory_positions_xyz: np.ndarray = Field(default_factory=_EMPTY_TRAJECTORY_POSITIONS_XYZ.copy)
    """Bounded keyframe trajectory history in world coordinates."""

    trajectory_timestamps_s: np.ndarray = Field(default_factory=_EMPTY_TRAJECTORY_TIMESTAMPS_S.copy)
    """Timestamps associated with `trajectory_positions_xyz`."""

    num_sparse_points: int = 0
    """Latest sparse-point count reported by the backend."""

    num_dense_points: int = 0
    """Latest dense-point count reported by the backend."""


__all__ = ["RunSnapshot", "RunState", "StreamingRunSnapshot"]
