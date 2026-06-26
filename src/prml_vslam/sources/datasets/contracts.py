from __future__ import annotations

import math
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Generic, Literal, TypeVar

from pydantic import Field, model_validator

from prml_vslam.utils import BaseConfig, BaseData

SequenceKey = int | str
SceneT = TypeVar("SceneT", bound=BaseData)
SequenceT = TypeVar("SequenceT", int, str)
ADVIO_LOCAL_FIRST_POSE_TRAJECTORY_CONVENTION = "local_first_pose_rdf_v1"
ADVIO_FIXEDPOINT_COMMON_START_TRAJECTORY_CONVENTION = "fixedpoint_common_start_local_rdf_v1"


class DatasetId(StrEnum):
    """Datasets exposed through evaluation surfaces."""

    ADVIO = "advio"
    RECORD3D = "record3d"
    TUM_RGBD = "tum_rgbd"

    @property
    def label(self) -> str:
        """Return the short user-facing dataset label."""
        return {self.ADVIO: "ADVIO", self.RECORD3D: "Record3D", self.TUM_RGBD: "TUM RGB-D"}[self]


class AdvioPoseSource(StrEnum):
    """ADVIO trajectory providers surfaced through replay and pipeline contracts."""

    GROUND_TRUTH = "ground_truth"
    ARCORE = "arcore"
    ARKIT = "arkit"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            self.GROUND_TRUTH: "Ground Truth",
            self.ARCORE: "ARCore",
            self.ARKIT: "ARKit",
            self.NONE: "No Pose Overlay",
        }[self]

    @property
    def is_real_provider(self) -> bool:
        return self is not self.NONE


class AdvioPoseFrameMode(StrEnum):
    """Coordinate-frame semantics for served ADVIO trajectories."""

    PROVIDER_WORLD = "provider_world"
    LOCAL_FIRST_POSE = "local_first_pose"
    FIXEDPOINT_COMMON_START_LOCAL = "fixedpoint_common_start_local"

    @property
    def label(self) -> str:
        return {
            self.PROVIDER_WORLD: "Provider World",
            self.LOCAL_FIRST_POSE: "Local First Pose",
            self.FIXEDPOINT_COMMON_START_LOCAL: "ADVIO Fixedpoint Common Start Local",
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
        return max(1, int(math.ceil(native_fps / self.target_fps))) if native_fps > 0.0 else 1

    def stride_for_timestamps_s(self, timestamps_s: Sequence[float]) -> int:
        return self.stride_for_timestamps_ns([int(round(value * 1e9)) for value in timestamps_s])


class ReferenceCloudConfig(BaseConfig):
    """Source-prepared RGB-D reference-cloud sampling policy."""

    depth_stride_px: int = Field(default=8, ge=1)
    max_points: int = Field(default=100_000, ge=1)
    random_seed: int = 17
    min_confidence: int | None = Field(default=None, ge=0, le=255)


class DatasetDownloadResult(BaseData, Generic[SequenceT]):
    """Summary of one explicit dataset download action."""

    sequence_ids: list[SequenceT]
    downloaded_archive_count: int = 0
    reused_archive_count: int = 0
    written_path_count: int = 0


class LocalSceneStatus(BaseData, Generic[SceneT]):
    """Local availability summary for one dataset scene."""

    scene: SceneT
    sequence_dir: Path | None = None
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
    dataset_serving: AdvioServingConfig | None,
    *,
    default: AdvioPoseSource = AdvioPoseSource.GROUND_TRUTH,
) -> AdvioPoseSource:
    """Return the effective ADVIO provider for one optional serving config."""
    return default if dataset_serving is None else dataset_serving.pose_source
