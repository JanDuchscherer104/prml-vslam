"""Run-scoped context shared by pipeline runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from prml_vslam.methods.descriptors import BackendDescriptor
from prml_vslam.pipeline.config import RunConfig
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.utils import PathConfig, RunArtifactPaths


@dataclass(frozen=True, slots=True)
class StageExecutionContext:
    """Immutable inputs shared by coordinator-owned stage input builders."""

    plan: RunPlan
    path_config: PathConfig
    run_paths: RunArtifactPaths
    backend_descriptor: BackendDescriptor
    run_config: RunConfig


__all__ = ["StageExecutionContext"]
