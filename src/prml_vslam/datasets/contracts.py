"""Dataset-owned contracts."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Generic, Literal, TypeAlias, TypeVar

from pydantic import Field, model_validator

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.utils import BaseConfig, BaseData

SequenceKey = int | str
SceneT = TypeVar("SceneT", bound=BaseData)
ModalityT = TypeVar("ModalityT", bound=StrEnum)
SequenceT = TypeVar("SequenceT", int, str)


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"
    TUM_RGBD = "tum_rgbd"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {self.ADVIO: "ADVIO", self.TUM_RGBD: "TUM RGB-D"}[self]


class AdvioPoseSource(StrEnum):
    """ADVIO trajectory providers surfaced through replay and pipeline contracts."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"
    TANGO_RAW = "tango_raw"
    TANGO_AREA_LEARNING = "tango_area_learning"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            self.GROUND_TRUTH: "Ground Truth",
            self.ARCORE: "ARCore",
            self.ARKIT: "ARKit",
            self.TANGO_RAW: "Tango Raw",
            self.TANGO_AREA_LEARNING: "Tango Area-Learning",
            self.NONE: "No Pose Overlay",
        }[self]

    @property
    def is_real_provider(self) -> bool:
        return self is not self.NONE


class AdvioPoseFrameMode(StrEnum):
    """Coordinate-frame semantics for served ADVIO trajectories."""

    PROVIDER_WORLD = "provider_world"
    REFERENCE_WORLD = "reference_world"
    LOCAL_FIRST_POSE = "local_first_pose"

    @property
    def label(self) -> str:
        return {
            self.PROVIDER_WORLD: "Provider World",
            self.REFERENCE_WORLD: "Aligned Global",
            self.LOCAL_FIRST_POSE: "Local First Pose",
        }[self]


class AdvioServingConfig(BaseConfig):
    """Typed ADVIO serving semantics shared by request and manifest contracts."""

    dataset_id: Literal["advio"] = "advio"
    pose_source: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH
    pose_frame_mode: AdvioPoseFrameMode = AdvioPoseFrameMode.PROVIDER_WORLD

    @model_validator(mode="after")
    def validate_real_provider(self) -> AdvioServingConfig:
        if not self.pose_source.is_real_provider:
            raise ValueError("AdvioServingConfig.pose_source must name a real provider, not `none`.")
        return self


DatasetServingConfig: TypeAlias = AdvioServingConfig


class AdvioRawPoseRefs(BaseData):
    """Relevant ADVIO raw pose artifacts preserved in the normalized manifest."""

    ground_truth_csv_path: Path
    arcore_csv_path: Path | None = None
    arkit_csv_path: Path | None = None
    tango_raw_csv_path: Path | None = None
    tango_area_learning_csv_path: Path | None = None
    selected_pose_csv_path: Path | None = None


class AdvioManifestAssets(BaseData):
    """ADVIO-specific manifest payload preserved for downstream consumers."""

    calibration_path: Path
    intrinsics: CameraIntrinsics
    T_cam_imu: FrameTransform
    pose_refs: AdvioRawPoseRefs
    fixpoints_csv_path: Path | None = None
    tango_point_cloud_index_path: Path | None = None
    tango_payload_root: Path | None = None


class FrameSelectionConfig(BaseConfig):
    frame_stride: int = Field(default=1, ge=1)
    target_fps: float | None = Field(default=None, gt=0.0)

    @model_validator(mode="after")
    def validate_single_sampling_mode(self) -> FrameSelectionConfig:
        if self.target_fps is not None and self.frame_stride != 1:
            raise ValueError("Configure either `frame_stride` or `target_fps`, not both.")
        return self

    def stride_for_timestamps_ns(self, timestamps_ns: Sequence[int]) -> int:
        if self.target_fps is None or len(timestamps_ns) < 2:
            return self.frame_stride
        duration_s = max((int(timestamps_ns[-1]) - int(timestamps_ns[0])) / 1e9, 0.0)
        native_fps = 0.0 if duration_s <= 0.0 else (len(timestamps_ns) - 1) / duration_s
        return max(1, int(round(native_fps / self.target_fps))) if native_fps > 0.0 else 1

    def stride_for_timestamps_s(self, timestamps_s: Sequence[float]) -> int:
        return self.stride_for_timestamps_ns([int(round(value * 1e9)) for value in timestamps_s])


class DatasetDownloadResult(BaseData, Generic[SequenceT, ModalityT]):
    """Summary of one explicit dataset download action."""

    sequence_ids: list[SequenceT]
    modalities: list[ModalityT]
    downloaded_archive_count: int = 0
    reused_archive_count: int = 0
    written_path_count: int = 0


class LocalSceneStatus(BaseData, Generic[SceneT, ModalityT]):
    """Local availability summary for one dataset scene."""

    scene: SceneT
    sequence_dir: Path | None = None
    local_modalities: list[ModalityT] = Field(default_factory=list)
    archive_path: Path | None = None
    replay_ready: bool = False
    offline_ready: bool = False


class DatasetSummary(BaseData):
    """High-level summary of committed and local dataset coverage."""

    total_scene_count: int
    local_scene_count: int
    replay_ready_scene_count: int
    offline_ready_scene_count: int
    cached_archive_count: int
    total_remote_archive_bytes: int


def selected_advio_pose_source(
    dataset_serving: DatasetServingConfig | None,
    *,
    default: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
) -> AdvioPoseSource:
    """Return the effective ADVIO provider for one optional serving config."""
    return default if dataset_serving is None else dataset_serving.pose_source


__all__ = [
    "AdvioManifestAssets",
    "AdvioPoseFrameMode",
    "AdvioPoseSource",
    "AdvioRawPoseRefs",
    "AdvioServingConfig",
    "DatasetDownloadResult",
    "DatasetId",
    "DatasetServingConfig",
    "DatasetSummary",
    "FrameSelectionConfig",
    "LocalSceneStatus",
    "SequenceKey",
    "selected_advio_pose_source",
]
