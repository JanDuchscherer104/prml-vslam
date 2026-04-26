"""Curated import surface for repo-wide shared DTOs."""

from .alignment import GroundAlignmentMetadata, GroundPlaneModel, GroundPlaneVisualizationHint
from .camera import CameraIntrinsics, CameraIntrinsicsSample, CameraIntrinsicsSeries
from .geometry import DepthMap, PointCloud, PointMap
from .observation import (
    CAMERA_RDF_FRAME,
    OBSERVATION_SEQUENCE_FORMAT,
    Observation,
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from .transforms import FrameTransform
from .visualization import VisualizationArtifacts

__all__ = [
    "CameraIntrinsics",
    "CameraIntrinsicsSample",
    "CameraIntrinsicsSeries",
    "CAMERA_RDF_FRAME",
    "DepthMap",
    "FrameTransform",
    "GroundAlignmentMetadata",
    "GroundPlaneModel",
    "GroundPlaneVisualizationHint",
    "OBSERVATION_SEQUENCE_FORMAT",
    "Observation",
    "ObservationIndexEntry",
    "ObservationProvenance",
    "ObservationSequenceIndex",
    "ObservationSequenceRef",
    "PointCloud",
    "PointMap",
    "VisualizationArtifacts",
]
