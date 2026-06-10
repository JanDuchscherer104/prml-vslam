"""Tidy dataframe and persisted report helpers for experiments."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from prml_vslam.experiments.contracts import (
    ExperimentArtifactRecord,
    ExperimentMetricRecord,
    ExperimentReport,
    ExperimentRunSpec,
)
from prml_vslam.utils import BaseConfig, RunArtifactPaths

_TRAJECTORY_STAT_UNITS = {
    "rmse": "m",
    "mean": "m",
    "median": "m",
    "std": "m",
    "min": "m",
    "max": "m",
    "sse": "m2",
}


def collect_metric_records(spec: ExperimentRunSpec) -> list[ExperimentMetricRecord]:
    """Collect existing persisted trajectory/cloud metrics into tidy rows."""
    paths = RunArtifactPaths.build(spec.artifact_root)
    records: list[ExperimentMetricRecord] = []
    records.extend(_trajectory_metric_records(spec, paths.trajectory_metrics_path))
    records.extend(
        _trajectory_alignment_records(spec, paths.artifact_root / "evaluation" / "trajectory_alignment.json")
    )
    records.extend(_cloud_alignment_records(spec, paths.artifact_root / "evaluation" / "cloud_alignment.json"))
    return records


def collect_artifact_records(spec: ExperimentRunSpec) -> list[ExperimentArtifactRecord]:
    """Collect existing stage manifest outputs into tidy artifact rows."""
    manifest_path = RunArtifactPaths.build(spec.artifact_root).stage_manifests_path
    if not manifest_path.is_file():
        return []
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[ExperimentArtifactRecord] = []
    for manifest in payload:
        output_paths = manifest.get("output_paths", {})
        for artifact_key, artifact_path in output_paths.items():
            records.append(
                ExperimentArtifactRecord(
                    experiment_id=spec.experiment_id,
                    run_id=spec.run_id,
                    item_id=spec.item_id,
                    dataset_id=spec.dataset_id,
                    sequence_id=spec.sequence_id,
                    method_id=spec.method_id,
                    stage=str(manifest.get("stage_id", "")),
                    artifact_key=str(artifact_key),
                    artifact_path=Path(str(artifact_path)),
                    status=str(manifest.get("status", "")),
                )
            )
    return records


def collect_run_dataframes(report: ExperimentReport) -> dict[str, pd.DataFrame]:
    """Return tidy pandas tables for metrics, validation checks, and artifacts."""
    metric_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    artifact_rows: list[dict[str, Any]] = []
    for result in report.results:
        metric_rows.extend(record.model_dump(mode="json") for record in result.metrics)
        validation_rows.extend(record.model_dump(mode="json") for record in result.validations)
        artifact_rows.extend(record.model_dump(mode="json") for record in result.artifacts)
    return {
        "metrics": pd.DataFrame(metric_rows),
        "validation": pd.DataFrame(validation_rows),
        "artifacts": pd.DataFrame(artifact_rows),
    }


def write_experiment_report(report: ExperimentReport, *, output_dir: Path) -> ExperimentReport:
    """Persist a report JSON file plus long-form CSV/Parquet tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    completed = report.completed_at if report.completed_at is not None else datetime.now().astimezone()
    updated = report.model_copy(update={"completed_at": completed})
    report_json_path = output_dir / "experiment_report.json"
    dataframes = collect_run_dataframes(updated)
    path_updates: dict[str, Path] = {"report_json_path": report_json_path}
    for name, dataframe in dataframes.items():
        csv_path = output_dir / f"{name}_long.csv"
        parquet_path = output_dir / f"{name}_long.parquet"
        dataframe.to_csv(csv_path, index=False)
        dataframe.to_parquet(parquet_path, index=False)
        path_updates[f"{name}_csv_path"] = csv_path
        path_updates[f"{name}_parquet_path"] = parquet_path
    updated = updated.model_copy(update=path_updates)
    report_json_path.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
    return updated


def _trajectory_metric_records(spec: ExperimentRunSpec, path: Path) -> list[ExperimentMetricRecord]:
    payload = _read_json_if_present(path)
    if payload is None:
        return []
    records: list[ExperimentMetricRecord] = []
    stats = payload.get("stats", {})
    if isinstance(stats, dict):
        records.extend(
            _metric(
                spec,
                stage="evaluate.trajectory",
                name=f"ape_translation_{name}",
                value=value,
                unit=_TRAJECTORY_STAT_UNITS.get(str(name)),
                path=path,
            )
            for name, value in stats.items()
        )
    if "matched_pairs" in payload:
        records.append(
            _metric(
                spec,
                stage="evaluate.trajectory",
                name="matched_pairs",
                value=payload["matched_pairs"],
                unit="pairs",
                path=path,
            )
        )
    return records


def _trajectory_alignment_records(spec: ExperimentRunSpec, path: Path) -> list[ExperimentMetricRecord]:
    payload = _read_json_if_present(path)
    if payload is None:
        return []
    records: list[ExperimentMetricRecord] = []
    for name, unit in (("rms_error_m", "m"), ("scale", None), ("matched_pairs", "pairs")):
        if name in payload:
            records.append(
                _metric(spec, stage="align.trajectory", name=name, value=payload[name], unit=unit, path=path)
            )
    return records


def _cloud_alignment_records(spec: ExperimentRunSpec, path: Path) -> list[ExperimentMetricRecord]:
    payload = _read_json_if_present(path)
    if payload is None:
        return []
    records: list[ExperimentMetricRecord] = []
    for name, unit in (("fitness", None), ("inlier_rmse_m", "m"), ("max_correspondence_distance_m", "m")):
        if name in payload:
            records.append(_metric(spec, stage="align.cloud", name=name, value=payload[name], unit=unit, path=path))
    return records


def _metric(
    spec: ExperimentRunSpec,
    *,
    stage: str,
    name: str,
    value: Any,
    unit: str | None,
    path: Path,
) -> ExperimentMetricRecord:
    return ExperimentMetricRecord(
        experiment_id=spec.experiment_id,
        run_id=spec.run_id,
        item_id=spec.item_id,
        dataset_id=spec.dataset_id,
        sequence_id=spec.sequence_id,
        method_id=spec.method_id,
        stage=stage,
        metric_name=name,
        metric_value=BaseConfig.to_jsonable(value),
        unit=unit,
        artifact_path=path,
    )


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.is_file() or path.stat().st_size == 0:
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload
