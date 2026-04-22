"""Stage-local contracts for bounded summary projection."""

from __future__ import annotations

from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.plan import RunPlan
from prml_vslam.pipeline.contracts.request import RunRequest
from prml_vslam.utils import BaseData, RunArtifactPaths


class SummaryRuntimeInput(BaseData):
    """Inputs required to project durable summary artifacts.

    Summary is projection-only: it consumes terminal stage outcomes and the run
    plan to write manifests and the final run summary. It must not compute new
    metrics or reinterpret domain payloads.
    """

    # TODO(pipeline-refactor/WP-09): Replace RunRequest with target RunConfig
    # summary policy once launch paths submit RunConfig directly.
    request: RunRequest
    """Current run request carrying summary fingerprint inputs."""

    plan: RunPlan
    """Compiled run plan whose artifact root owns summary outputs."""

    run_paths: RunArtifactPaths
    """Canonical artifact paths for the current run."""

    stage_outcomes: list[StageOutcome]
    """Terminal outcomes accumulated before the summary stage runs."""


__all__ = ["SummaryRuntimeInput"]
