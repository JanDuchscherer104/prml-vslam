"""Public orchestration surface for the repository pipeline.

The :mod:`prml_vslam.pipeline` package owns typed run requests, deterministic
plans, normalized input and output artifacts, runtime events, projected
snapshots, and the execution façade used by the app and CLI. This root module
re-exports the smallest set of contracts that other packages most often import
directly.
"""

from .contracts.artifacts import SlamArtifacts
from .contracts.plan import RunPlan
from .contracts.provenance import RunSummary
from .contracts.request import PipelineMode, RunRequest
from .contracts.sequence import SequenceManifest

__all__ = [
    "PipelineMode",
    "RunPlan",
    "RunRequest",
    "SequenceManifest",
    "RunSummary",
    "SlamArtifacts",
]
