"""Optional Weights & Biases logging for experiment runs."""

from __future__ import annotations

from types import ModuleType

from prml_vslam.experiments.config import ExperimentConfig
from prml_vslam.experiments.contracts import ExperimentRunResult


def log_run_to_wandb(
    *,
    config: ExperimentConfig,
    result: ExperimentRunResult,
    wandb_module: ModuleType | None = None,
) -> None:
    """Log one concrete run to W&B when enabled by config."""
    if not config.wandb.enabled:
        return
    wandb = _resolve_wandb_module(wandb_module)
    init_kwargs = {
        "project": config.wandb.project,
        "group": config.wandb.group or config.name,
        "name": result.spec.run_id,
        "job_type": "pipeline-run",
        "tags": config.wandb.tags,
        "config": {
            "experiment_id": result.spec.experiment_id,
            "item_id": result.spec.item_id,
            "run_id": result.spec.run_id,
            "artifact_root": result.spec.artifact_root.as_posix(),
            "config_hash": result.spec.config_hash,
            "dataset_id": result.spec.dataset_id,
            "sequence_id": result.spec.sequence_id,
            "method_id": result.spec.method_id,
            "preset_id": result.spec.preset_id,
            "run_config": result.spec.run_config,
        },
    }
    if config.wandb.entity is not None:
        init_kwargs["entity"] = config.wandb.entity
    if config.wandb.mode is not None:
        init_kwargs["mode"] = config.wandb.mode
    run = wandb.init(**init_kwargs)
    try:
        run.summary["terminal_state"] = result.terminal_state
        run.summary["success"] = result.success
        run.summary["validation_passed"] = sum(validation.passed for validation in result.validations)
        run.summary["validation_total"] = len(result.validations)
        metrics: dict[str, float | int | bool] = {}
        for record in result.metrics:
            if isinstance(record.metric_value, bool | int | float):
                metrics[f"{record.stage}/{record.metric_name}"] = record.metric_value
        if metrics:
            run.log(metrics)
        if config.wandb.log_artifacts:
            artifact = wandb.Artifact(f"{result.spec.run_id}-paths", type="prml-vslam-run")
            artifact.add_reference(result.spec.artifact_root.as_uri())
            run.log_artifact(artifact)
    finally:
        run.finish()


def _resolve_wandb_module(wandb_module: ModuleType | None) -> ModuleType:
    if wandb_module is not None:
        return wandb_module
    try:
        import wandb
    except ImportError as exc:
        raise RuntimeError(
            "W&B logging is enabled, but the `wandb` package is not installed. "
            "Install it or set `[wandb].enabled = false`."
        ) from exc
    return wandb
