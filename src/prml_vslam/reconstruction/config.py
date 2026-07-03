"""Canonical reconstruction backend configs.

These are package-owned method-selection contracts for reconstruction
implementations. They may use :class:`prml_vslam.utils.FactoryConfig` because
they construct concrete reconstruction backends; pipeline reconstruction stage
configs should reference them rather than duplicating method-specific policy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import ConfigDict, Field

from prml_vslam.utils import BaseConfig, FactoryConfig

from .contracts import ReconstructionMethodId

if TYPE_CHECKING:
    from .nksr import NksrBackend
    from .poisson import PoissonBackend


class ReconstructionBackendConfig(BaseConfig):
    """Provide the package-local runtime contract shared by reconstruction configs.

    The discriminator names the reconstruction backend. Stage enablement,
    resource placement, and failure provenance stay in pipeline stage configs.
    """

    model_config = ConfigDict(extra="forbid")

    method_id: ReconstructionMethodId
    """Stable reconstruction backend discriminator."""

    @property
    def display_name(self) -> str:
        """Return the user-facing reconstruction label."""
        return self.method_id.display_name


class NksrBackendConfig(ReconstructionBackendConfig, FactoryConfig["NksrBackend"]):
    """Configure the Neural Kernel Surface Reconstruction (NKSR) backend.

    NKSR (CVPR 2023) is a high-fidelity surface reconstruction algorithm that
    processes large point clouds efficiently using GPU acceleration.
    """

    method_id: Literal[ReconstructionMethodId.NKSR] = ReconstructionMethodId.NKSR
    """Stable backend discriminator."""

    voxel_size: float = Field(default=0.01, gt=0.0)
    """Voxel size for reconstruction (detail level). Smaller is finer."""

    normal_radius_m: float = Field(default=0.05, gt=0.0)
    """Search radius in meters for estimating point-cloud normals."""

    normal_max_nn: int = Field(default=30, ge=1)
    """Maximum neighbor count for point-cloud normal estimation."""

    device: str = "cuda"
    """Device to run NKSR on (e.g., 'cuda', 'cpu')."""

    preprocess_normals: bool = True
    """Whether to estimate/re-estimate normals before running NKSR."""

    @property
    def target_type(self) -> type[NksrBackend]:
        """Return the concrete reconstruction backend type."""
        from .nksr import NksrBackend

        return NksrBackend

    def setup_target(self, **kwargs: Any) -> NksrBackend:
        """Instantiate the NKSR backend while ignoring unrelated kwargs."""
        kwargs.pop("path_config", None)
        from .nksr import NksrBackend

        return NksrBackend(self, input_payload=kwargs.get("input_payload"))


class PoissonBackendConfig(ReconstructionBackendConfig, FactoryConfig["PoissonBackend"]):
    """Configure the Screened Poisson surface reconstruction backend.

    Uses Open3D's implementation of Screened Poisson Surface Reconstruction.
    """

    method_id: Literal[ReconstructionMethodId.POISSON] = ReconstructionMethodId.POISSON
    """Stable backend discriminator."""

    depth: int = Field(default=8, ge=1)
    """Octree depth. Finer reconstruction requires larger depth."""

    width: float = 0.0
    """Target width of the octree. If > 0, depth is ignored."""

    scale: float = 1.1
    """The ratio between the diameter of the cube used for reconstruction and the diameter of the bounding box of the samples."""

    linear_fit: bool = False
    """If true, use linear interpolation for density estimation."""

    density_quantile: float = Field(default=0.02, ge=0.0, le=1.0)
    """Lower density quantile removed from Poisson meshes to trim weak support."""

    normal_radius_m: float = Field(default=0.05, gt=0.0)
    """Search radius in meters for estimating point-cloud normals."""

    normal_max_nn: int = Field(default=30, ge=1)
    """Maximum neighbor count for point-cloud normal estimation."""

    @property
    def target_type(self) -> type[PoissonBackend]:
        """Return the concrete reconstruction backend type."""
        from .poisson import PoissonBackend

        return PoissonBackend

    def setup_target(self, **kwargs: Any) -> PoissonBackend:
        """Instantiate the Poisson backend while ignoring unrelated kwargs."""
        kwargs.pop("path_config", None)
        from .poisson import PoissonBackend

        return PoissonBackend(self, input_payload=kwargs.get("input_payload"))


__all__ = [
    "NksrBackendConfig",
    "PoissonBackendConfig",
    "ReconstructionBackendConfig",
]
