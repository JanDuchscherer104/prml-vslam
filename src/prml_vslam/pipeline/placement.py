"""Repo-owned placement policy translation for the Ray backend."""

from __future__ import annotations

from typing import TypeAlias

from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.pipeline.contracts.stages import StageKey

RayActorResources: TypeAlias = dict[str, float]
RayActorOptionsValue: TypeAlias = float | int | RayActorResources | None
RayActorOptions: TypeAlias = dict[str, RayActorOptionsValue]


def actor_options_for_stage(
    *,
    stage_key: StageKey,
    request: RunRequest,
    backend: BackendDescriptor,
    default_num_cpus: float = 1.0,
    default_num_gpus: float = 0.0,
    restartable: bool = False,
    inherit_backend_defaults: bool = False,
) -> RayActorOptions:
    """Translate one repo-owned placement policy into Ray actor options."""
    placement = request.placement.by_stage.get(stage_key)
    resources = dict(backend.default_resources) if inherit_backend_defaults else {}
    if placement is not None:
        resources.update(placement.resources)
    return {
        "num_cpus": float(resources.pop("CPU", default_num_cpus)),
        "num_gpus": float(resources.pop("GPU", default_num_gpus)),
        "resources": resources or None,
        "max_restarts": -1 if restartable else 0,
        "max_task_retries": 1 if restartable else 0,
    }


__all__ = ["RayActorOptions", "RayActorOptionsValue", "RayActorResources", "actor_options_for_stage"]
