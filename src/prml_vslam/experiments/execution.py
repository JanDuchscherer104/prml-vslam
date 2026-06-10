"""Offline experiment expansion and sequential execution."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any, Protocol

from prml_vslam.experiments.config import ExperimentConfig, ExperimentItem, deep_merge_config_snapshot
from prml_vslam.experiments.contracts import ExperimentReport, ExperimentRunResult, ExperimentRunSpec
from prml_vslam.experiments.reporting import collect_artifact_records, collect_metric_records, write_experiment_report
from prml_vslam.experiments.validation import validate_run_artifacts
from prml_vslam.experiments.wandb_logging import log_run_to_wandb
from prml_vslam.pipeline.backend import PipelineRuntimeSource
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.demo import build_runtime_source_from_run_config
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.utils import BaseConfig, PathConfig


class ExperimentRunService(Protocol):
    """Subset of :class:`RunService` needed by experiment execution."""

    def start_run(self, *, run_config: RunConfig, runtime_source: PipelineRuntimeSource = None) -> None:
        """Start one pipeline run."""

    def snapshot(self) -> RunSnapshot:
        """Return the latest run snapshot."""

    def stop_run(self) -> None:
        """Stop the active run."""

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        """Release runtime resources."""


RunServiceFactory = Callable[[PathConfig], ExperimentRunService]


def expand_experiment_items(
    config: ExperimentConfig,
    *,
    path_config: PathConfig | None = None,
) -> list[ExperimentRunSpec]:
    """Expand experiment items into concrete offline run specs."""
    paths = PathConfig() if path_config is None else path_config
    return [_build_run_spec(config, item, _build_run_config_for_item(item), path_config=paths) for item in config.items]


def run_experiment(
    config: ExperimentConfig,
    *,
    path_config: PathConfig | None = None,
    run_service_factory: RunServiceFactory | None = None,
) -> ExperimentReport:
    """Execute an experiment sequentially through the existing pipeline service."""
    paths = PathConfig() if path_config is None else path_config
    service_factory = _default_run_service_factory if run_service_factory is None else run_service_factory
    report_dir = paths.resolve_output_dir(config.output_dir) / paths.slugify_experiment_name(config.name)
    report = ExperimentReport(experiment_id=config.name, started_at=datetime.now().astimezone())
    for item in config.items:
        run_config = _build_run_config_for_item(item)
        spec = _build_run_spec(config, item, run_config, path_config=paths)
        result = _run_one_item(
            spec=spec,
            item=item,
            run_config=run_config,
            path_config=paths,
            run_service_factory=service_factory,
        )
        report.results.append(result)
        report = write_experiment_report(report, output_dir=report_dir)
        log_run_to_wandb(config=config, result=result)
        if config.fail_fast and not result.success:
            break
    return write_experiment_report(report, output_dir=report_dir)


def _build_run_config_for_item(item: ExperimentItem) -> RunConfig:
    if item.run_config_path is not None:
        run_config = RunConfig.from_toml(item.run_config_path)
    elif item.run_config is not None:
        run_config = item.run_config
    else:
        raise ValueError("Experiment item has no run config source.")
    if item.overrides:
        snapshot = run_config.model_dump_jsonable()
        run_config = RunConfig.model_validate(deep_merge_config_snapshot(snapshot, item.overrides))
    if run_config.mode is not PipelineMode.OFFLINE:
        raise ValueError(f"Experiment item `{item.id}` must use offline mode, got `{run_config.mode.value}`.")
    return run_config


def _build_run_spec(
    config: ExperimentConfig,
    item: ExperimentItem,
    run_config: RunConfig,
    *,
    path_config: PathConfig,
) -> ExperimentRunSpec:
    plan = run_config.compile_plan(path_config)
    config_snapshot = run_config.model_dump_jsonable()
    return ExperimentRunSpec(
        experiment_id=config.name,
        item_id=item.id,
        run_id=plan.run_id,
        artifact_root=plan.artifact_root,
        config_hash=_stable_hash(config_snapshot),
        dataset_id=item.dataset_id or _dataset_id_from_plan(plan.source.metadata),
        sequence_id=item.sequence_id or plan.source.sequence_id,
        method_id=item.method_id or run_config.stages.slam.backend.method_id.value,
        preset_id=item.preset_id,
        run_config=config_snapshot,
    )


def _run_one_item(
    *,
    spec: ExperimentRunSpec,
    item: ExperimentItem,
    run_config: RunConfig,
    path_config: PathConfig,
    run_service_factory: RunServiceFactory,
) -> ExperimentRunResult:
    service = run_service_factory(path_config)
    snapshot = RunSnapshot(state=RunState.IDLE)
    try:
        runtime_source = build_runtime_source_from_run_config(run_config=run_config, path_config=path_config)
        service.start_run(run_config=run_config, runtime_source=runtime_source)
        snapshot = _wait_for_terminal_snapshot(service)
    except Exception as exc:
        snapshot = RunSnapshot(run_id=spec.run_id, state=RunState.FAILED, error_message=str(exc))
    finally:
        service.shutdown(
            preserve_local_head=snapshot.state is RunState.COMPLETED
            and run_config.ray_local_head_lifecycle == "reusable"
        )
    validations = validate_run_artifacts(
        spec=spec,
        run_config=run_config,
        snapshot=snapshot,
        allow_failure=item.allow_failure,
    )
    metrics = collect_metric_records(spec)
    artifacts = collect_artifact_records(spec)
    success = all(validation.passed for validation in validations) or (
        item.allow_failure and snapshot.state is not RunState.IDLE
    )
    return ExperimentRunResult(
        spec=spec,
        terminal_state=snapshot.state.value,
        success=success,
        error_message=snapshot.error_message,
        validations=validations,
        metrics=metrics,
        artifacts=artifacts,
    )


def _wait_for_terminal_snapshot(
    service: ExperimentRunService,
    *,
    poll_interval_seconds: float = 0.2,
) -> RunSnapshot:
    while True:
        snapshot = service.snapshot()
        if snapshot.state in {RunState.COMPLETED, RunState.FAILED, RunState.STOPPED}:
            return snapshot
        time.sleep(poll_interval_seconds)


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(BaseConfig.to_jsonable(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _dataset_id_from_plan(metadata: dict[str, str | int | float | bool | None]) -> str | None:
    value = metadata.get("dataset_id")
    return None if value is None else str(value)


def _default_run_service_factory(path_config: PathConfig) -> RunService:
    return RunService(path_config=path_config)
