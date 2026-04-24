"""Runtime option contracts shared by external VSLAM method adapters.

Persisted backend variants and muxing live in the SLAM stage config. This
module keeps method-local identifiers and generic runtime options used by
wrapper protocols and tests without constructing pipeline runtimes.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict

from prml_vslam.utils import BaseConfig


class MethodId(StrEnum):
    """Name the external or repository-local backends supported by the package."""

    VISTA = "vista"
    MAST3R = "mast3r"
    MOCK = "mock"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MAST3R:
                return "MASt3R-SLAM"
            case MethodId.MOCK:
                return "Mock Preview"


class SlamOutputPolicy(BaseConfig):
    """Describe which optional geometry surfaces a backend should materialize.

    These flags shape the contents of :class:`prml_vslam.pipeline.SlamArtifacts`
    without changing stage order or pipeline semantics.
    """

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = True
    """Whether the backend should materialize sparse geometry artifacts."""


class SlamBackendConfig(BaseConfig):
    """Provide generic backend runtime options shared by method protocols."""

    model_config = ConfigDict(extra="forbid")

    method_id: MethodId | None = None
    """Optional method-local identifier for direct wrapper use."""

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""

    @property
    def display_name(self) -> str:
        """Return the user-facing backend label used across planning and UI surfaces."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.display_name

    @property
    def kind(self) -> str:
        """Return the legacy backend discriminator string."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.value


__all__ = ["MethodId", "SlamBackendConfig", "SlamOutputPolicy"]
