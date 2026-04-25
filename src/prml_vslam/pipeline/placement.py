"""Repo-owned placement policy translation for the Ray backend.

This module contains the narrow translation layer from stage execution
resources into the Ray-specific actor options used by the backend runtime.
"""

from __future__ import annotations

from typing import TypeAlias

from prml_vslam.methods.stage.config import BackendConfigValue
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.stages import StageKey

RayActorResources: TypeAlias = dict[str, float]
RayActorOptionsValue: TypeAlias = float | int | RayActorResources | None
RayActorOptions: TypeAlias = dict[str, RayActorOptionsValue]


def actor_options_for_stage(
    *,
    stage_key: StageKey,
    run_config: RunConfig,
    backend: BackendConfigValue | None = None,
    default_num_cpus: float = 1.0,
    default_num_gpus: float = 0.0,
    restartable: bool = False,
    inherit_backend_defaults: bool = False,
) -> RayActorOptions:
    """Translate one repo-owned stage execution policy into Ray actor options."""
    stage_config = run_config.stages.section(stage_key)
    backend_resources = (
        backend.default_resources
        if backend is not None
        else (
            run_config.stages.slam.backend.default_resources
            if stage_key is StageKey.SLAM and run_config.stages.slam.backend is not None
            else {}
        )
    )
    resources = dict(backend_resources) if inherit_backend_defaults else {}
    resources.update(stage_config.resources.custom_resources)
    if stage_config.resources.num_cpus is not None:
        resources["CPU"] = stage_config.resources.num_cpus
    if stage_config.resources.num_gpus is not None:
        resources["GPU"] = stage_config.resources.num_gpus
    return {
        "num_cpus": float(resources.pop("CPU", default_num_cpus)),
        "num_gpus": float(resources.pop("GPU", default_num_gpus)),
        "resources": resources or None,
        "max_restarts": -1 if restartable else 0,
        "max_task_retries": 1 if restartable else 0,
    }


__all__ = ["RayActorOptions", "RayActorOptionsValue", "RayActorResources", "actor_options_for_stage"]
