"""Curated import surface for repo-wide shared DTOs.

The ``interfaces`` package should expose only datamodels whose semantics are
identical across multiple top-level packages, such as camera intrinsics,
runtime frame packets, frame-labelled transforms, ingest manifests, and
normalized artifact bundles. Live SLAM notices are still re-exported here as
migration contacts; target ownership moves method-live semantics toward
``prml_vslam.methods`` and pipeline-live transport toward stage runtime
contracts.
"""

from .alignment import GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint
from .camera import CameraIntrinsics, CameraIntrinsicsSample, CameraIntrinsicsSeries
from .ingest import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
    PreparedBenchmarkInputs,
    ReferenceCloudRef,
    ReferencePointCloudSequenceRef,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from .rgbd import (
    RGBD_OBSERVATION_SEQUENCE_FORMAT,
    RgbdObservation,
    RgbdObservationIndexEntry,
    RgbdObservationProvenance,
    RgbdObservationSequenceIndex,
    RgbdObservationSequenceRef,
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
    "CameraIntrinsicsSample",
    "CameraIntrinsicsSeries",
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
    "RGBD_OBSERVATION_SEQUENCE_FORMAT",
    "RgbdObservation",
    "RgbdObservationIndexEntry",
    "RgbdObservationProvenance",
    "RgbdObservationSequenceIndex",
    "RgbdObservationSequenceRef",
    "SequenceManifest",
    "SessionClosed",
    "SlamArtifacts",
    "SlamSessionInit",
    "SlamUpdate",
    "VisualizationArtifacts",
]

# TODO: how should we optimally distinguish between interfaces / protocols and DTOs / data models in terms of module organization and naming conventions? Should we define all dtos + modules that are stage specific as many here in the stage specific modules or should we define all of them in a dedicated dto module where the leav module indicates the stage?
