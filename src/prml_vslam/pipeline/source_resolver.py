"""Pipeline-local source resolution for offline-capable requests.

This module adapts request-layer source specs into concrete
:class:`prml_vslam.protocols.source.OfflineSequenceSource` owners. It belongs to
the pipeline because it translates request contracts into source adapters, but
the actual dataset and IO logic still stays in their owning packages.
"""

from __future__ import annotations

from dataclasses import dataclass

from prml_vslam.pipeline.contracts.request import SourceSpec
from prml_vslam.pipeline.stages.source.config import source_backend_config_from_source_spec
from prml_vslam.protocols.source import OfflineSequenceSource
from prml_vslam.utils import PathConfig


@dataclass(slots=True)
class OfflineSourceResolver:
    """Resolve request-layer source specs into offline-capable source adapters."""

    path_config: PathConfig

    def resolve(self, source_spec: SourceSpec) -> OfflineSequenceSource:
        """Resolve one request source spec into the owning offline source adapter."""
        # TODO(pipeline-refactor/WP-10): Delete this resolver once legacy
        # RunRequest.source callers construct SourceBackendConfig directly.
        return source_backend_config_from_source_spec(source_spec).setup_target(path_config=self.path_config)


__all__ = ["OfflineSourceResolver"]
