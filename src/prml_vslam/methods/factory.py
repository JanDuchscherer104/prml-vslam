"""Typed backend factory for method-owned SLAM backend construction.

The factory is the method package's construction seam. Pipeline planning may
ask it for descriptors and runtime code may ask it to instantiate a backend,
but the factory does not own stage lifecycle, resource placement, event
recording, or benchmark policy.
"""

from __future__ import annotations

from typing import Protocol

from prml_vslam.methods.config_contracts import MethodId, SlamBackendConfig
from prml_vslam.methods.configs import BackendConfig
from prml_vslam.methods.descriptors import BackendCapabilities, BackendDescriptor
from prml_vslam.methods.protocols import SlamBackend
from prml_vslam.utils import PathConfig


class BackendFactoryProtocol(Protocol):
    """Factory surface consumed by pipeline runtimes and tests."""

    def describe(self, backend_config: SlamBackendConfig) -> BackendDescriptor:
        """Return the descriptor for one backend config."""

    def build(self, backend_config: BackendConfig, *, path_config: PathConfig | None = None) -> SlamBackend:
        """Instantiate one executable backend from its typed config."""


class BackendFactory(BackendFactoryProtocol):
    """Build method backends from the repository's discriminated config union.

    Concrete backend configs own their factory behavior through
    :class:`prml_vslam.utils.FactoryConfig`. This class centralizes validation
    and descriptor creation so pipeline code does not switch on method ids in
    multiple places.
    """

    def describe(self, backend_config: SlamBackendConfig) -> BackendDescriptor:
        """Return capability metadata without constructing the backend.

        The descriptor is safe for plan previews and app controls because it is
        derived from config properties only.
        """
        method_id = _require_method_id(backend_config)
        return BackendDescriptor(
            key=method_id.value,
            display_name=backend_config.display_name,
            capabilities=BackendCapabilities(
                offline=backend_config.supports_offline,
                streaming=backend_config.supports_streaming,
                dense_points=backend_config.supports_dense_points,
                live_preview=backend_config.supports_live_preview,
                native_visualization=backend_config.supports_native_visualization,
                trajectory_benchmark_support=backend_config.supports_trajectory_benchmark,
            ),
            default_resources=backend_config.default_resources,
            notes=backend_config.notes,
        )

    def build(self, backend_config: BackendConfig, *, path_config: PathConfig | None = None) -> SlamBackend:
        """Instantiate one executable backend from its typed config.

        Args:
            backend_config: Concrete method-owned backend config.
            path_config: Optional repository path policy needed by external
                wrappers such as ViSTA.

        Returns:
            Backend implementing the method protocols for offline and/or
            streaming execution.
        """
        method_id = _require_method_id(backend_config)
        if method_id is MethodId.MAST3R:
            raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")
        backend = backend_config.setup_target(path_config=path_config)
        if backend is None:
            raise RuntimeError(f"Failed to build backend '{method_id.value}'.")
        return backend


def _require_method_id(backend_config: SlamBackendConfig) -> MethodId:
    method_id = backend_config.method_id
    if method_id is None:
        raise RuntimeError("Backend config must define method_id.")
    return method_id


__all__ = ["BackendFactory", "BackendFactoryProtocol"]
