"""Batch construction of canonical normalized dataset-store entries."""

from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from enum import StrEnum
from pathlib import Path
from typing import TypeAlias, cast

from pydantic import Field, field_validator, model_validator

from prml_vslam.sources.datasets.advio import AdvioLocalSceneStatus
from prml_vslam.sources.datasets.contracts import DatasetId, ReferenceCloudConfig, SequenceKey
from prml_vslam.sources.datasets.normalization import (
    DatasetService,
    dataset_service,
    normalize_dataset_entry,
    normalized_profile_for_dataset,
    normalized_store_for_service,
    parse_dataset_id,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetEntry, NormalizedDatasetProfile
from prml_vslam.sources.datasets.record3d import Record3DLocalSceneStatus
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdLocalSceneStatus
from prml_vslam.utils import BaseConfig, BaseData, PathConfig, get_path_config

SequenceSelection: TypeAlias = str | int
BatchLocalSceneStatus: TypeAlias = AdvioLocalSceneStatus | TumRgbdLocalSceneStatus | Record3DLocalSceneStatus
ProgressCallback: TypeAlias = Callable[["NormalizedDatasetBatchProgress"], None]


class NormalizedDatasetMissingPolicy(StrEnum):
    """Policy for configured scenes that are not offline-ready locally."""

    FAIL = "fail"
    SKIP = "skip"


class NormalizedDatasetSelection(BaseConfig):
    """Select one dataset slice for normalized-store construction."""

    dataset_id: DatasetId
    """Dataset whose offline-ready scenes should be normalized."""

    sequence_ids: list[str] = Field(default_factory=list)
    """Dataset-specific ids or slugs; empty means every locally offline-ready scene."""

    reference_cloud: ReferenceCloudConfig | None = None
    """Optional source-prepared reference-cloud settings included in the profile key."""

    @field_validator("dataset_id", mode="before")
    @classmethod
    def normalize_dataset_id(cls, value: str | DatasetId) -> DatasetId:
        """Accept user-facing TOML aliases such as ``record3d``."""
        return parse_dataset_id(value) if isinstance(value, str) else value

    @field_validator("sequence_ids", mode="before")
    @classmethod
    def normalize_sequence_ids(cls, value: list[SequenceSelection] | SequenceSelection | None) -> list[str]:
        """Normalize scalar/list TOML selections to unique strings."""
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        return list(dict.fromkeys(str(item) for item in values))


class NormalizedDatasetBatchConfig(BaseConfig):
    """Configure a batch build of canonical normalized dataset-store entries."""

    datasets: list[NormalizedDatasetSelection] = Field(default_factory=list)
    """Datasets to build; empty means ADVIO, TUM RGB-D, and Record3D catalogs."""

    max_workers: int = Field(default_factory=lambda: max(1, os.cpu_count() or 1), ge=1)
    """Number of worker processes used to normalize independent sequences."""

    missing_policy: NormalizedDatasetMissingPolicy = NormalizedDatasetMissingPolicy.FAIL
    """Whether unavailable selected scenes fail the batch or are reported as skipped."""

    overwrite: bool = False
    """Whether existing entries should be rebuilt instead of reused."""

    @model_validator(mode="after")
    def default_registered_datasets(self) -> NormalizedDatasetBatchConfig:
        """Default to all registered dataset families."""
        if not self.datasets:
            self.datasets = [
                NormalizedDatasetSelection(dataset_id=DatasetId.ADVIO),
                NormalizedDatasetSelection(dataset_id=DatasetId.TUM_RGBD),
                NormalizedDatasetSelection(dataset_id=DatasetId.RECORD3D),
            ]
        return self


class NormalizedDatasetBatchRecord(BaseData):
    """Result for one requested normalized-store entry."""

    dataset_id: DatasetId
    sequence_id: str
    profile_key: str | None = None
    entry_root: Path | None = None
    status: str
    message: str = ""


class NormalizedDatasetBatchProgress(BaseData):
    """Progress event emitted by batch normalized-store construction."""

    stage: str
    dataset_id: DatasetId | None = None
    sequence_id: str | None = None
    status: str | None = None
    completed: int = 0
    total: int = 0
    message: str = ""


class NormalizedDatasetBatchResult(BaseData):
    """Summary returned by batch normalized-store construction."""

    records: list[NormalizedDatasetBatchRecord] = Field(default_factory=list)
    skipped: list[NormalizedDatasetBatchRecord] = Field(default_factory=list)
    failed: list[NormalizedDatasetBatchRecord] = Field(default_factory=list)

    @property
    def built_count(self) -> int:
        """Return the number of successfully built or reused entries."""
        return len(self.records)

    @property
    def skipped_count(self) -> int:
        """Return the number of skipped unavailable targets."""
        return len(self.skipped)

    @property
    def failed_count(self) -> int:
        """Return the number of failed targets."""
        return len(self.failed)


class _BatchTask(BaseData):
    path_config: PathConfig
    selection: NormalizedDatasetSelection
    sequence_id: str
    overwrite: bool = False


def normalize_dataset_batch(
    config: NormalizedDatasetBatchConfig,
    *,
    path_config: PathConfig | None = None,
    progress: ProgressCallback | None = None,
) -> NormalizedDatasetBatchResult:
    """Normalize every configured offline-ready dataset sequence."""
    resolved_path_config = get_path_config() if path_config is None else path_config
    tasks: list[_BatchTask] = []
    skipped: list[NormalizedDatasetBatchRecord] = []
    failed: list[NormalizedDatasetBatchRecord] = []
    for selection in config.datasets:
        _emit_progress(
            progress,
            stage="discovering",
            dataset_id=selection.dataset_id,
            message=f"Discovering local {selection.dataset_id.value} scenes.",
        )
        service = dataset_service(selection.dataset_id, resolved_path_config)
        statuses = service.local_scene_statuses()
        status_by_id = {alias: status for status in statuses for alias in _status_aliases(selection.dataset_id, status)}
        sequence_ids = selection.sequence_ids or [
            _normalization_sequence_id(selection.dataset_id, service, status.scene.sequence_id)
            for status in statuses
            if status.offline_ready
        ]
        _emit_progress(
            progress,
            stage="discovered",
            dataset_id=selection.dataset_id,
            total=len(sequence_ids),
            message=(
                f"Discovered {len(sequence_ids)} locally offline-ready {selection.dataset_id.value} "
                "scene(s) to normalize."
            ),
        )
        for requested_id in sequence_ids:
            canonical_id = _normalization_sequence_id(selection.dataset_id, service, requested_id)
            status = status_by_id.get(canonical_id) or status_by_id.get(str(requested_id))
            if status is None or not status.offline_ready:
                record = NormalizedDatasetBatchRecord(
                    dataset_id=selection.dataset_id,
                    sequence_id=canonical_id,
                    status="missing",
                    message=f"Dataset scene is not offline-ready locally: {selection.dataset_id.value}/{requested_id}",
                )
                if config.missing_policy is NormalizedDatasetMissingPolicy.SKIP:
                    skipped.append(record)
                    _emit_progress(
                        progress,
                        stage="skipped",
                        dataset_id=selection.dataset_id,
                        sequence_id=canonical_id,
                        status="missing",
                        message=record.message,
                    )
                else:
                    failed.append(record)
                    _emit_progress(
                        progress,
                        stage="failed",
                        dataset_id=selection.dataset_id,
                        sequence_id=canonical_id,
                        status="missing",
                        message=record.message,
                    )
                continue
            tasks.append(
                _BatchTask(
                    path_config=resolved_path_config,
                    selection=selection,
                    sequence_id=canonical_id,
                    overwrite=config.overwrite,
                )
            )
    records = _run_tasks(tasks, max_workers=config.max_workers, progress=progress)
    ok = [record for record in records if record.status in {"built", "reused"}]
    failed.extend(record for record in records if record.status == "failed")
    return NormalizedDatasetBatchResult(records=sorted(ok, key=_record_sort_key), skipped=skipped, failed=failed)


def _status_aliases(dataset_id: DatasetId, status: BatchLocalSceneStatus) -> set[str]:
    scene = status.scene
    aliases = {str(scene.sequence_id)}
    if dataset_id is DatasetId.ADVIO:
        aliases.add(cast(AdvioLocalSceneStatus, status).scene.sequence_slug)
    return aliases


def _normalization_sequence_id(dataset_id: DatasetId, service: DatasetService, sequence_id: SequenceKey) -> str:
    if dataset_id is DatasetId.ADVIO:
        resolved = int(sequence_id) if isinstance(sequence_id, str) and sequence_id.isdigit() else sequence_id
        resolved = service.resolve_sequence_id(str(resolved)) if not isinstance(resolved, int) else resolved
        return f"advio-{int(resolved):02d}"
    return str(service.resolve_sequence_id(str(sequence_id)))


def _run_tasks(
    tasks: list[_BatchTask], *, max_workers: int, progress: ProgressCallback | None
) -> list[NormalizedDatasetBatchRecord]:
    if not tasks:
        _emit_progress(progress, stage="done", completed=0, total=0, message="No offline-ready scenes to normalize.")
        return []
    worker_count = min(max_workers, len(tasks))
    _emit_progress(
        progress,
        stage="queued",
        completed=0,
        total=len(tasks),
        message=f"Queued {len(tasks)} normalized-store task(s) across {worker_count} worker process(es).",
    )
    if max_workers == 1:
        serial_records: list[NormalizedDatasetBatchRecord] = []
        for completed, task in enumerate(tasks, start=1):
            _emit_progress(
                progress,
                stage="processing",
                dataset_id=task.selection.dataset_id,
                sequence_id=task.sequence_id,
                completed=completed - 1,
                total=len(tasks),
                message=f"Processing {task.selection.dataset_id.value}/{task.sequence_id}.",
            )
            record = _normalize_batch_task(task)
            serial_records.append(record)
            _emit_progress_for_record(progress, record, completed=completed, total=len(tasks))
        return serial_records
    records: list[NormalizedDatasetBatchRecord] = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(_normalize_batch_task, task) for task in tasks]
        for task in tasks:
            _emit_progress(
                progress,
                stage="submitted",
                dataset_id=task.selection.dataset_id,
                sequence_id=task.sequence_id,
                completed=0,
                total=len(tasks),
                message=f"Submitted {task.selection.dataset_id.value}/{task.sequence_id}.",
            )
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            _emit_progress_for_record(progress, record, completed=len(records), total=len(tasks))
    return records


def _emit_progress_for_record(
    progress: ProgressCallback | None, record: NormalizedDatasetBatchRecord, *, completed: int, total: int
) -> None:
    _emit_progress(
        progress,
        stage="completed",
        dataset_id=record.dataset_id,
        sequence_id=record.sequence_id,
        status=record.status,
        completed=completed,
        total=total,
        message=f"{record.status}: {record.dataset_id.value}/{record.sequence_id}",
    )


def _emit_progress(
    progress: ProgressCallback | None,
    *,
    stage: str,
    dataset_id: DatasetId | None = None,
    sequence_id: str | None = None,
    status: str | None = None,
    completed: int = 0,
    total: int = 0,
    message: str = "",
) -> None:
    if progress is None:
        return
    progress(
        NormalizedDatasetBatchProgress(
            stage=stage,
            dataset_id=dataset_id,
            sequence_id=sequence_id,
            status=status,
            completed=completed,
            total=total,
            message=message,
        )
    )


def _normalize_batch_task(task: _BatchTask) -> NormalizedDatasetBatchRecord:
    profile: NormalizedDatasetProfile | None = None
    entry_root: Path | None = None
    try:
        service = dataset_service(task.selection.dataset_id, task.path_config)
        source_config = source_config_for_normalization(
            dataset_id=task.selection.dataset_id,
            sequence_id=task.sequence_id,
            reference_cloud=task.selection.reference_cloud,
        )
        profile = normalized_profile_for_dataset(
            dataset_id=task.selection.dataset_id, service=service, source_config=source_config
        )
        store = normalized_store_for_service(task.selection.dataset_id, service)
        entry_root = store.entry_root(profile)
        if not task.overwrite:
            try:
                return _record_from_entry(store.load_entry(profile), status="reused")
            except FileNotFoundError:
                pass
        entry = normalize_dataset_entry(
            dataset_id=task.selection.dataset_id, service=service, source_config=source_config
        )
        return _record_from_entry(entry, status="built")
    except Exception as exc:
        return NormalizedDatasetBatchRecord(
            dataset_id=task.selection.dataset_id,
            sequence_id=task.sequence_id,
            profile_key=None if profile is None else profile.profile_key,
            entry_root=entry_root,
            status="failed",
            message=_batch_failure_message(task=task, exc=exc, profile=profile, entry_root=entry_root),
        )


def _batch_failure_message(
    *,
    task: _BatchTask,
    exc: Exception,
    profile: NormalizedDatasetProfile | None,
    entry_root: Path | None,
) -> str:
    details = [
        f"{type(exc).__name__} while normalizing",
        f"dataset_id={task.selection.dataset_id.value}",
        f"sequence_id={task.sequence_id}",
    ]
    if profile is not None:
        details.append(f"profile_key={profile.profile_key}")
    if entry_root is not None:
        details.append(f"entry_root={entry_root}")
    message = str(exc)
    if message:
        details.append(message)
    return ": ".join(details)


def _record_from_entry(entry: NormalizedDatasetEntry, *, status: str) -> NormalizedDatasetBatchRecord:
    return NormalizedDatasetBatchRecord(
        dataset_id=entry.dataset_id,
        sequence_id=entry.sequence_id,
        profile_key=entry.profile_key,
        entry_root=entry.root,
        status=status,
    )


def _record_sort_key(record: NormalizedDatasetBatchRecord) -> tuple[str, str, str]:
    return (record.dataset_id.value, record.sequence_id, record.profile_key or "")


__all__ = [
    "NormalizedDatasetBatchConfig",
    "NormalizedDatasetBatchProgress",
    "NormalizedDatasetBatchRecord",
    "NormalizedDatasetBatchResult",
    "NormalizedDatasetMissingPolicy",
    "NormalizedDatasetSelection",
    "normalize_dataset_batch",
]
