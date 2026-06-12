"""Dataset-owned helpers for normalized-store ingestion and lookup."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    TumRgbdSourceConfig,
    normalized_profile_for_source_config,
)
from prml_vslam.sources.datasets.advio import AdvioDatasetService
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig, SequenceKey
from prml_vslam.sources.datasets.normalized_store import (
    NormalizableDatasetSource,
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
)
from prml_vslam.sources.datasets.record3d import Record3DDatasetService
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.replay import ObservationStream
from prml_vslam.utils import JsonObject
from prml_vslam.utils.path_config import PathConfig


def parse_dataset_id(value: str) -> DatasetId:
    """Parse CLI-facing dataset aliases into canonical dataset ids."""
    normalized = value.strip().lower().replace("-", "_")
    aliases = {"record3d": DatasetId.RECORD3D.value}
    try:
        return DatasetId(aliases.get(normalized, normalized))
    except ValueError as exc:
        raise ValueError("Expected one of: advio, tum_rgbd, record3d.") from exc


def dataset_service(
    dataset_id: DatasetId, path_config: PathConfig
) -> AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService:
    """Build the service that owns one dataset's local layout and raw loading."""
    match dataset_id:
        case DatasetId.ADVIO:
            return AdvioDatasetService(path_config)
        case DatasetId.TUM_RGBD:
            return TumRgbdDatasetService(path_config)
        case DatasetId.RECORD3D:
            return Record3DDatasetService(path_config)


def normalized_store_for_service(
    dataset_id: DatasetId, service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService
) -> NormalizedDatasetStore:
    """Build the normalized store colocated with a dataset service root."""
    return NormalizedDatasetStore(dataset_root=service.dataset_root, dataset_id=dataset_id)


def source_config_for_normalization(
    *,
    dataset_id: DatasetId,
    sequence_id: SequenceKey,
    reference_cloud: ReferenceCloudConfig | None = None,
) -> AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig:
    """Build the source config whose byte-affecting fields define one store profile."""
    match dataset_id:
        case DatasetId.ADVIO:
            return AdvioSourceConfig(
                sequence_id=f"advio-{int(sequence_id):02d}" if isinstance(sequence_id, int) else sequence_id
            )
        case DatasetId.TUM_RGBD:
            return TumRgbdSourceConfig(
                sequence_id=str(sequence_id), reference_cloud=reference_cloud or ReferenceCloudConfig()
            )
        case DatasetId.RECORD3D:
            return Record3DDatasetSourceConfig(
                sequence_id=str(sequence_id),
                reference_cloud=reference_cloud or ReferenceCloudConfig(min_confidence=1),
            )


def normalized_profile_for_dataset(
    *,
    dataset_id: DatasetId,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
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


def normalize_dataset_entry(
    *,
    dataset_id: DatasetId,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
) -> NormalizedDatasetEntry:
    """Create or replace one full-frame normalized entry from raw local dataset data."""
    profile = normalized_profile_for_dataset(dataset_id=dataset_id, service=service, source_config=source_config)
    store = normalized_store_for_service(dataset_id, service)
    return store.create_entry_from_source(
        profile=profile,
        source=raw_dataset_source(dataset_id=dataset_id, service=service, source_config=source_config),
    )


def normalize_dataset_entries(
    *,
    dataset_id: DatasetId,
    path_config: PathConfig,
    sequence_ids: list[SequenceKey],
    reference_cloud: ReferenceCloudConfig | None = None,
    workers: int = 1,
) -> list[NormalizedDatasetEntry]:
    """Create normalized entries for multiple local dataset sequences."""
    if workers < 1:
        raise ValueError("workers must be >= 1.")
    if len(sequence_ids) <= 1 or workers == 1:
        service = dataset_service(dataset_id, path_config)
        return [
            normalize_dataset_entry(
                dataset_id=dataset_id,
                service=service,
                source_config=source_config_for_normalization(
                    dataset_id=dataset_id,
                    sequence_id=sequence_id,
                    reference_cloud=reference_cloud,
                ),
            )
            for sequence_id in sequence_ids
        ]
    path_config_payload = path_config.model_dump(mode="json")
    reference_cloud_payload = None if reference_cloud is None else reference_cloud.model_dump(mode="json")
    tasks = [
        (path_config_payload, dataset_id.value, sequence_id, reference_cloud_payload) for sequence_id in sequence_ids
    ]
    with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as executor:
        return list(executor.map(_normalize_dataset_entry_worker, tasks))


def _normalize_dataset_entry_worker(
    task: tuple[JsonObject, str, SequenceKey, JsonObject | None],
) -> NormalizedDatasetEntry:
    path_config_payload, dataset_id_value, sequence_id, reference_cloud_payload = task
    dataset_id = DatasetId(dataset_id_value)
    path_config = PathConfig.model_validate(path_config_payload)
    service = dataset_service(dataset_id, path_config)
    return normalize_dataset_entry(
        dataset_id=dataset_id,
        service=service,
        source_config=source_config_for_normalization(
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            reference_cloud=None
            if reference_cloud_payload is None
            else ReferenceCloudConfig.model_validate(reference_cloud_payload),
        ),
    )


def open_normalized_dataset_stream(
    *,
    dataset_id: DatasetId,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
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
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
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
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
) -> NormalizableDatasetSource:
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
