"""Record3D `.r3d` archive parsing and materialization helpers."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.camera import scale_camera_intrinsics
from prml_vslam.utils import BaseData

from .record3d_models import Record3DPoseFrameMode


class Record3DArchiveFrame(BaseData):
    """One RGB-D frame triplet inside a `.r3d` archive."""

    index: int
    jpg_name: str
    depth_name: str
    confidence_name: str


class Record3DArchiveMetadata(BaseData):
    """Validated subset of Record3D metadata used by the adapter."""

    K: list[float]
    w: int
    h: int
    dw: int
    dh: int
    fps: float
    frameTimestamps: list[float]
    poses: list[list[float]]


class Record3DOfflineSample(BaseData):
    """Decoded archive-level metadata for one Record3D sequence."""

    model_config = {"arbitrary_types_allowed": True}

    sequence_id: str
    sequence_name: str
    archive_path: Path
    metadata: Record3DArchiveMetadata
    frames: list[Record3DArchiveFrame]
    rgb_intrinsics: CameraIntrinsics
    depth_intrinsics: CameraIntrinsics
    timestamps_ns: list[int]
    poses_world_camera: list[FrameTransform]

    @property
    def frame_timestamps_ns(self) -> NDArray[np.int64]:
        return np.asarray(self.timestamps_ns, dtype=np.int64)

    @property
    def duration_s(self) -> float:
        timestamps = self.frame_timestamps_ns
        return 0.0 if timestamps.size < 2 else float((timestamps[-1] - timestamps[0]) / 1e9)


def read_archive_metadata(archive_path: Path) -> Record3DArchiveMetadata:
    """Read and validate the Record3D archive metadata JSON."""
    with zipfile.ZipFile(archive_path) as archive:
        payload = json.loads(archive.read("metadata").decode("utf-8"))
    return Record3DArchiveMetadata.model_validate(payload)


def index_archive_frames(archive_path: Path, metadata: Record3DArchiveMetadata) -> list[Record3DArchiveFrame]:
    """Return ordered RGB-D frame triplets from an `.r3d` archive."""
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())
    jpg_by_index = _names_by_index(names, ".jpg")
    depth_by_index = _names_by_index(names, ".depth")
    conf_by_index = _names_by_index(names, ".conf")
    indices = sorted(set(jpg_by_index) & set(depth_by_index) & set(conf_by_index))
    expected_count = len(metadata.frameTimestamps)
    if len(indices) != expected_count or len(metadata.poses) != expected_count:
        raise ValueError(
            f"Record3D archive frame count mismatch: {len(indices)} RGB-D triplets, "
            f"{len(metadata.frameTimestamps)} timestamps, {len(metadata.poses)} poses."
        )
    if indices != list(range(expected_count)):
        raise ValueError(
            "Record3D archive frames must be consecutively numbered from 0 "
            f"to {expected_count - 1}; found {indices[:5]}..."
        )
    return [
        Record3DArchiveFrame(
            index=index,
            jpg_name=jpg_by_index[index],
            depth_name=depth_by_index[index],
            confidence_name=conf_by_index[index],
        )
        for index in indices
    ]


def build_rgb_intrinsics(metadata: Record3DArchiveMetadata) -> CameraIntrinsics:
    """Parse the Record3D column-major K matrix for the RGB raster."""
    return CameraIntrinsics.from_column_major_flat_k(metadata.K, width_px=metadata.w, height_px=metadata.h)


def build_depth_intrinsics(rgb_intrinsics: CameraIntrinsics, metadata: Record3DArchiveMetadata) -> CameraIntrinsics:
    """Scale RGB intrinsics into the depth raster used by `.depth` payloads."""
    return scale_camera_intrinsics(
        rgb_intrinsics,
        scale_x=metadata.dw / metadata.w,
        scale_y=metadata.dh / metadata.h,
        width_px=metadata.dw,
        height_px=metadata.dh,
    )


def timestamps_ns_from_metadata(metadata: Record3DArchiveMetadata) -> list[int]:
    """Convert Record3D floating second timestamps into nanoseconds."""
    return [int(round(float(value) * 1e9)) for value in metadata.frameTimestamps]


def poses_from_metadata(
    metadata: Record3DArchiveMetadata, *, pose_frame_mode: Record3DPoseFrameMode
) -> list[FrameTransform]:
    """Convert Record3D pose rows into frame-labelled transforms."""
    return [pose_from_metadata_row(row, pose_frame_mode=pose_frame_mode) for row in metadata.poses]


def pose_from_metadata_row(row: Sequence[float], *, pose_frame_mode: Record3DPoseFrameMode) -> FrameTransform:
    """Convert one `[qx, qy, qz, qw, tx, ty, tz]` metadata pose row."""
    if len(row) != 7:
        raise ValueError(f"Expected Record3D pose row with 7 values, got {len(row)}.")
    transform = FrameTransform.from_quaternion_translation(
        np.asarray(row[:4], dtype=np.float64),
        np.asarray(row[4:], dtype=np.float64),
        target_frame="record3d_world",
        source_frame="camera_rdf",
    )
    if pose_frame_mode is Record3DPoseFrameMode.METADATA:
        return transform
    pose_matrix = transform.as_matrix()
    flip = np.diag([1.0, -1.0, -1.0, 1.0])
    return FrameTransform.from_matrix(
        flip @ pose_matrix @ flip, target_frame="record3d_world", source_frame="camera_rdf"
    )


def decode_rgb_frame(archive_path: Path, frame: Record3DArchiveFrame) -> NDArray[np.uint8]:
    """Decode one RGB frame from an archive into RGB channel order."""
    with zipfile.ZipFile(archive_path) as archive:
        payload = np.frombuffer(archive.read(frame.jpg_name), dtype=np.uint8)
    image_bgr = cv2.imdecode(payload, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise ValueError(f"Cannot decode Record3D RGB payload: {frame.jpg_name}")
    return np.asarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB), dtype=np.uint8)


def decode_depth_frame_m(
    archive_path: Path,
    frame: Record3DArchiveFrame,
    metadata: Record3DArchiveMetadata,
    *,
    depth_unit_scale: float = 1.0,
) -> NDArray[np.float32]:
    """Decode one LZFSE-compressed depth payload into meters."""
    with zipfile.ZipFile(archive_path) as archive:
        payload = archive.read(frame.depth_name)
    decompressed = _load_liblzfse().decompress(payload)
    depth = np.frombuffer(decompressed, dtype=np.float32)
    expected = metadata.dh * metadata.dw
    if depth.size != expected:
        raise ValueError(f"Expected {expected} depth values in {frame.depth_name}, got {depth.size}.")
    return (depth.reshape((metadata.dh, metadata.dw)) * depth_unit_scale).astype(np.float32, copy=False)


def decode_confidence_frame(
    archive_path: Path,
    frame: Record3DArchiveFrame,
    metadata: Record3DArchiveMetadata,
) -> NDArray[np.uint8]:
    """Decode one LZFSE-compressed confidence payload."""
    with zipfile.ZipFile(archive_path) as archive:
        payload = archive.read(frame.confidence_name)
    decompressed = _load_liblzfse().decompress(payload)
    confidence = np.frombuffer(decompressed, dtype=np.uint8)
    expected = metadata.dh * metadata.dw
    if confidence.size != expected:
        raise ValueError(f"Expected {expected} confidence values in {frame.confidence_name}, got {confidence.size}.")
    return confidence.reshape((metadata.dh, metadata.dw))


def write_timestamps_json(timestamps_ns: Sequence[int], target_path: Path) -> Path:
    """Write normalized timestamp JSON for materialized RGB frames."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(
        json.dumps({"timestamps_ns": [int(value) for value in timestamps_ns]}, indent=2), encoding="utf-8"
    )
    return target_path.resolve()


def resize_rgb_to_depth(rgb: NDArray[np.uint8], metadata: Record3DArchiveMetadata) -> NDArray[np.uint8]:
    """Resize an RGB frame into the depth raster dimensions."""
    resized = cv2.resize(rgb, (metadata.dw, metadata.dh), interpolation=cv2.INTER_AREA)
    return np.asarray(resized, dtype=np.uint8)


def _names_by_index(names: set[str], suffix: str) -> dict[int, str]:
    result: dict[int, str] = {}
    for name in names:
        if not name.endswith(suffix):
            continue
        stem = Path(name).stem
        try:
            result[int(stem)] = name
        except ValueError:
            continue
    return result


def _load_liblzfse() -> Any:
    try:
        import liblzfse
    except ImportError as exc:
        raise RuntimeError(
            "Record3D `.r3d` depth/confidence decoding requires `pyliblzfse`. "
            "Install the project dependencies or run `uv sync` in the helper-managed environment."
        ) from exc
    return liblzfse
