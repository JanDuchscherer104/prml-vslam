"""Backend capability descriptors consumed by planning and launch surfaces.

The descriptor layer is intentionally read-only metadata. It lets the pipeline
planner, CLI, and Streamlit workbench explain whether a backend can run
offline, stream, emit dense points, or support benchmarks without constructing
the backend or importing upstream runtime state.
"""

from __future__ import annotations

from pydantic import Field

from prml_vslam.pipeline.contracts.transport import TransportModel


class BackendCapabilities(TransportModel):
    """Boolean capability matrix advertised by one method backend.

    These fields drive availability diagnostics and UI messaging. They are not
    guarantees that all external dependencies are installed; runtime preflight
    and backend construction still fail early for missing checkpoints, repos,
    devices, or unsupported execution modes.
    """

    offline: bool
    streaming: bool
    dense_points: bool
    live_preview: bool
    native_visualization: bool
    trajectory_benchmark_support: bool


class BackendDescriptor(TransportModel):
    """User- and planner-facing description of a configured backend kind.

    The descriptor is a stable summary derived from method-owned config. It is
    safe to serialize into plan previews because it carries capability and
    resource hints only, not backend objects, credentials, or live state.
    """

    key: str
    display_name: str
    capabilities: BackendCapabilities
    default_resources: dict[str, float] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


__all__ = ["BackendCapabilities", "BackendDescriptor"]
