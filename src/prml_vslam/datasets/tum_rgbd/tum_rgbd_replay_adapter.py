from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics, FramePacket, FramePacketProvenance, FrameTransform
from prml_vslam.io import Cv2ReplayMode
from prml_vslam.protocols import FramePacketStream

from .tum_rgbd_loading import (
    TumRgbdFrameAssociation,
    load_depth_image_m,
    load_tum_rgbd_associations,
    load_tum_rgbd_ground_truth,
    load_tum_rgbd_intrinsics,
    resolve_ground_truth_path,
)
from .tum_rgbd_models import TumRgbdPoseSource


class TumRgbdImageSequenceStream:
    def __init__(
        self,
        *,
        sequence_dir: Path,
        associations: list[TumRgbdFrameAssociation],
        intrinsics: CameraIntrinsics,
        trajectory: PoseTrajectory3D | None,
        stride: int,
        loop: bool,
        replay_mode: Cv2ReplayMode,
        include_depth: bool,
        provenance: FramePacketProvenance,
    ) -> None:
        self.sequence_dir = sequence_dir
        self.associations = associations
        self.intrinsics = intrinsics
        self.stride = stride
        self.loop = loop
        self.replay_mode = replay_mode
        self.include_depth = include_depth
        self.provenance = provenance
        self._frame_index = 0
        self._loop_index = 0
        self._stream_start_monotonic: float | None = None
        self._stream_start_timestamp_ns: int | None = None
        self._poses_by_frame = _poses_for_associations(associations, trajectory)

    def connect(self) -> Path:
        if not self.sequence_dir.is_dir():
            raise FileNotFoundError(f"TUM RGB-D sequence directory is missing: {self.sequence_dir}")
        self._frame_index = 0
        self._loop_index = 0
        self._stream_start_monotonic = None
        self._stream_start_timestamp_ns = None
        return self.sequence_dir

    def disconnect(self) -> None:
        return None

    def wait_for_packet(self, timeout_seconds: float | None = None) -> FramePacket:
        del timeout_seconds
        associations = self.associations
        while True:
            if self._frame_index >= len(associations):
                if not self.loop:
                    raise EOFError(f"Reached the end of {self.sequence_dir}")
                self._frame_index = 0
                self._loop_index += 1
                self._stream_start_monotonic = None
                self._stream_start_timestamp_ns = None
                continue
            source_frame_index = self._frame_index
            self._frame_index += 1
            if source_frame_index % self.stride != 0:
                continue
            association = associations[source_frame_index]
            timestamp_ns = int(round(association.rgb_timestamp_s * 1e9))
            self._apply_replay_timing(timestamp_ns)
            rgb = _load_rgb_image(association.rgb_path)
            depth = (
                load_depth_image_m(association.depth_path)
                if self.include_depth and association.depth_path is not None
                else None
            )
            return FramePacket(
                seq=source_frame_index,
                timestamp_ns=timestamp_ns,
                arrival_timestamp_s=time.time(),
                rgb=rgb,
                depth=depth,
                intrinsics=self.intrinsics,
                pose=self._poses_by_frame[source_frame_index],
                provenance=self.provenance.model_copy(
                    update={
                        "loop_index": self._loop_index,
                        "source_frame_index": source_frame_index,
                    }
                ),
            )

    def _apply_replay_timing(self, timestamp_ns: int) -> None:
        if self.replay_mode is not Cv2ReplayMode.REALTIME:
            return
        if self._stream_start_timestamp_ns is None:
            self._stream_start_timestamp_ns = timestamp_ns
            self._stream_start_monotonic = time.monotonic()
            return
        if self._stream_start_monotonic is None:
            return
        target_elapsed_s = max(timestamp_ns - self._stream_start_timestamp_ns, 0) / 1e9
        actual_elapsed_s = time.monotonic() - self._stream_start_monotonic
        sleep_seconds = target_elapsed_s - actual_elapsed_s
        if sleep_seconds > 0.0:
            time.sleep(sleep_seconds)


def open_tum_rgbd_stream(
    sequence_id: str,
    sequence_dir: Path,
    *,
    pose_source: TumRgbdPoseSource = TumRgbdPoseSource.GROUND_TRUTH,
    stride: int = 1,
    loop: bool = True,
    replay_mode: Cv2ReplayMode = Cv2ReplayMode.REALTIME,
    include_depth: bool = True,
) -> FramePacketStream:
    associations = load_tum_rgbd_associations(sequence_dir)
    trajectory = (
        None
        if pose_source is TumRgbdPoseSource.NONE
        else load_tum_rgbd_ground_truth(resolve_ground_truth_path(sequence_dir))
    )
    return TumRgbdImageSequenceStream(
        sequence_dir=sequence_dir,
        associations=associations,
        intrinsics=load_tum_rgbd_intrinsics(sequence_id, sequence_dir),
        trajectory=trajectory,
        stride=stride,
        loop=loop,
        replay_mode=replay_mode,
        include_depth=include_depth,
        provenance=FramePacketProvenance(
            dataset_id="tum_rgbd",
            sequence_id=sequence_id,
            sequence_name=sequence_id,
            pose_source=pose_source.value,
        ),
    )


def _poses_for_associations(
    associations: list[TumRgbdFrameAssociation],
    trajectory: PoseTrajectory3D | None,
) -> list[FrameTransform | None]:
    if trajectory is None:
        return [None] * len(associations)
    return [
        None
        if association.pose_index is None
        else FrameTransform.from_matrix(np.asarray(trajectory.poses_se3[association.pose_index], dtype=np.float64))
        for association in associations
    ]


def _load_rgb_image(path: Path) -> NDArray[np.uint8]:
    frame_bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if frame_bgr is None:
        raise FileNotFoundError(f"Cannot read TUM RGB-D RGB image: {path}")
    return np.asarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)
