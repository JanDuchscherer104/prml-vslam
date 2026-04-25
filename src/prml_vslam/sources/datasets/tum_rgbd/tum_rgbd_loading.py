from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import load_tum_trajectory


class TumRgbdFrameAssociation(BaseData):
    rgb_timestamp_s: float
    rgb_path: Path
    depth_timestamp_s: float | None = None
    depth_path: Path | None = None
    pose_timestamp_s: float | None = None
    pose_index: int | None = None


class TumRgbdOfflineSample(BaseData):
    model_config = {"arbitrary_types_allowed": True}

    sequence_id: str
    sequence_name: str
    paths: object
    associations: list[TumRgbdFrameAssociation]
    intrinsics: CameraIntrinsics
    ground_truth: PoseTrajectory3D

    @property
    def frame_timestamps_ns(self) -> NDArray[np.int64]:
        return np.asarray([round(item.rgb_timestamp_s * 1e9) for item in self.associations], dtype=np.int64)

    @property
    def duration_s(self) -> float:
        timestamps = self.frame_timestamps_ns
        return 0.0 if timestamps.size < 2 else float((timestamps[-1] - timestamps[0]) / 1e9)


def load_tum_rgbd_list(path: Path) -> list[tuple[float, Path]]:
    rows: list[tuple[float, Path]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        if len(fields) < 2:
            raise ValueError(f"Invalid TUM RGB-D list row in {path}: {line!r}")
        rows.append((float(fields[0]), Path(fields[1])))
    if not rows:
        raise ValueError(f"TUM RGB-D list file '{path}' does not contain any rows.")
    return rows


def load_tum_rgbd_ground_truth(path: Path) -> PoseTrajectory3D:
    return load_tum_trajectory(path)


def load_tum_rgbd_associations(
    sequence_dir: Path,
    *,
    max_delta_s: float = 0.02,
) -> list[TumRgbdFrameAssociation]:
    rgb_rows = load_tum_rgbd_list(sequence_dir / "rgb.txt")
    depth_rows = load_tum_rgbd_list(sequence_dir / "depth.txt") if (sequence_dir / "depth.txt").exists() else []
    pose_path = resolve_ground_truth_path(sequence_dir)
    pose_trajectory = load_tum_rgbd_ground_truth(pose_path)
    pose_timestamps = np.asarray(pose_trajectory.timestamps, dtype=np.float64)
    depth_timestamps = np.asarray([timestamp for timestamp, _ in depth_rows], dtype=np.float64)

    associations: list[TumRgbdFrameAssociation] = []
    for rgb_timestamp_s, rgb_relative_path in rgb_rows:
        depth_index = _nearest_index(depth_timestamps, rgb_timestamp_s)
        pose_index = _nearest_index(pose_timestamps, rgb_timestamp_s)
        if pose_index is None:
            continue
        pose_timestamp_s = float(pose_timestamps[pose_index])
        if abs(pose_timestamp_s - rgb_timestamp_s) >= max_delta_s:
            continue
        depth_timestamp_s = None
        depth_path = None
        if depth_index is not None:
            candidate_depth_timestamp_s = float(depth_timestamps[depth_index])
            if abs(candidate_depth_timestamp_s - rgb_timestamp_s) < max_delta_s:
                depth_timestamp_s = candidate_depth_timestamp_s
                depth_path = sequence_dir / depth_rows[depth_index][1]
        associations.append(
            TumRgbdFrameAssociation(
                rgb_timestamp_s=rgb_timestamp_s,
                rgb_path=sequence_dir / rgb_relative_path,
                depth_timestamp_s=depth_timestamp_s,
                depth_path=depth_path,
                pose_timestamp_s=pose_timestamp_s,
                pose_index=int(pose_index),
            )
        )
    if not associations:
        raise ValueError(f"No RGB/pose associations were found under '{sequence_dir}'.")
    return associations


def load_tum_rgbd_intrinsics(sequence_id: str, sequence_dir: Path | None = None) -> CameraIntrinsics:
    if sequence_dir is not None and (sequence_dir / "intrinsics.txt").exists():
        values = _load_intrinsics_txt(sequence_dir / "intrinsics.txt")
        return CameraIntrinsics.from_matrix(values, width_px=640, height_px=480)
    if "freiburg1" in sequence_id:
        return CameraIntrinsics(
            fx=517.3,
            fy=516.5,
            cx=318.6,
            cy=255.3,
            width_px=640,
            height_px=480,
            distortion_model="radial-tangential",
            distortion_coefficients=(0.2624, -0.9531, -0.0054, 0.0026, 1.1633),
        )
    if "freiburg2" in sequence_id:
        return CameraIntrinsics(
            fx=520.9,
            fy=521.0,
            cx=325.1,
            cy=249.7,
            width_px=640,
            height_px=480,
            distortion_model="radial-tangential",
            distortion_coefficients=(0.2312, -0.7849, -0.0033, -0.0001, 0.9172),
        )
    if "freiburg3" in sequence_id:
        return CameraIntrinsics(
            fx=535.4,
            fy=539.2,
            cx=320.1,
            cy=247.6,
            width_px=640,
            height_px=480,
        )
    raise ValueError(f"Cannot infer TUM RGB-D intrinsics for sequence '{sequence_id}'.")


def ensure_tum_rgbd_intrinsics_yaml(sequence_id: str, sequence_dir: Path, target_path: Path | None = None) -> Path:
    intrinsics = load_tum_rgbd_intrinsics(sequence_id, sequence_dir)
    path = target_path or sequence_dir / "intrinsics.yaml"
    if path.exists():
        return path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    distortion = ", ".join(f"{value:.8g}" for value in intrinsics.distortion_coefficients)
    rows = [
        "cameras:",
        "- camera:",
        f"    image_height: {intrinsics.height_px or 480}",
        f"    image_width: {intrinsics.width_px or 640}",
        "    type: pinhole",
        "    intrinsics:",
        f"      data: [{intrinsics.fx:.8g}, {intrinsics.fy:.8g}, {intrinsics.cx:.8g}, {intrinsics.cy:.8g}]",
        "    distortion:",
        f"      type: {intrinsics.distortion_model or 'none'}",
        "      parameters:",
        f"        data: [{distortion}]",
        "    T_cam_imu:",
        "      data:",
        "      - [1.0, 0.0, 0.0, 0.0]",
        "      - [0.0, 1.0, 0.0, 0.0]",
        "      - [0.0, 0.0, 1.0, 0.0]",
        "      - [0.0, 0.0, 0.0, 1.0]",
    ]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path.resolve()


def ensure_ground_truth_tum(sequence_dir: Path, target_path: Path) -> Path:
    if target_path.exists():
        return target_path.resolve()
    source_path = resolve_ground_truth_path(sequence_dir)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    return target_path.resolve()


def resolve_ground_truth_path(sequence_dir: Path) -> Path:
    for candidate in (sequence_dir / "groundtruth.txt", sequence_dir / "pose.txt"):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"TUM RGB-D ground-truth file is missing under {sequence_dir}")


def load_depth_image_m(path: Path) -> NDArray[np.float32]:
    depth = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if depth is None:
        raise FileNotFoundError(f"Cannot read TUM RGB-D depth image: {path}")
    return (np.asarray(depth, dtype=np.float32) / 5000.0).astype(np.float32, copy=False)


def _nearest_index(values: NDArray[np.float64], target: float) -> int | None:
    if values.size == 0:
        return None
    return int(np.argmin(np.abs(values - target)))


def _load_intrinsics_txt(path: Path) -> NDArray[np.float64]:
    values = [float(field) for field in path.read_text(encoding="utf-8").split()]
    if len(values) == 4:
        fx, fy, cx, cy = values
        return np.asarray([[fx, 0.0, cx], [0.0, fy, cy], [0.0, 0.0, 1.0]], dtype=np.float64)
    if len(values) == 9:
        return np.asarray(values, dtype=np.float64).reshape(3, 3)
    raise ValueError(f"Expected 4 or 9 intrinsics values in '{path}', got {len(values)}.")
