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

# TODO: how should we optimally distinguish between interfaces / protocols and DTOs / data models in terms of module organization and naming conventions? Should we define all dtos + modules that are stage specific as many here in the stage specific modules or should we define all of them in a dedicated dto module where the leav module indicates the stage?
