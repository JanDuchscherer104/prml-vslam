"""Persisted SLAM backend config and backend muxing.

The SLAM stage owns the public backend discriminator, output policy, and
config-as-factory variants used by pipeline launch. Concrete method adapters
are imported only when ``setup_target(...)`` is called so heavy resources are
created in the execution process.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self, TypeAlias

from pydantic import ConfigDict, Field, model_validator

from prml_vslam.utils import BaseConfig, FactoryConfig, PathConfig

if TYPE_CHECKING:
    from prml_vslam.methods.lingbot.adapter import LingbotMapSlamBackend
    from prml_vslam.methods.mast3r.adapter import Mast3rSlamBackend
    from prml_vslam.methods.vista.adapter import VistaSlamBackend


class MethodId(StrEnum):
    """Name the SLAM backends exposed by the pipeline stage config."""

    VISTA = "vista"
    MAST3R = "mast3r"
    LINGBOT_MAP = "lingbot_map"

    @property
    def display_name(self) -> str:
        """Return the upstream method name shown to users."""
        match self:
            case MethodId.VISTA:
                return "ViSTA-SLAM"
            case MethodId.MAST3R:
                return "MASt3R-SLAM"
            case MethodId.LINGBOT_MAP:
                return "LingBot-Map"


class SlamOutputPolicy(BaseConfig):
    """Describe optional SLAM geometry materialization."""

    model_config = ConfigDict(extra="ignore")

    emit_dense_points: bool = True
    """Whether the backend should materialize a dense point cloud artifact."""

    emit_sparse_points: bool = False
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
    def eager_load_offline_rgb(self) -> bool:
        """Whether offline source dematerialization should load RGB arrays."""
        return True

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
    """Configure the canonical MASt3R-SLAM backend.

    Hyperparameters for tracking / retrieval / local-opt / reloc are loaded
    from the upstream YAML pointed to by :attr:`yaml_config_path`. To deviate
    from upstream defaults edit ``config/base.yaml`` in the submodule or point
    :attr:`yaml_config_path` at a repo-local override.
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
    """Upstream YAML hyperparameter config (use ``calib.yaml`` for use_calib=True presets)."""

    c_conf_threshold: float = 1.5
    """Confidence threshold applied when exporting the dense point cloud."""

    device: str = "cuda:0"
    """Torch device used for model inference and CUDA kernels."""

    img_size: Literal[224, 512] = 512
    """Encoder long-edge size for MASt3R. Upstream supports only 224 or 512."""

    use_calib: bool | None = None
    """Override the YAML 'use_calib' flag. None = respect YAML; True/False = force it."""

    match_frac_thresh: float | None = Field(default=None, gt=0.0, lt=1.0)
    """Override the upstream keyframe overlap threshold (`tracking.match_frac_thresh`).

    A new keyframe is added when the overlap with the current keyframe drops below
    this fraction. Higher values keyframe more eagerly (denser cloud, higher image
    coverage, slower run). ``None`` respects the YAML default (0.333)."""

    backend_poll_interval_s: float = 0.01
    """Sleep between iterations of the backend optimisation thread when idle."""

    backend_join_timeout_s: float = 30.0
    """Max seconds to wait for the backend thread to exit on close()."""

    keyframe_buffer_size: int = 512
    """Maximum number of keyframes the upstream SharedKeyframes can hold.

    Upstream default is 512, which preallocates ~3 GB of GPU tensors at
    img_size=512. Reduce this when GPU memory is tight or when you know the
    sequence will produce few keyframes.
    """

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
        return ["GPU acceleration is required for real MASt3R-SLAM runs."]

    @property
    def target_type(self) -> type[Mast3rSlamBackend]:
        """Return the backend type instantiated by ``setup_target``."""
        from prml_vslam.methods.mast3r.adapter import Mast3rSlamBackend

        return Mast3rSlamBackend

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> Mast3rSlamBackend:
        """Instantiate the MASt3R backend in the execution process."""
        from prml_vslam.methods.mast3r.adapter import Mast3rSlamBackend

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
    keyframe_detection: Literal["flow", "stride", "flow_stride"] = "flow"
    stride: Annotated[int, Field(ge=1)] = 3
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


class LingbotMapSlamBackendConfig(SlamBackendConfig, FactoryConfig["LingbotMapSlamBackend"]):
    """Configure the optional LingBot-Map backend."""

    method_id: Literal[MethodId.LINGBOT_MAP] = MethodId.LINGBOT_MAP

    checkpoint_path: Path = Path("external/lingbot-map/checkpoints/lingbot-map.pt")
    """Path to the LingBot-Map checkpoint weights."""

    device: Literal["auto", "cuda", "cpu"] = "auto"
    """Torch device preference used for model inference."""

    mode: Literal["streaming", "windowed"] = "streaming"
    """LingBot-Map inference API to use during repository offline execution."""

    image_size: int = Field(default=518, ge=1)
    patch_size: int = Field(default=14, ge=1)
    enable_3d_rope: bool = True
    max_frame_num: int = Field(default=1024, ge=1)
    num_scale_frames: int = Field(default=8, ge=1)
    kv_cache_sliding_window: int = Field(default=64, ge=1)
    keyframe_interval: int | Literal["auto"] = "auto"
    use_sdpa: bool = True
    use_amp: bool = True
    model_dtype: Literal["auto", "float32", "float16", "bfloat16"] = "auto"
    checkpoint_pos_embed: Literal["error", "interpolate", "drop"] = "error"
    camera_num_iterations: int = Field(default=4, ge=1)
    enable_point_head: bool = False
    window_size: int = Field(default=64, ge=1)
    overlap_size: int | None = Field(default=None, ge=1)
    overlap_keyframes: int | None = Field(default=None, ge=1)
    confidence_threshold: float = Field(default=0.0, ge=0.0)
    point_stride: int = Field(default=8, ge=1)
    max_points: int | None = Field(default=100_000, ge=1)
    """Optional output point cap applied after LingBot dense geometry extraction."""

    max_depth_m: float | None = Field(default=100.0, gt=0.0)

    @model_validator(mode="after")
    def validate_patch_grid(self) -> Self:
        """Ensure LingBot image dimensions produce an integral patch grid."""
        if self.image_size % self.patch_size != 0:
            raise ValueError("LingBot-Map `image_size` must be divisible by `patch_size`.")
        if self.keyframe_interval != "auto" and self.keyframe_interval < 1:
            raise ValueError("LingBot-Map `keyframe_interval` must be positive or `auto`.")
        return self

    @property
    def supports_offline(self) -> bool:
        """Whether the backend supports offline execution."""
        return True

    @property
    def eager_load_offline_rgb(self) -> bool:
        """LingBot consumes normalized RGB paths directly during offline inference."""
        return False

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
        return False

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
            "LingBot-Map is wired as an offline and bounded terminal-streaming repository backend.",
            "Streaming requires max_frames and emits terminal artifacts at finish, without incremental live preview.",
            "Windowed mode delegates finite-sequence windowing, overlap alignment, and stitching to upstream LingBot-Map.",
            "Install the LingBot optional dependency group and provide the checkpoint before real runs.",
        ]

    @property
    def target_type(self) -> type[LingbotMapSlamBackend]:
        """Return the backend type instantiated by ``setup_target``."""
        from prml_vslam.methods.lingbot.adapter import LingbotMapSlamBackend

        return LingbotMapSlamBackend

    def setup_target(self, *, path_config: PathConfig | None = None, **_kwargs: Any) -> LingbotMapSlamBackend:
        """Instantiate the LingBot-Map backend in the execution process."""
        from prml_vslam.methods.lingbot.adapter import LingbotMapSlamBackend

        return LingbotMapSlamBackend(self, path_config=path_config)


BackendConfig: TypeAlias = Annotated[
    VistaSlamBackendConfig | Mast3rSlamBackendConfig | LingbotMapSlamBackendConfig,
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
        case MethodId.LINGBOT_MAP:
            return LingbotMapSlamBackendConfig.model_validate({"method_id": MethodId.LINGBOT_MAP, **backend_payload})


__all__ = [
    "BackendConfig",
    "BackendConfigValue",
    "LingbotMapSlamBackendConfig",
    "Mast3rSlamBackendConfig",
    "MethodId",
    "SlamBackendConfig",
    "SlamOutputPolicy",
    "VistaSlamBackendConfig",
    "build_slam_backend_config",
]
