"""Persisted contracts for offline benchmark experiments."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import Field

from prml_vslam.utils import BaseData


class ExperimentRunSpec(BaseData):
    """Resolved plan metadata for one experiment item."""

    experiment_id: str
    item_id: str
    run_id: str
    artifact_root: Path
    config_hash: str
    dataset_id: str | None = None
    sequence_id: str | None = None
    method_id: str | None = None
    preset_id: str | None = None
    run_config: dict[str, Any]


class ExperimentValidationResult(BaseData):
    """One deterministic validation check result for a concrete run."""

    experiment_id: str
    run_id: str
    item_id: str
    check_name: str
    passed: bool
    status: str
    message: str = ""
    artifact_path: Path | None = None


class ExperimentMetricRecord(BaseData):
    """One tidy metric observation collected from persisted run artifacts."""

    experiment_id: str
    run_id: str
    item_id: str
    dataset_id: str | None = None
    sequence_id: str | None = None
    method_id: str | None = None
    stage: str
    metric_name: str
    metric_value: float | int | str | bool | None
    unit: str | None = None
    artifact_path: Path | None = None
    status: str = "available"


class ExperimentArtifactRecord(BaseData):
    """One tidy artifact observation collected from persisted manifests."""

    experiment_id: str
    run_id: str
    item_id: str
    dataset_id: str | None = None
    sequence_id: str | None = None
    method_id: str | None = None
    stage: str
    artifact_key: str
    artifact_path: Path
    status: str


class ExperimentRunResult(BaseData):
    """Terminal result for one concrete experiment item."""

    spec: ExperimentRunSpec
    terminal_state: str
    success: bool
    error_message: str = ""
    validations: list[ExperimentValidationResult] = Field(default_factory=list)
    metrics: list[ExperimentMetricRecord] = Field(default_factory=list)
    artifacts: list[ExperimentArtifactRecord] = Field(default_factory=list)


class ExperimentReport(BaseData):
    """Machine-readable report for one offline experiment execution."""

    experiment_id: str
    started_at: datetime
    completed_at: datetime | None = None
    results: list[ExperimentRunResult] = Field(default_factory=list)
    report_json_path: Path | None = None
    metrics_csv_path: Path | None = None
    metrics_parquet_path: Path | None = None
    validation_csv_path: Path | None = None
    validation_parquet_path: Path | None = None
    artifacts_csv_path: Path | None = None
    artifacts_parquet_path: Path | None = None

    @property
    def success(self) -> bool:
        """Return true when every run succeeded or was explicitly allowed to fail."""
        return all(result.success for result in self.results)
