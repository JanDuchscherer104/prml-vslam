from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from evo.core.trajectory import PoseTrajectory3D
from evo.tools import file_interface
from numpy.typing import NDArray

from prml_vslam.interfaces import CameraIntrinsics
from prml_vslam.utils import BaseData

_CSV_FLOAT_PATTERN = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
_NUMERIC_CSV_ROW_PATTERN = re.compile(
    rf"^\s*({_CSV_FLOAT_PATTERN}(?:\s*,\s*{_CSV_FLOAT_PATTERN})*)\s*$",
    flags=re.MULTILINE,
)


class AdvioCalibration(BaseData):
    calibration_path: Path
    intrinsics: CameraIntrinsics
    t_cam_imu: NDArray[np.float64]


def load_advio_frame_timestamps_ns(path: Path) -> NDArray[np.int64]:
    """Load exact iPhone frame timestamps from `frames.csv` as nanoseconds."""
    rows = _read_numeric_csv(path, min_columns=1)
    if rows.size == 0:
        return np.empty(0, dtype=np.int64)
    return np.rint(rows[:, 0] * 1e9).astype(np.int64, copy=False)


def load_advio_trajectory(path: Path) -> PoseTrajectory3D:
    """Load an ADVIO trajectory CSV into an `evo` pose trajectory."""
    rows = _read_numeric_csv(path, min_columns=8)
    if rows.ndim != 2 or rows.shape[1] < 8:
        msg = f"Expected at least 8 columns in ADVIO pose CSV: {path}"
        raise ValueError(msg)
    trajectory = PoseTrajectory3D(
        positions_xyz=rows[:, 1:4].astype(np.float64, copy=True),
        orientations_quat_wxyz=rows[:, 4:8].astype(np.float64, copy=True),
        timestamps=rows[:, 0].astype(np.float64, copy=True),
    )
    valid, details = trajectory.check()
    if not valid:
        raise ValueError(f"Invalid ADVIO trajectory '{path}': {details}")
    return trajectory


def load_advio_calibration(path: Path) -> AdvioCalibration:
    """Parse an official ADVIO calibration YAML into a typed camera model."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected a YAML mapping in {path}"
        raise ValueError(msg)
    camera = _extract_camera_mapping(payload, calibration_path=path)
    intrinsics = _expect_float_list(camera, "intrinsics", "data", expected_len=4)
    distortion = _expect_mapping(camera, "distortion")
    return AdvioCalibration(
        calibration_path=path,
        intrinsics=CameraIntrinsics(
            fx=intrinsics[0],
            fy=intrinsics[1],
            cx=intrinsics[2],
            cy=intrinsics[3],
            width_px=int(camera["image_width"]),
            height_px=int(camera["image_height"]),
            distortion_model=str(distortion.get("type")) if distortion.get("type") is not None else None,
            distortion_coefficients=tuple(_expect_float_list(distortion, "parameters", "data")),
        ),
        t_cam_imu=np.asarray(_expect_matrix(camera, "T_cam_imu"), dtype=np.float64),
    )


def write_advio_pose_tum(source_path: Path, target_path: Path) -> Path:
    """Convert an ADVIO pose CSV into a TUM trajectory file."""
    trajectory = load_advio_trajectory(source_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    file_interface.write_tum_trajectory_file(target_path, trajectory)
    return target_path.resolve()


def _read_numeric_csv(path: Path, *, min_columns: int) -> NDArray[np.float64]:
    row_strings = np.asarray(_NUMERIC_CSV_ROW_PATTERN.findall(path.read_text(encoding="utf-8")), dtype=str)
    if row_strings.size == 0:
        return np.empty((0, 0), dtype=np.float64)

    column_counts = np.char.count(row_strings, ",").astype(np.int64) + 1
    min_count = int(column_counts.min())
    if min_count < min_columns:
        msg = f"Expected at least {min_columns} columns in {path}, got {min_count}"
        raise ValueError(msg)
    first_count = int(column_counts[0])
    if np.any(column_counts != first_count):
        msg = f"Expected a rectangular numeric CSV in {path}"
        raise ValueError(msg)
    numeric_text = "\n".join(row_strings.tolist()).replace(",", " ")
    return np.fromstring(numeric_text, sep=" ", dtype=np.float64).reshape(-1, first_count)


def _extract_camera_mapping(payload: dict[str, Any], *, calibration_path: Path) -> dict[str, Any]:
    cameras = payload.get("cameras")
    if not isinstance(cameras, list) or not cameras:
        msg = f"Expected a non-empty `cameras` list in {calibration_path}"
        raise ValueError(msg)
    camera_entry = cameras[0]
    if not isinstance(camera_entry, dict):
        msg = f"Expected a mapping camera entry in {calibration_path}"
        raise ValueError(msg)
    camera = camera_entry.get("camera")
    if not isinstance(camera, dict):
        msg = f"Expected a `camera` mapping in {calibration_path}"
        raise ValueError(msg)
    return camera


def _expect_mapping(mapping: dict[str, Any], key: str) -> dict[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, dict):
        msg = f"Expected `{key}` to be a mapping"
        raise ValueError(msg)
    return value


def _expect_float_list(
    mapping: dict[str, Any],
    key: str,
    nested_key: str,
    *,
    expected_len: int | None = None,
) -> list[float]:
    values = _expect_mapping(mapping, key).get(nested_key)
    if not isinstance(values, list):
        msg = f"Expected `{key}.{nested_key}` to be a list"
        raise ValueError(msg)
    floats = [float(value) for value in values]
    if expected_len is not None and len(floats) != expected_len:
        msg = f"Expected `{key}.{nested_key}` to have length {expected_len}, got {len(floats)}"
        raise ValueError(msg)
    return floats


def _expect_matrix(mapping: dict[str, Any], key: str) -> list[list[float]]:
    rows = _expect_mapping(mapping, key).get("data")
    if not isinstance(rows, list) or len(rows) != 4:
        msg = f"Expected `{key}.data` to be a 4x4 matrix"
        raise ValueError(msg)
    matrix: list[list[float]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) != 4:
            msg = f"Expected `{key}.data` to be a 4x4 matrix"
            raise ValueError(msg)
        matrix.append([float(value) for value in row])
    return matrix
