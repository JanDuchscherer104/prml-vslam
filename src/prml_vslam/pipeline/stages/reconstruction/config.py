"""Persisted config and backend muxing for the ``reconstruction`` stage."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.config import StageConfig
from prml_vslam.utils import BaseConfig, FactoryConfig

if TYPE_CHECKING:
    from prml_vslam.reconstruction.open3d_tsdf import Open3dTsdfBackend


class ReconstructionId(StrEnum):
    """Name reconstruction backends exposed by the pipeline stage."""

    OPEN3D_TSDF = "open3d_tsdf"

    @property
    def display_name(self) -> str:
        """Return the user-facing backend label."""
        match self:
            case ReconstructionId.OPEN3D_TSDF:
                return "Open3D TSDF"


class ReconstructionBackendConfig(BaseConfig):
    """Base for stage-owned reconstruction backend variants."""

    model_config = ConfigDict(extra="ignore")

    reconstruction_id: ReconstructionId
    """Stable reconstruction backend discriminator."""

    @property
    def display_name(self) -> str:
        """Return the user-facing reconstruction label."""
        return self.reconstruction_id.display_name


class Open3dTsdfReconstructionConfig(ReconstructionBackendConfig, FactoryConfig["Open3dTsdfBackend"]):
    """Configure the Open3D TSDF reconstruction backend through the stage."""

    reconstruction_id: Literal[ReconstructionId.OPEN3D_TSDF] = ReconstructionId.OPEN3D_TSDF
    voxel_length_m: float = Field(default=0.02, gt=0.0)
    sdf_trunc_m: float = Field(default=0.08, gt=0.0)
    depth_scale: float = Field(default=1.0, gt=0.0)
    depth_trunc_m: float = Field(default=3.0, gt=0.0)
    integrate_color: bool = False
    convert_rgb_to_intensity: bool = False
    volume_unit_resolution: int = Field(default=16, ge=1)
    depth_sampling_stride: int = Field(default=4, ge=1)
    extract_mesh: bool = False

    @property
    def target_type(self) -> type[Open3dTsdfBackend]:
        """Return the concrete reconstruction backend type."""
        from prml_vslam.reconstruction.open3d_tsdf import Open3dTsdfBackend

        return Open3dTsdfBackend

    def setup_target(self, **kwargs: Any) -> Open3dTsdfBackend:
        """Instantiate the Open3D backend in the execution process."""
        kwargs.pop("path_config", None)
        from prml_vslam.reconstruction.open3d_tsdf import Open3dTsdfBackend

        return Open3dTsdfBackend(self)


ReconstructionBackend: TypeAlias = Annotated[
    Open3dTsdfReconstructionConfig,
    Field(discriminator="reconstruction_id"),
]


class ReconstructionStageConfig(StageConfig):
    """Persisted reconstruction stage policy and backend selection."""

    model_config = ConfigDict(extra="ignore")

    stage_key: StageKey | None = StageKey.RECONSTRUCTION
    backend: ReconstructionBackend = Field(default_factory=Open3dTsdfReconstructionConfig)
    """Concrete reconstruction backend config."""


__all__ = [
    "Open3dTsdfReconstructionConfig",
    "ReconstructionBackend",
    "ReconstructionBackendConfig",
    "ReconstructionId",
    "ReconstructionStageConfig",
]
