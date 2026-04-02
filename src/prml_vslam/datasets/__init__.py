"""Dataset adapters for benchmark inputs and replay sources."""

from __future__ import annotations

from .interfaces import DatasetId, TimedPoseTrajectory

_ADVIO_EXPORTS = {
    "ADVIO_SEQUENCE_COUNT",
    "AdvioCalibration",
    "AdvioCatalog",
    "AdvioDatasetService",
    "AdvioDatasetSummary",
    "AdvioDownloadPreset",
    "AdvioDownloadRequest",
    "AdvioDownloadResult",
    "AdvioEnvironment",
    "AdvioLocalSceneStatus",
    "AdvioModality",
    "AdvioOfflineSample",
    "AdvioPeopleLevel",
    "AdvioPoseSource",
    "AdvioSceneMetadata",
    "AdvioSequence",
    "AdvioSequenceConfig",
    "AdvioSequencePaths",
    "AdvioUpstreamMetadata",
    "list_advio_sequence_ids",
    "load_advio_calibration",
    "load_advio_catalog",
    "load_advio_frame_timestamps_ns",
    "load_advio_sequence",
    "load_advio_trajectory",
    "write_advio_pose_tum",
}

__all__ = [
    "ADVIO_SEQUENCE_COUNT",
    "AdvioCalibration",
    "AdvioCatalog",
    "AdvioDatasetService",
    "AdvioDatasetSummary",
    "AdvioDownloadPreset",
    "AdvioDownloadRequest",
    "AdvioDownloadResult",
    "AdvioEnvironment",
    "AdvioLocalSceneStatus",
    "AdvioModality",
    "AdvioOfflineSample",
    "AdvioPeopleLevel",
    "AdvioPoseSource",
    "AdvioSceneMetadata",
    "AdvioSequence",
    "AdvioSequenceConfig",
    "AdvioSequencePaths",
    "AdvioUpstreamMetadata",
    "DatasetId",
    "TimedPoseTrajectory",
    "load_advio_catalog",
    "list_advio_sequence_ids",
    "load_advio_calibration",
    "load_advio_frame_timestamps_ns",
    "load_advio_sequence",
    "load_advio_trajectory",
    "write_advio_pose_tum",
]


def __getattr__(name: str) -> object:
    """Lazily load heavy dataset adapters to avoid package import cycles."""
    if name in {"DatasetId", "TimedPoseTrajectory"}:
        return globals()[name]
    if name in _ADVIO_EXPORTS:
        from . import advio

        return getattr(advio, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
