"""Repo-wide canonical shared DTOs."""

from .alignment import GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint
from .camera import CameraIntrinsics
from .ingest import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferenceCloudRef,
    ReferencePointCloudSequenceRef,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from .runtime import FramePacket, FramePacketProvenance, Record3DTransportId
from .slam import (
    ArtifactRef,
    BackendError,
    BackendEvent,
    BackendWarning,
    KeyframeAccepted,
    KeyframeVisualizationReady,
    MapStatsUpdated,
    PoseEstimated,
    SessionClosed,
    SlamArtifacts,
    SlamSessionInit,
    SlamUpdate,
)
from .transforms import FrameTransform
from .visualization import VisualizationArtifacts

__all__ = [
    "AdvioManifestAssets",
    "AdvioRawPoseRefs",
    "ArtifactRef",
    "BackendError",
    "BackendEvent",
    "BackendWarning",
    "CameraIntrinsics",
    "FramePacket",
    "FramePacketProvenance",
    "FrameTransform",
    "GroundAlignmentMetadata",
    "GroundPlaneModel",
    "GroundPlaneVisualizationHint",
    "KeyframeAccepted",
    "KeyframeVisualizationReady",
    "MapStatsUpdated",
    "PoseEstimated",
    "PreparedBenchmarkInputs",
    "Record3DTransportId",
    "ReferenceCloudRef",
    "ReferencePointCloudSequenceRef",
    "ReferenceTrajectoryRef",
    "SequenceManifest",
    "SessionClosed",
    "SlamArtifacts",
    "SlamSessionInit",
    "SlamUpdate",
    "VisualizationArtifacts",
]
