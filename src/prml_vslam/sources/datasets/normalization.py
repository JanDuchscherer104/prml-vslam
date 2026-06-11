"""Dataset-owned helpers for normalized-store ingestion and lookup."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    TumRgbdSourceConfig,
    normalized_profile_for_source_config,
)
from prml_vslam.sources.datasets.advio import AdvioDatasetService
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
)
from prml_vslam.sources.datasets.record3d import Record3DDatasetService
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.protocols import BenchmarkInputSource
from prml_vslam.sources.replay import ObservationStream
from prml_vslam.utils.path_config import PathConfig

DatasetService: TypeAlias = AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService
DatasetSourceConfig: TypeAlias = AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig


def parse_dataset_id(value: str) -> DatasetId:
    """Parse CLI-facing dataset aliases into canonical dataset ids."""
    normalized = value.strip().lower().replace("-", "_")
    aliases = {"record3d": DatasetId.RECORD3D.value}
    try:
        return DatasetId(aliases.get(normalized, normalized))
    except ValueError as exc:
        raise ValueError("Expected one of: advio, tum_rgbd, record3d.") from exc


def dataset_service(dataset_id: DatasetId, path_config: PathConfig) -> DatasetService:
    """Build the service that owns one dataset's local layout and raw loading."""
    match dataset_id:
        case DatasetId.ADVIO:
            return AdvioDatasetService(path_config)
        case DatasetId.TUM_RGBD:
            return TumRgbdDatasetService(path_config)
        case DatasetId.RECORD3D:
            return Record3DDatasetService(path_config)


def normalized_store_for_service(dataset_id: DatasetId, service: DatasetService) -> NormalizedDatasetStore:
    """Build the normalized store colocated with a dataset service root."""
    return NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=dataset_id)


def source_config_for_normalization(
    *,
    dataset_id: DatasetId,
    sequence_id: str,
    record3d_reference_cloud_pixel_stride: int = 8,
    record3d_reference_cloud_min_confidence: int | None = 1,
    record3d_reference_cloud_max_points: int = 100_000,
) -> DatasetSourceConfig:
    """Build the source config whose byte-affecting fields define one store profile."""
    match dataset_id:
        case DatasetId.ADVIO:
            return AdvioSourceConfig(sequence_id=sequence_id)
        case DatasetId.TUM_RGBD:
            return TumRgbdSourceConfig(sequence_id=sequence_id)
        case DatasetId.RECORD3D:
            return Record3DDatasetSourceConfig(
                sequence_id=sequence_id,
                reference_cloud=ReferenceCloudConfig(
                    depth_stride_px=record3d_reference_cloud_pixel_stride,
                    max_points=record3d_reference_cloud_max_points,
                    min_confidence=record3d_reference_cloud_min_confidence,
                ),
            )


def normalized_profile_for_dataset(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    source_config: DatasetSourceConfig,
) -> NormalizedDatasetProfile:
    """Return the normalized-store profile for a dataset source config."""
    canonical_sequence_id = canonical_sequence_id_for_dataset(
        dataset_id=dataset_id,
        service=service,
        sequence_id=source_config.sequence_id,
    )
    return normalized_profile_for_source_config(
        dataset_id=dataset_id,
        sequence_id=canonical_sequence_id,
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )


def normalized_entry_exists(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    source_config: DatasetSourceConfig,
) -> bool:
    """Return whether the normalized store contains the source config's profile."""
    profile = normalized_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source_config)
    return normalized_store_for_service(dataset_id, service).entry_exists(profile)


def normalize_dataset_entry(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    source_config: DatasetSourceConfig,
) -> NormalizedDatasetEntry:
    """Create or replace one full-frame normalized entry from raw local dataset data."""
    profile = normalized_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source_config)
    store = normalized_store_for_service(dataset_id, service)
    return store.create_entry_from_source(
        profile=profile,
        source=raw_dataset_source(dataset_id=dataset_id, service=service, source_config=source_config),
    )


def open_normalized_dataset_stream(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    source_config: DatasetSourceConfig,
    include_depth: bool,
    output_dir: Path | None = None,
) -> ObservationStream:
    """Open a replay stream from one normalized dataset entry."""
    profile = normalized_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source_config)
    store = normalized_store_for_service(dataset_id, service)
    entry = store.load_entry(profile)
    return store.open_stream(
        entry,
        frame_selection=FrameSelectionConfig(),
        output_dir=entry.root / "preview" if output_dir is None else output_dir,
        loop=True,
        replay_mode=source_config.replay_mode,
        include_depth=include_depth,
    )


def canonical_sequence_id_for_dataset(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    sequence_id: str,
) -> str:
    """Resolve a dataset sequence id into the normalized-store canonical id."""
    resolved = service.resolve_sequence_id(sequence_id)
    if dataset_id is DatasetId.ADVIO:
        return f"advio-{int(resolved):02d}"
    return str(resolved)


def raw_dataset_source(
    *,
    dataset_id: DatasetId,
    service: DatasetService,
    source_config: DatasetSourceConfig,
) -> BenchmarkInputSource:
    """Build the raw local source used only to ingest a normalized entry."""
    canonical_sequence_id = canonical_sequence_id_for_dataset(
        dataset_id=dataset_id,
        service=service,
        sequence_id=source_config.sequence_id,
    )
    match dataset_id:
        case DatasetId.ADVIO:
            if not isinstance(service, AdvioDatasetService) or not isinstance(source_config, AdvioSourceConfig):
                raise TypeError("ADVIO normalization received mismatched service/config.")
            return service.build_streaming_source(
                sequence_id=service.resolve_sequence_id(canonical_sequence_id),
                frame_selection=FrameSelectionConfig(),
                dataset_serving=source_config.dataset_serving,
                replay_mode=source_config.replay_mode,
                normalize_video_orientation=source_config.normalize_video_orientation,
            )
        case DatasetId.TUM_RGBD:
            if not isinstance(service, TumRgbdDatasetService) or not isinstance(source_config, TumRgbdSourceConfig):
                raise TypeError("TUM RGB-D normalization received mismatched service/config.")
            return service.build_streaming_source(
                sequence_id=canonical_sequence_id,
                frame_selection=FrameSelectionConfig(),
                replay_mode=source_config.replay_mode,
                pose_source=TumRgbdPoseSource.GROUND_TRUTH,
                include_depth=True,
                reference_cloud=source_config.reference_cloud,
            )
        case DatasetId.RECORD3D:
            if not isinstance(service, Record3DDatasetService) or not isinstance(
                source_config, Record3DDatasetSourceConfig
            ):
                raise TypeError("Record3D normalization received mismatched service/config.")
            return service.build_streaming_source(
                sequence_id=canonical_sequence_id,
                frame_selection=FrameSelectionConfig(),
                replay_mode=source_config.replay_mode,
                materialization=source_config.materialization,
                reference_cloud=source_config.reference_cloud,
            )
