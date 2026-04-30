"""Persisted SLAM backend config and backend muxing.

The SLAM stage owns the public backend discriminator, output policy, and
config-as-factory variants used by pipeline launch. Concrete method adapters
are imported only when ``setup_target(...)`` is called so heavy resources are
created in the execution process.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, TypeAlias

from pydantic import ConfigDict, Field

from prml_vslam.utils import BaseConfig, FactoryConfig, PathConfig

if TYPE_CHECKING:
    from prml_vslam.methods.mast3r import Mast3rSlamBackend
    from prml_vslam.methods.vista.adapter import VistaSlamBackend


class MethodId(StrEnum):
    """Name the SLAM backends exposed by the pipeline stage config."""

    VISTA = "vista"
    MAST3R = "mast3r"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MAST3R:
                return "MASt3R-SLAM"


class SlamOutputPolicy(BaseConfig):
    """Describe optional SLAM geometry materialization."""

    model_config = ConfigDict(extra="ignore")

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = True
    """Whether the backend should materialize sparse geometry artifacts."""


class SlamBackendConfig(BaseConfig):
    """Base for concrete stage-owned SLAM backend variants."""

    model_config = ConfigDict(extra="ignore")

    method_id: MethodId | None = None
    """Stable backend discriminator used by the stage-owned union."""

    max_frames: int | None = None
    """Optional frame cap used for debugging or short smoke runs."""

    @property
    def display_name(self) -> str:
        """Return the user-facing backend label used by planning and UI surfaces."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.display_name

    @property
    def kind(self) -> str:
        """Return the backend discriminator string."""
        if self.method_id is None:
            raise NotImplementedError("Concrete backend configs must define method_id.")
        return self.method_id.value

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        raise NotImplementedError

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        raise NotImplementedError

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        raise NotImplementedError

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        raise NotImplementedError

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        raise NotImplementedError

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        raise NotImplementedError

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default resource hints."""
        return {}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes surfaced to callers."""
        return []


class Mast3rSlamBackendConfig(SlamBackendConfig, FactoryConfig["Mast3rSlamBackend"]):
    """Configure the canonical MASt3R-SLAM backend wrapper.

    Hyperparameters for tracking, retrieval, local optimization, and
    relocalization are loaded from the upstream YAML config. Override
    :attr:`yaml_config_path` when a run needs a repo-local variant instead of
    editing the submodule in place.
    """

    method_id: Literal[MethodId.MAST3R] = MethodId.MAST3R
    mast3r_slam_dir: Path = Path("external/mast3r-slam")
    """Path to the MASt3R-SLAM submodule root."""

    checkpoint_path: Path = Path(
        "external/mast3r-slam/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric.pth"
    )
    """Path to the MASt3R backbone weights."""

    retrieval_checkpoint_path: Path = Path(
        "external/mast3r-slam/checkpoints/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric_retrieval_trainingfree.pth"
    )
    """Path to the retrieval weights used for loop closure."""

    yaml_config_path: Path = Path("external/mast3r-slam/config/base.yaml")
    """Path to the upstream YAML hyperparameter config."""

    c_conf_threshold: float = Field(default=1.5, ge=0.0)
    """Confidence threshold applied when exporting the dense point cloud."""

    device: str = "cuda:0"
    """Torch device used for model inference and CUDA kernels."""

    img_size: int = Field(default=512, gt=0)
    """Image long-edge size for the MASt3R encoder."""

    use_calib: bool | None = None
    """Override the upstream ``use_calib`` flag; ``None`` keeps the YAML value."""

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return True

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return True

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return True

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return False

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return True

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default resource hints."""
        return {"CPU": 2.0, "GPU": 1.0}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return [
            "GPU acceleration and the editable upstream MASt3R-SLAM checkout are required for real runs.",
            "MASt3R exports a dense reconstruction cloud; sparse_points_ply remains empty unless upstream adds one.",
        ]

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the backend type instantiated by ``setup_target``."""
        from prml_vslam.methods.mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> Mast3rSlamBackend:
        """Instantiate the MASt3R backend in the execution process."""
        from prml_vslam.methods.mast3r import Mast3rSlamBackend

        return Mast3rSlamBackend(self, path_config=path_config)


class VistaSlamBackendConfig(SlamBackendConfig, FactoryConfig["VistaSlamBackend"]):
    """Configure the canonical ViSTA-SLAM backend."""

    method_id: Literal[MethodId.VISTA] = MethodId.VISTA
    vista_slam_dir: Path = Path("external/vista-slam")
    checkpoint_path: Path = Path("external/vista-slam/pretrains/frontend_sta_weights.pth")
    vocab_path: Path = Path("external/vista-slam/pretrains/ORBvoc.txt")
    max_view_num: int = 400
    flow_thres: float = 5.0
    neighbor_edge_num: int = 3
    loop_edge_num: int = 3
    loop_dist_min: int = 40
    loop_nms: int = 40
    loop_cand_thresh_neighbor: int = 5
    point_conf_thres: float = 4.2
    rel_pose_thres: float = 0.75
    pgo_every: int = 500
    random_seed: int = 43
    device: Literal["auto", "cuda", "cpu"] = "auto"

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def supports_streaming(self) -> bool:
        """Whether the backend supports streaming execution."""
        return True

    @property
    def supports_dense_points(self) -> bool:
        """Whether the backend can expose point-cloud outputs."""
        return True

    @property
    def supports_live_preview(self) -> bool:
        """Whether the backend can emit live preview payloads."""
        return True

    @property
    def supports_native_visualization(self) -> bool:
        """Whether the backend may emit native visualization artifacts."""
        return True

    @property
    def supports_trajectory_benchmark(self) -> bool:
        """Whether the backend supports repository trajectory evaluation."""
        return True

    @property
    def default_resources(self) -> dict[str, float]:
        """Return backend-owned default resource hints."""
        return {"CPU": 2.0, "GPU": 1.0}

    @property
    def notes(self) -> list[str]:
        """Return backend-specific planning notes."""
        return ["GPU acceleration is recommended for real ViSTA runs."]

    @property
    def target_type(self) -> type[VistaSlamBackend]:
        """Return the backend type instantiated by ``setup_target``."""
        from prml_vslam.methods.vista.adapter import VistaSlamBackend

        return VistaSlamBackend

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> VistaSlamBackend:
        """Instantiate the ViSTA backend in the execution process."""
        from prml_vslam.methods.vista.adapter import VistaSlamBackend

        return VistaSlamBackend(self, path_config=path_config)


BackendConfig: TypeAlias = Annotated[
    VistaSlamBackendConfig | Mast3rSlamBackendConfig,
    Field(discriminator="method_id"),
]


BackendConfigValue: TypeAlias = Path | str | int | float | bool | None


def build_slam_backend_config(
    *,
    method: MethodId,
    max_frames: int | None = None,
    overrides: dict[str, BackendConfigValue] | None = None,
) -> BackendConfig:
    """Build a typed backend config from a selected method and overrides."""
    backend_payload: dict[str, BackendConfigValue] = {"max_frames": max_frames}
    if overrides is not None:
        backend_payload.update(overrides)
    match method:
        case MethodId.VISTA:
            return VistaSlamBackendConfig.model_validate({"method_id": MethodId.VISTA, **backend_payload})
        case MethodId.MAST3R:
            return Mast3rSlamBackendConfig.model_validate({"method_id": MethodId.MAST3R, **backend_payload})


__all__ = [
    "BackendConfig",
    "BackendConfigValue",
    "Mast3rSlamBackendConfig",
    "MethodId",
    "SlamBackendConfig",
    "SlamOutputPolicy",
    "VistaSlamBackendConfig",
    "build_slam_backend_config",
]
