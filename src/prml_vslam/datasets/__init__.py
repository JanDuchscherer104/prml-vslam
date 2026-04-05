"""Dataset adapters for benchmark inputs and replay sources."""

from __future__ import annotations

from importlib import import_module

_LAYOUT_EXPORTS = "load_advio_catalog".split()
_LOADING_EXPORTS = """
AdvioCalibration load_advio_calibration load_advio_frame_timestamps_ns load_advio_trajectory write_advio_pose_tum
""".split()
_MODEL_EXPORTS = """
ADVIO_SEQUENCE_COUNT AdvioCatalog AdvioDatasetSummary AdvioDownloadPreset AdvioDownloadRequest
AdvioDownloadResult AdvioEnvironment AdvioLocalSceneStatus AdvioModality AdvioPeopleLevel
AdvioPoseSource AdvioSceneMetadata AdvioUpstreamMetadata
""".split()
_SEQUENCE_EXPORTS = """
AdvioOfflineSample AdvioSequence AdvioSequenceConfig AdvioSequencePaths list_advio_sequence_ids load_advio_sequence
""".split()
_SERVICE_EXPORTS = "AdvioDatasetService".split()
_EXPORT_MODULES = (
    {name: "advio_layout" for name in _LAYOUT_EXPORTS}
    | {name: "advio_loading" for name in _LOADING_EXPORTS}
    | {name: "advio_models" for name in _MODEL_EXPORTS}
    | {name: "advio_sequence" for name in _SEQUENCE_EXPORTS}
    | {name: "advio_service" for name in _SERVICE_EXPORTS}
)

__all__ = [*_LAYOUT_EXPORTS, *_LOADING_EXPORTS, *_MODEL_EXPORTS, *_SEQUENCE_EXPORTS, *_SERVICE_EXPORTS]


def __getattr__(name: str) -> object:
    """Load exported dataset symbols lazily to avoid import cycles."""
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(import_module(f".{module_name}", __name__), name)
