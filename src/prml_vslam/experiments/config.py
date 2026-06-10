"""Typed configuration for offline benchmark experiment groups."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import Field, model_validator

from prml_vslam.pipeline.config import RunConfig
from prml_vslam.utils import BaseConfig, PathConfig


class WandbExperimentLoggingConfig(BaseConfig):
    """Configure optional Weights & Biases logging for an experiment."""

    enabled: bool = False
    """Enable W&B logging. Disabled mode imports no W&B package."""

    project: str = "prml-vslam"
    """W&B project name."""

    entity: str | None = None
    """Optional W&B entity."""

    group: str | None = None
    """Optional W&B run group. Defaults to the experiment name."""

    mode: Literal["online", "offline", "disabled"] | None = None
    """Optional W&B init mode."""

    tags: list[str] = Field(default_factory=list)
    """Tags applied to every concrete W&B run."""

    log_artifacts: bool = False
    """Whether to attach lightweight local report files as W&B artifacts."""


class ExperimentItem(BaseConfig):
    """One concrete pipeline run entry inside an offline experiment."""

    id: str
    """Stable item id used in reports and W&B run names."""

    run_config_path: Path | None = None
    """Path to an existing pipeline ``RunConfig`` TOML file."""

    run_config: RunConfig | None = None
    """Inline pipeline ``RunConfig`` payload."""

    overrides: dict[str, Any] = Field(default_factory=dict)
    """Declarative deep-merge updates applied before planning and execution."""

    allow_failure: bool = False
    """Record failed runs without making the whole experiment fail."""

    dataset_id: str | None = None
    """Optional dataset label for tidy analysis rows."""

    sequence_id: str | None = None
    """Optional sequence label for tidy analysis rows."""

    method_id: str | None = None
    """Optional method label for tidy analysis rows."""

    preset_id: str | None = None
    """Optional method-parameter preset label."""

    @model_validator(mode="after")
    def validate_run_config_source(self) -> Self:
        """Require exactly one source for the concrete run config."""
        source_count = int(self.run_config_path is not None) + int(self.run_config is not None)
        if source_count != 1:
            raise ValueError("ExperimentItem requires exactly one of `run_config_path` or `run_config`.")
        return self


class ExperimentConfig(BaseConfig):
    """Group explicit offline run configs into one benchmark experiment."""

    name: str
    """Experiment id and default W&B group."""

    output_dir: Path = Path(".artifacts/experiments")
    """Directory for experiment reports and long-form tables."""

    fail_fast: bool = False
    """Stop after the first disallowed failed item."""

    items: list[ExperimentItem] = Field(default_factory=list)
    """Concrete experiment items to plan and execute."""

    wandb: WandbExperimentLoggingConfig = Field(default_factory=WandbExperimentLoggingConfig)
    """Optional W&B logging policy."""

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        """Reject empty experiments and duplicate item ids."""
        if not self.items:
            raise ValueError("ExperimentConfig requires at least one item.")
        item_ids = [item.id for item in self.items]
        duplicates = sorted({item_id for item_id in item_ids if item_ids.count(item_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate experiment item id(s): {', '.join(duplicates)}")
        return self


def load_experiment_config(path: Path, *, path_config: PathConfig | None = None) -> ExperimentConfig:
    """Load an experiment config TOML path with repo-relative resolution."""
    config_paths = PathConfig() if path_config is None else path_config
    resolved = config_paths.resolve_toml_path(path, must_exist=True)
    config = ExperimentConfig.from_toml(resolved)
    return _resolve_item_paths(config, base_dir=resolved.parent)


def _resolve_item_paths(config: ExperimentConfig, *, base_dir: Path) -> ExperimentConfig:
    updated_items: list[ExperimentItem] = []
    for item in config.items:
        if item.run_config_path is None or item.run_config_path.is_absolute():
            updated_items.append(item)
            continue
        updated_items.append(item.model_copy(update={"run_config_path": (base_dir / item.run_config_path).resolve()}))
    return config.model_copy(update={"items": updated_items})


def deep_merge_config_snapshot(base: Mapping[str, Any], updates: Mapping[str, Any]) -> dict[str, Any]:
    """Return a recursive config snapshot merge without mutating either input."""
    merged: dict[str, Any] = dict(base)
    for key, value in updates.items():
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge_config_snapshot(existing, value)
        else:
            merged[key] = value
    return merged
