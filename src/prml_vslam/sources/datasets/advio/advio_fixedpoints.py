"""ADVIO fixedpoint registration helpers.

The official ADVIO visualization registers provider trajectories to
``ground-truth/fixpoints.csv`` before overlaying them. This module keeps that
dataset-specific preprocessing next to the ADVIO adapter while leaving raw pose
loading unchanged.
"""

from __future__ import annotations

import math
from enum import StrEnum
from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray

from prml_vslam.interfaces import FrameTransform
from prml_vslam.sources.contracts import ReferenceSource
from prml_vslam.sources.datasets.contracts import AdvioPoseSource
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import apply_similarity_to_trajectory, yaw_similarity_align

from .advio_frames import basis_for_pose_source, rdf_basis_matrix
from .advio_loading import _read_numeric_csv

MIN_ADVIO_FIXEDPOINT_MATCHES = 6
MIN_ADVIO_COMMON_INTERVAL_S = 10.0
MIN_ADVIO_COMMON_INTERVAL_COVERAGE_RATIO = 0.95
MAX_ADVIO_FIXEDPOINT_GRAVITY_TILT_DEG = 15.0
ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME = "advio_fixedpoint_common_start_local"
ADVIO_GT_WORLD_RDF_FRAME = "advio_gt_world_rdf"
ADVIO_PROVIDER_WORLD_RDF_FRAMES = {
    ReferenceSource.GROUND_TRUTH: ADVIO_GT_WORLD_RDF_FRAME,
    ReferenceSource.ARCORE: "advio_arcore_world_rdf",
    ReferenceSource.ARKIT: "advio_arkit_world_rdf",
}
RDF_DOWN_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)


class AdvioFixedpointFitMode(StrEnum):
    """Rigid registration mode selected for one ADVIO provider trajectory."""

    FULL_SO3 = "full_so3"
    YAW_ONLY = "yaw_only"


class AdvioFixpointSet(BaseData):
    """ADVIO fixpoints converted to repository RDF coordinates."""

    path: Path
    timestamps_s: list[float]
    positions_xyz_rdf: list[list[float]]


class AdvioFixedpointRegistration(BaseData):
    """Static transform from one provider RDF world into the fixedpoint frame."""

    provider_source: str
    target_frame: str
    native_frame: str
    method: str
    fit_mode: AdvioFixedpointFitMode
    scale: float
    rotation: list[list[float]]
    translation: list[float]
    matched_fixpoints: int
    sync_policy: str
    rms_error_m: float
    max_error_m: float
    fixedpoint_horizontal_span_m: float
    gravity_tilt_deg: float
    fallback_used: bool
    max_rms_error_m: float
    max_error_threshold_m: float


def load_advio_fixpoints(path: Path) -> AdvioFixpointSet:
    """Load ADVIO fixpoints with upstream-compatible axis handling.

    Upstream visualization reads fixpoint rows as ``[t, col1, col3, col2]``.
    The resulting raw ADVIO positions are then converted through the same
    Apple-Y-up-to-RDF basis used for pose CSV trajectories.
    """
    rows = _read_numeric_csv(path, min_columns=4)
    if rows.size == 0:
        raise ValueError(f"ADVIO fixpoints '{path}' is empty.")
    upstream_raw = np.column_stack((rows[:, 0], rows[:, 1], rows[:, 3], rows[:, 2]))
    basis = rdf_basis_matrix(basis_for_pose_source(AdvioPoseSource.GROUND_TRUTH))
    positions_rdf = upstream_raw[:, 1:4].astype(np.float64, copy=False) @ basis.T
    return AdvioFixpointSet(
        path=path.resolve(),
        timestamps_s=upstream_raw[:, 0].astype(np.float64, copy=False).tolist(),
        positions_xyz_rdf=positions_rdf.tolist(),
    )


def estimate_advio_fixedpoint_registration(
    trajectory_rdf: PoseTrajectory3D,
    fixpoints_rdf: AdvioFixpointSet,
    *,
    provider_source: ReferenceSource,
    native_frame: str,
    target_frame: str = ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
) -> AdvioFixedpointRegistration:
    """Estimate a no-scale rigid transform from provider RDF world to fixpoints."""
    fix_timestamps = np.asarray(fixpoints_rdf.timestamps_s, dtype=np.float64)
    fix_positions = np.asarray(fixpoints_rdf.positions_xyz_rdf, dtype=np.float64)
    traj_timestamps = np.asarray(trajectory_rdf.timestamps, dtype=np.float64)
    inside = (fix_timestamps >= traj_timestamps[0]) & (fix_timestamps <= traj_timestamps[-1])
    matched_timestamps = fix_timestamps[inside]
    matched_fixpoints = fix_positions[inside]
    if len(matched_timestamps) < MIN_ADVIO_FIXEDPOINT_MATCHES:
        raise ValueError(
            f"ADVIO {provider_source.value} needs at least {MIN_ADVIO_FIXEDPOINT_MATCHES} fixedpoint matches, "
            f"got {len(matched_timestamps)}."
        )
    matched_trajectory = _interpolate_positions(trajectory_rdf, matched_timestamps)
    full_rotation, full_translation = _estimate_rigid_no_scale(
        target_xyz=matched_fixpoints,
        source_xyz=matched_trajectory,
    )
    full_tilt = _gravity_tilt_deg(full_rotation)
    if full_tilt <= MAX_ADVIO_FIXEDPOINT_GRAVITY_TILT_DEG:
        fit_mode = AdvioFixedpointFitMode.FULL_SO3
        rotation = full_rotation
        translation = full_translation
        fallback_used = False
        gravity_tilt = full_tilt
    else:
        _, rotation, translation = yaw_similarity_align(
            matched_trajectory,
            matched_fixpoints,
            up_axis=RDF_DOWN_AXIS,
            correct_scale=False,
        )
        fit_mode = AdvioFixedpointFitMode.YAW_ONLY
        fallback_used = True
        gravity_tilt = _gravity_tilt_deg(rotation)
    residual = matched_fixpoints - ((rotation @ matched_trajectory.T).T + translation)
    residual_norm = np.linalg.norm(residual, axis=1)
    rms_error = float(np.sqrt(np.mean(residual_norm**2)))
    max_error = float(np.max(residual_norm))
    horizontal_span = _horizontal_span_m(matched_fixpoints)
    max_rms_error = max(10.0, 0.15 * horizontal_span)
    max_error_threshold = max(25.0, 0.35 * horizontal_span)
    if rms_error > max_rms_error or max_error > max_error_threshold:
        raise ValueError(
            f"ADVIO {provider_source.value} fixedpoint registration residual is too large: "
            f"rms={rms_error:.3f}m (limit {max_rms_error:.3f}m), "
            f"max={max_error:.3f}m (limit {max_error_threshold:.3f}m)."
        )
    return AdvioFixedpointRegistration(
        provider_source=provider_source.value,
        target_frame=target_frame,
        native_frame=native_frame,
        method="advio_fixedpoint_rigid_no_scale",
        fit_mode=fit_mode,
        scale=1.0,
        rotation=rotation.tolist(),
        translation=translation.reshape(3).tolist(),
        matched_fixpoints=int(len(matched_timestamps)),
        sync_policy="linear_position_interpolation_at_fixpoint_timestamps",
        rms_error_m=rms_error,
        max_error_m=max_error,
        fixedpoint_horizontal_span_m=horizontal_span,
        gravity_tilt_deg=gravity_tilt,
        fallback_used=fallback_used,
        max_rms_error_m=max_rms_error,
        max_error_threshold_m=max_error_threshold,
    )


def apply_advio_fixedpoint_registration(
    trajectory_rdf: PoseTrajectory3D,
    registration: AdvioFixedpointRegistration,
) -> PoseTrajectory3D:
    """Apply one fixedpoint registration to a provider RDF trajectory."""
    return apply_similarity_to_trajectory(
        trajectory_rdf,
        scale=registration.scale,
        rotation=np.asarray(registration.rotation, dtype=np.float64),
        translation=np.asarray(registration.translation, dtype=np.float64),
    )


def advio_common_start_local_trajectories(
    registered_trajectories: dict[ReferenceSource, PoseTrajectory3D],
) -> tuple[dict[ReferenceSource, PoseTrajectory3D], dict[str, float | str | list[list[float]]]]:
    """Crop registered ADVIO trajectories and express them in one GT local frame."""
    if ReferenceSource.GROUND_TRUTH not in registered_trajectories:
        raise ValueError("ADVIO common-start normalization requires a registered ground-truth trajectory.")
    starts = [float(trajectory.timestamps[0]) for trajectory in registered_trajectories.values()]
    ends = [float(trajectory.timestamps[-1]) for trajectory in registered_trajectories.values()]
    common_start = max(starts)
    common_end = min(ends)
    common_duration = common_end - common_start
    shortest_duration = min(
        float(trajectory.timestamps[-1] - trajectory.timestamps[0]) for trajectory in registered_trajectories.values()
    )
    coverage_ratio = common_duration / shortest_duration if shortest_duration > 0.0 else 0.0
    requires_min_duration = shortest_duration >= MIN_ADVIO_COMMON_INTERVAL_S
    if (requires_min_duration and common_duration < MIN_ADVIO_COMMON_INTERVAL_S) or (
        coverage_ratio < MIN_ADVIO_COMMON_INTERVAL_COVERAGE_RATIO
    ):
        raise ValueError(
            "ADVIO common interval is too short for normalized publication: "
            f"duration={common_duration:.3f}s, coverage={coverage_ratio:.3f}."
        )
    ground_truth = registered_trajectories[ReferenceSource.GROUND_TRUTH]
    T_fixedpoint_gt_start = _pose_at_timestamp(ground_truth, common_start)
    T_common_fixedpoint = np.linalg.inv(T_fixedpoint_gt_start)
    normalized = {
        source: _transform_and_crop_trajectory(
            trajectory,
            T_target_source=T_common_fixedpoint,
            start_s=common_start,
            end_s=common_end,
        )
        for source, trajectory in registered_trajectories.items()
    }
    return normalized, {
        "common_start_s": float(common_start),
        "common_end_s": float(common_end),
        "common_duration_s": float(common_duration),
        "coverage_ratio": float(coverage_ratio),
        "anchor_source": ReferenceSource.GROUND_TRUTH.value,
        "T_common_local_fixedpoint": T_common_fixedpoint.tolist(),
    }


def _interpolate_positions(trajectory: PoseTrajectory3D, timestamps_s: NDArray[np.float64]) -> NDArray[np.float64]:
    trajectory_timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
    positions = np.asarray(trajectory.positions_xyz, dtype=np.float64)
    return np.stack(
        [np.interp(timestamps_s, trajectory_timestamps, positions[:, axis]) for axis in range(3)],
        axis=1,
    )


def _estimate_rigid_no_scale(
    *,
    target_xyz: NDArray[np.float64],
    source_xyz: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    target_centroid = target_xyz.mean(axis=0)
    source_centroid = source_xyz.mean(axis=0)
    target_centered = target_xyz - target_centroid
    source_centered = source_xyz - source_centroid
    u_matrix, _singular_values, vt_matrix = np.linalg.svd(source_centered.T @ target_centered)
    rotation = vt_matrix.T @ u_matrix.T
    if np.linalg.det(rotation) < 0.0:
        vt_matrix[-1] *= -1.0
        rotation = vt_matrix.T @ u_matrix.T
    translation = target_centroid - rotation @ source_centroid
    return rotation, translation


def _gravity_tilt_deg(rotation: NDArray[np.float64]) -> float:
    rotated_down = rotation @ RDF_DOWN_AXIS
    return math.degrees(math.acos(float(np.clip(rotated_down @ RDF_DOWN_AXIS, -1.0, 1.0))))


def _horizontal_span_m(points_xyz: NDArray[np.float64]) -> float:
    horizontal = points_xyz[:, [0, 2]]
    return float(np.linalg.norm(np.ptp(horizontal, axis=0)))


def _pose_at_timestamp(trajectory: PoseTrajectory3D, timestamp_s: float) -> NDArray[np.float64]:
    timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
    pose_index = int(np.clip(np.searchsorted(timestamps, timestamp_s), 0, len(timestamps) - 1))
    pose = np.asarray(trajectory.poses_se3[pose_index], dtype=np.float64).copy()
    pose[:3, 3] = _interpolate_positions(trajectory, np.asarray([timestamp_s], dtype=np.float64))[0]
    return pose


def _transform_and_crop_trajectory(
    trajectory: PoseTrajectory3D,
    *,
    T_target_source: NDArray[np.float64],
    start_s: float,
    end_s: float,
) -> PoseTrajectory3D:
    timestamps = np.asarray(trajectory.timestamps, dtype=np.float64)
    mask = (timestamps >= start_s) & (timestamps <= end_s)
    if not np.any(mask):
        raise ValueError("ADVIO common-start crop removed all poses.")
    poses = [
        T_target_source @ np.asarray(pose, dtype=np.float64)
        for pose, keep in zip(trajectory.poses_se3, mask, strict=True)
        if keep
    ]
    return PoseTrajectory3D(poses_se3=poses, timestamps=timestamps[mask])


def advio_frame_transform_from_pose(
    pose: NDArray[np.float64],
    *,
    target_frame: str = ADVIO_FIXEDPOINT_COMMON_START_LOCAL_FRAME,
) -> FrameTransform:
    """Build a frame-labelled camera pose from a matrix."""
    return FrameTransform.from_matrix(
        np.asarray(pose, dtype=np.float64), target_frame=target_frame, source_frame="camera_rdf"
    )
