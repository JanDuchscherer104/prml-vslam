"""Read-only query surface for canonical normalized dataset-store entries."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from prml_vslam.sources.datasets.contracts import DatasetId
from prml_vslam.sources.datasets.normalization import dataset_service, normalized_store_for_service
from prml_vslam.sources.datasets.normalized_store import NormalizedDatasetEntry, NormalizedDatasetStoreIssue
from prml_vslam.sources.datasets.normalized_tables import read_long_csv
from prml_vslam.utils import JsonObject, PathConfig, get_path_config


class NormalizedDatasetQuery:
    """Discover normalized entries and load source-owned long rows."""

    def __init__(self, *, path_config: PathConfig | None = None) -> None:
        self._path_config = get_path_config() if path_config is None else path_config

    @classmethod
    def from_path_config(cls, path_config: PathConfig | None = None) -> NormalizedDatasetQuery:
        """Build a query rooted at the configured repo data directory."""
        return cls(path_config=path_config)

    def records(self, dataset_ids: Iterable[DatasetId] | None = None) -> list[NormalizedDatasetEntry]:
        """Return discovered normalized entries for selected dataset stores."""
        selected = tuple(dataset_ids) if dataset_ids is not None else tuple(DatasetId)
        entries: list[NormalizedDatasetEntry] = []
        for dataset_id in selected:
            service = dataset_service(dataset_id, self._path_config)
            entries.extend(normalized_store_for_service(dataset_id, service).summary(strict=False))
        return sorted(entries, key=lambda entry: (entry.dataset_id.value, entry.sequence_id, entry.profile_key))

    def issues(self, dataset_ids: Iterable[DatasetId] | None = None) -> list[NormalizedDatasetStoreIssue]:
        """Return normalized-store entries that need rebuild or operator attention."""
        selected = tuple(dataset_ids) if dataset_ids is not None else tuple(DatasetId)
        issues: list[NormalizedDatasetStoreIssue] = []
        for dataset_id in selected:
            service = dataset_service(dataset_id, self._path_config)
            issues.extend(normalized_store_for_service(dataset_id, service).issues())
        return sorted(issues, key=lambda issue: (issue.dataset_id.value, issue.sequence_id, issue.profile_key))

    def issue_rows(
        self,
        dataset_ids: Iterable[DatasetId] | None = None,
        *,
        issues: list[NormalizedDatasetStoreIssue] | None = None,
    ) -> list[JsonObject]:
        """Return normalized-store issues as JSON-compatible rows."""
        selected = self.issues(dataset_ids) if issues is None else issues
        return [issue.model_dump(mode="json") for issue in selected]

    def record_rows(
        self,
        dataset_ids: Iterable[DatasetId] | None = None,
        *,
        records: list[NormalizedDatasetEntry] | None = None,
    ) -> list[JsonObject]:
        """Return normalized entries as JSON-compatible rows."""
        entries = self.records(dataset_ids) if records is None else records
        return [entry.model_dump(mode="json") for entry in entries]

    def stats_long_rows(
        self,
        dataset_ids: Iterable[DatasetId] | None = None,
        *,
        records: list[NormalizedDatasetEntry] | None = None,
    ) -> list[JsonObject]:
        """Return persisted Core + Motion statistics as tidy long rows."""
        entries = self.records(dataset_ids) if records is None else records
        return _concat_csv_rows((entry.stats_long_csv_path for entry in entries), label="stats_long_csv_path")

    def metadata_long_rows(
        self,
        dataset_ids: Iterable[DatasetId] | None = None,
        *,
        records: list[NormalizedDatasetEntry] | None = None,
    ) -> list[JsonObject]:
        """Return persisted metadata as tidy long rows."""
        entries = self.records(dataset_ids) if records is None else records
        return _concat_csv_rows((entry.metadata_long_csv_path for entry in entries), label="metadata_long_csv_path")


def _concat_csv_rows(paths: Iterable[Path | None], *, label: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for path in paths:
        if path is None:
            continue
        if not path.exists():
            raise FileNotFoundError(f"Normalized entry advertises missing {label}: {path}")
        rows.extend(read_long_csv(path))
    return rows


def load_normalized_dataset_query(path_config: PathConfig | None = None) -> NormalizedDatasetQuery:
    """Return the default normalized dataset query interface."""
    return NormalizedDatasetQuery(path_config=path_config)


__all__ = ["NormalizedDatasetQuery", "load_normalized_dataset_query"]
