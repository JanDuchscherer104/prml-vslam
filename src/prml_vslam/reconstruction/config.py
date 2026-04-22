"""Canonical reconstruction backend configs.

These are package-owned method-selection contracts for reconstruction
implementations. They may use :class:`prml_vslam.utils.FactoryConfig` because
they construct concrete reconstruction backends; pipeline reconstruction stage
configs should reference them rather than duplicating TSDF or Open3D policy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import ConfigDict, Field

from prml_vslam.utils import BaseConfig, FactoryConfig

from .contracts import ReconstructionMethodId

if TYPE_CHECKING:
    from .open3d_tsdf import Open3dTsdfBackend


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


class Open3dTsdfBackendConfig(ReconstructionBackendConfig, FactoryConfig["Open3dTsdfBackend"]):
    """Configure the minimal Open3D TSDF reconstruction backend.

    The repo targets Open3D ``0.19.x`` and uses its
    ``ScalableTSDFVolume`` integration path directly. Inputs must be metric RGB-D
    observations with coherent intrinsics and ``T_world_camera`` poses; this
    config controls TSDF parameters, not source normalization or pipeline
    scheduling.
    """

    method_id: Literal[ReconstructionMethodId.OPEN3D_TSDF] = ReconstructionMethodId.OPEN3D_TSDF
    """Stable backend discriminator."""

    voxel_length_m: float = Field(default=0.02, gt=0.0)
    """Length of one TSDF voxel edge in meters."""

    sdf_trunc_m: float = Field(default=0.08, gt=0.0)
    """Signed-distance truncation used by the TSDF integrator in meters."""

    depth_scale: float = Field(default=1.0, gt=0.0)
    """Scale applied by Open3D before depth truncation."""

    depth_trunc_m: float = Field(default=3.0, gt=0.0)
    """Depth values beyond this range are discarded before integration."""

    integrate_color: bool = False
    """Whether RGB values should be fused into the TSDF volume."""

    convert_rgb_to_intensity: bool = False
    """Whether Open3D should convert RGB to intensity when building RGBD images."""

    volume_unit_resolution: int = Field(default=16, ge=1)
    """Open3D TSDF volume-unit resolution."""

    depth_sampling_stride: int = Field(default=4, ge=1)
    """Open3D TSDF depth-sampling stride."""

    extract_mesh: bool = False
    """Whether to preserve an extracted mesh in addition to the point cloud."""

    @property
    def target_type(self) -> type[Open3dTsdfBackend]:
        """Return the concrete reconstruction backend type."""
        from .open3d_tsdf import Open3dTsdfBackend

        return Open3dTsdfBackend

    def setup_target(self, **kwargs: Any) -> Open3dTsdfBackend:
        """Instantiate the Open3D TSDF backend while ignoring unrelated kwargs."""
        kwargs.pop("path_config", None)
        from .open3d_tsdf import Open3dTsdfBackend

        return Open3dTsdfBackend(self)


__all__ = [
    "Open3dTsdfBackendConfig",
    "ReconstructionBackendConfig",
]
