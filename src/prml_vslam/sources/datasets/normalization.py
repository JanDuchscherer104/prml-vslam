"""Dataset-owned helpers for normalized-store ingestion and lookup."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, TypeAdapter, model_validator

from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    SourceBackendConfig,
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
    normalized_store_for_path_config,
)
from prml_vslam.sources.datasets.record3d import Record3DDatasetService
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDatasetService, TumRgbdPoseSource
from prml_vslam.sources.replay import ObservationStream
from prml_vslam.utils import BaseConfig, JsonObject
from prml_vslam.utils.path_config import PathConfig


class NormalizedDatasetBuildConfig(BaseConfig):
    """TOML-owned source list for generating normalized datastore entries."""

    workers: int | None = Field(default=None, ge=1)
    sources: list[
        Annotated[
            AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
            Field(discriminator="source_id"),
        ]
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset_sources(self) -> NormalizedDatasetBuildConfig:
        for source in self.sources:
            dataset_id_for_source_config(source)
        return self


def parse_dataset_id(value: str) -> DatasetId:
    """Parse CLI-facing dataset aliases into canonical dataset ids."""
    normalized = value.strip().lower().replace("-", "_")
    try:
        return DatasetId(normalized)
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


def dataset_id_for_source_config(
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
) -> DatasetId:
    """Return the normalized datastore dataset id owned by one source config."""
    match source_config:
        case AdvioSourceConfig():
            return DatasetId.ADVIO
        case TumRgbdSourceConfig():
            return DatasetId.TUM_RGBD
        case Record3DDatasetSourceConfig():
            return DatasetId.RECORD3D


def normalized_store_for_service(
    dataset_id: DatasetId,
    path_config: PathConfig,
) -> NormalizedDatasetStore:
    """Build the normalized store for one dataset under the shared datastore root."""
    return normalized_store_for_path_config(dataset_id, path_config)


def source_config_for_normalization(
    *,
    dataset_id: DatasetId,
    sequence_id: SequenceKey,
    reference_cloud: ReferenceCloudConfig | None = None,
    frame_selection: FrameSelectionConfig | None = None,
) -> AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig:
    """Build the source config whose byte-affecting fields define one store profile."""
    match dataset_id:
        case DatasetId.ADVIO:
            selection = frame_selection or default_frame_selection_for_dataset(dataset_id)
            return AdvioSourceConfig(
                sequence_id=f"advio-{int(sequence_id):02d}" if isinstance(sequence_id, int) else sequence_id,
                frame_stride=selection.frame_stride,
                target_fps=selection.target_fps,
            )
        case DatasetId.TUM_RGBD:
            selection = frame_selection or default_frame_selection_for_dataset(dataset_id)
            return TumRgbdSourceConfig(
                sequence_id=str(sequence_id),
                reference_cloud=reference_cloud or ReferenceCloudConfig(),
                frame_stride=selection.frame_stride,
                target_fps=selection.target_fps,
            )
        case DatasetId.RECORD3D:
            selection = frame_selection or default_frame_selection_for_dataset(dataset_id)
            return Record3DDatasetSourceConfig(
                sequence_id=str(sequence_id),
                reference_cloud=reference_cloud or ReferenceCloudConfig(min_confidence=1),
                frame_stride=selection.frame_stride,
                target_fps=selection.target_fps,
            )


def default_frame_selection_for_dataset(dataset_id: DatasetId) -> FrameSelectionConfig:
    """Return normalize-time sampling defaults for newly persisted entries."""
    return FrameSelectionConfig(target_fps=10.0 if dataset_id is DatasetId.ADVIO else 15.0)


def normalized_profile_for_dataset(
    *,
    dataset_id: DatasetId,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
    include_frame_selection: bool = False,
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
        include_frame_selection=include_frame_selection,
    )


def normalize_dataset_entry(
    *,
    dataset_id: DatasetId,
    path_config: PathConfig,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
) -> NormalizedDatasetEntry:
    """Create or replace one normalized entry from raw local dataset data."""
    profile = normalized_profile_for_dataset(
        dataset_id=dataset_id,
        service=service,
        source_config=source_config,
        include_frame_selection=True,
    )
    store = normalized_store_for_service(dataset_id, path_config)
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
    frame_selection: FrameSelectionConfig | None = None,
    workers: int = 1,
) -> list[NormalizedDatasetEntry]:
    """Create normalized entries for multiple local dataset sequences."""
    if workers < 1:
        raise ValueError("workers must be >= 1.")
    selection = frame_selection or default_frame_selection_for_dataset(dataset_id)
    if len(sequence_ids) <= 1 or workers == 1:
        service = dataset_service(dataset_id, path_config)
        return [
            normalize_dataset_entry(
                dataset_id=dataset_id,
                path_config=path_config,
                service=service,
                source_config=source_config_for_normalization(
                    dataset_id=dataset_id,
                    sequence_id=sequence_id,
                    reference_cloud=reference_cloud,
                    frame_selection=selection,
                ),
            )
            for sequence_id in sequence_ids
        ]
    path_config_payload = path_config.model_dump(mode="json")
    reference_cloud_payload = None if reference_cloud is None else reference_cloud.model_dump(mode="json")
    frame_selection_payload = selection.model_dump(mode="json")
    tasks = [
        (path_config_payload, dataset_id.value, sequence_id, reference_cloud_payload, frame_selection_payload)
        for sequence_id in sequence_ids
    ]
    with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as executor:
        return list(executor.map(_normalize_dataset_entry_worker, tasks))


def normalize_dataset_source_configs(
    *,
    path_config: PathConfig,
    source_configs: list[AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig],
    workers: int = 1,
) -> list[NormalizedDatasetEntry]:
    """Create normalized entries from a typed source-config list."""
    if workers < 1:
        raise ValueError("workers must be >= 1.")
    if len(source_configs) <= 1 or workers == 1:
        return [
            normalize_dataset_entry(
                dataset_id=dataset_id_for_source_config(source_config),
                path_config=path_config,
                service=dataset_service(dataset_id_for_source_config(source_config), path_config),
                source_config=source_config,
            )
            for source_config in source_configs
        ]
    path_config_payload = path_config.model_dump(mode="json")
    tasks = [(path_config_payload, source_config.model_dump(mode="json")) for source_config in source_configs]
    with ProcessPoolExecutor(max_workers=min(workers, len(tasks))) as executor:
        return list(executor.map(_normalize_dataset_source_config_worker, tasks))


def _normalize_dataset_entry_worker(
    task: tuple[JsonObject, str, SequenceKey, JsonObject | None, JsonObject],
) -> NormalizedDatasetEntry:
    path_config_payload, dataset_id_value, sequence_id, reference_cloud_payload, frame_selection_payload = task
    dataset_id = DatasetId(dataset_id_value)
    path_config = PathConfig.model_validate(path_config_payload)
    service = dataset_service(dataset_id, path_config)
    return normalize_dataset_entry(
        dataset_id=dataset_id,
        path_config=path_config,
        service=service,
        source_config=source_config_for_normalization(
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            reference_cloud=None
            if reference_cloud_payload is None
            else ReferenceCloudConfig.model_validate(reference_cloud_payload),
            frame_selection=FrameSelectionConfig.model_validate(frame_selection_payload),
        ),
    )


def _normalize_dataset_source_config_worker(
    task: tuple[JsonObject, JsonObject],
) -> NormalizedDatasetEntry:
    path_config_payload, source_config_payload = task
    path_config = PathConfig.model_validate(path_config_payload)
    source_config = _dataset_source_config_from_payload(source_config_payload)
    dataset_id = dataset_id_for_source_config(source_config)
    return normalize_dataset_entry(
        dataset_id=dataset_id,
        path_config=path_config,
        service=dataset_service(dataset_id, path_config),
        source_config=source_config,
    )


def _dataset_source_config_from_payload(
    payload: JsonObject,
) -> AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig:
    source_config: Any = TypeAdapter(SourceBackendConfig).validate_python(payload)
    if isinstance(source_config, AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig):
        return source_config
    raise ValueError(
        "Expected a dataset source config with source_id advio, tum_rgbd, or record3d_dataset; "
        f"got {source_config.source_id!r}."
    )


def open_normalized_dataset_stream(
    *,
    dataset_id: DatasetId,
    service: AdvioDatasetService | TumRgbdDatasetService | Record3DDatasetService,
    source_config: AdvioSourceConfig | TumRgbdSourceConfig | Record3DDatasetSourceConfig,
    include_depth: bool,
    path_config: PathConfig,
    output_dir: Path | None = None,
) -> ObservationStream:
    """Open a replay stream from one normalized dataset entry."""
    profile = normalized_profile_for_dataset(
        dataset_id=dataset_id,
        service=service,
        source_config=source_config,
    )
    store = normalized_store_for_service(dataset_id, path_config)
    frame_selection = FrameSelectionConfig(frame_stride=source_config.frame_stride, target_fps=source_config.target_fps)
    entry = store.resolve_entry(profile, frame_selection=frame_selection)
    return store.open_stream(
        entry,
        frame_selection=frame_selection,
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
            return service._build_raw_streaming_source(
                sequence_id=service.resolve_sequence_id(canonical_sequence_id),
                frame_selection=FrameSelectionConfig(
                    frame_stride=source_config.frame_stride,
                    target_fps=source_config.target_fps,
                ),
                rgb_max_width_px=source_config.rgb_max_width_px,
                rgb_dimension_multiple=source_config.rgb_dimension_multiple,
                dataset_serving=source_config.dataset_serving,
                replay_mode=source_config.replay_mode,
                normalize_video_orientation=source_config.normalize_video_orientation,
            )
        case DatasetId.TUM_RGBD:
            if not isinstance(service, TumRgbdDatasetService) or not isinstance(source_config, TumRgbdSourceConfig):
                raise TypeError("TUM RGB-D normalization received mismatched service/config.")
            return service._build_raw_streaming_source(
                sequence_id=canonical_sequence_id,
                frame_selection=FrameSelectionConfig(
                    frame_stride=source_config.frame_stride,
                    target_fps=source_config.target_fps,
                ),
                replay_mode=source_config.replay_mode,
                pose_source=TumRgbdPoseSource.GROUND_TRUTH,
                include_depth=True,
                reference_cloud=source_config.reference_cloud,
                rgb_max_width_px=source_config.rgb_max_width_px,
                rgb_dimension_multiple=source_config.rgb_dimension_multiple,
            )
        case DatasetId.RECORD3D:
            if not isinstance(service, Record3DDatasetService) or not isinstance(
                source_config, Record3DDatasetSourceConfig
            ):
                raise TypeError("Record3D normalization received mismatched service/config.")
            return service._build_raw_streaming_source(
                sequence_id=canonical_sequence_id,
                frame_selection=FrameSelectionConfig(
                    frame_stride=source_config.frame_stride,
                    target_fps=source_config.target_fps,
                ),
                replay_mode=source_config.replay_mode,
                materialization=source_config.materialization,
                reference_cloud=source_config.reference_cloud,
                rgb_max_width_px=source_config.rgb_max_width_px,
                rgb_dimension_multiple=source_config.rgb_dimension_multiple,
            )
