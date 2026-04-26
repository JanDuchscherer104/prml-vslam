from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prml_vslam.methods.stage.backend_config import SlamBackendConfig
    from prml_vslam.pipeline.config import RunConfig
    from prml_vslam.pipeline.contracts.plan import RunPlan
    from prml_vslam.pipeline.runner import StageResultStore
    from prml_vslam.sources.protocols import OfflineSequenceSource
    from prml_vslam.utils import PathConfig, RunArtifactPaths


@dataclass(frozen=True, slots=True)
class PipelinePlanContext:
    """Inputs available while compiling a deterministic run plan."""

    run_config: RunConfig
    path_config: PathConfig
    run_paths: RunArtifactPaths
    slam_backend: SlamBackendConfig | None = None


@dataclass(frozen=True, slots=True)
class PipelineExecutionContext:
    """Inputs available while constructing and executing stage runtimes."""

    run_config: RunConfig
    path_config: PathConfig
    run_paths: RunArtifactPaths
    plan: RunPlan
    results: StageResultStore
    source: OfflineSequenceSource | None = None
    slam_backend: SlamBackendConfig | None = None


__all__ = ["PipelinePlanContext", "PipelineExecutionContext"]
