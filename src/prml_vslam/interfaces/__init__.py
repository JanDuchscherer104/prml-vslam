"""Curated import surface for repo-wide shared DTOs.

The ``interfaces`` package should expose only datamodels whose semantics are
identical across multiple top-level packages, such as camera intrinsics,
runtime frame packets, frame-labelled transforms, ingest manifests, and
normalized artifact bundles.
"""

from .alignment import GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint
from .camera import CameraIntrinsics, CameraIntrinsicsSample, CameraIntrinsicsSeries
from .geometry import DepthMap, PointCloud, PointMap
from .ingest import (
    AdvioManifestAssets,
    AdvioRawPoseRefs,
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
from .transforms import FrameTransform
from .visualization import VisualizationArtifacts

__all__ = [
    "AdvioManifestAssets",
    "AdvioRawPoseRefs",
    "CameraIntrinsics",
    "CameraIntrinsicsSample",
    "CameraIntrinsicsSeries",
    "DepthMap",
    "FramePacket",
    "FramePacketProvenance",
    "FrameTransform",
    "GroundAlignmentMetadata",
    "GroundPlaneModel",
    "GroundPlaneVisualizationHint",
    "PointCloud",
    "PointMap",
    "Record3DTransportId",
    "RGBD_OBSERVATION_SEQUENCE_FORMAT",
    "RgbdObservation",
    "RgbdObservationIndexEntry",
    "RgbdObservationProvenance",
    "RgbdObservationSequenceIndex",
    "RgbdObservationSequenceRef",
    "SequenceManifest",
    "VisualizationArtifacts",
]
