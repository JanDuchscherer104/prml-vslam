"""Sim(3) Umeyama trajectory alignment helpers."""

from __future__ import annotations

import copy
import math

import numpy as np
from evo.core.trajectory import PoseTrajectory3D

from prml_vslam.align.trajectory_sim3.contracts import TrajectoryAlignmentArtifact
from prml_vslam.utils.geometry import apply_similarity_to_trajectory, yaw_similarity_align

# Down-axis for the RDF camera convention; ADVIO worlds are gravity-aligned about this axis.
_RDF_DOWN_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)


def is_gravity_aligned_target(target_frame: str) -> bool:
    """Whether the benchmark target frame is gravity-aligned (up == RDF -Y).

    ADVIO provider worlds derive from Apple Y-up, so RDF ``-Y`` is gravity. The
    TUM first-camera RDF frame is *not* gravity-aligned, so it keeps full Umeyama.
    """
    return target_frame.startswith("advio_") and target_frame.endswith("_world")


__all__ = [
    "align_estimate_sim3",
    "sim3_up_axis_tilt_deg",
    "trajectory_supports_sim3",
]


def trajectory_supports_sim3(reference: PoseTrajectory3D, estimate: PoseTrajectory3D) -> bool:
    """Return True when both trajectories have enough geometric spread for Sim(3) alignment."""
    if len(reference.positions_xyz) < 3 or len(estimate.positions_xyz) < 3:
        return False
    reference_centered = np.asarray(reference.positions_xyz, dtype=np.float64) - np.mean(
        reference.positions_xyz,
        axis=0,
    )
    estimate_centered = np.asarray(estimate.positions_xyz, dtype=np.float64) - np.mean(
        estimate.positions_xyz,
        axis=0,
    )
    return np.linalg.matrix_rank(reference_centered) >= 2 and np.linalg.matrix_rank(estimate_centered) >= 2


def align_estimate_sim3(
    *,
    reference: PoseTrajectory3D,
    estimate: PoseTrajectory3D,
    max_diff_s: float,
    target_frame: str = "world",
    source_frame: str = "slam_world",
    reference_source: str = "reference",
    method_id: str | None = None,
    method_label: str | None = None,
) -> tuple[PoseTrajectory3D, TrajectoryAlignmentArtifact]:
    """Align *estimate* to *reference* via Sim(3) and return the aligned trajectory and artifact."""
    if is_gravity_aligned_target(target_frame):
        # Gravity-aligned benchmark worlds (e.g. ADVIO) are near-planar; full
        # Umeyama can return an up/down-flipped rotation. Lock rotation to yaw
        # about the RDF gravity axis so the cloud overlay cannot flip upside down.
        scale_value, rotation_matrix, translation_vector = yaw_similarity_align(
            np.asarray(estimate.positions_xyz, dtype=np.float64),
            np.asarray(reference.positions_xyz, dtype=np.float64),
            up_axis=_RDF_DOWN_AXIS,
            correct_scale=True,
        )
        aligned_estimate = apply_similarity_to_trajectory(
            estimate, scale=scale_value, rotation=rotation_matrix, translation=translation_vector
        )
        rotation, translation, scale = rotation_matrix, translation_vector, scale_value
    else:
        aligned_estimate = copy.deepcopy(estimate)
        rotation, translation, scale = aligned_estimate.align(reference, correct_scale=True)
    residual = np.asarray(reference.positions_xyz, dtype=np.float64) - np.asarray(
        aligned_estimate.positions_xyz,
        dtype=np.float64,
    )
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return aligned_estimate, TrajectoryAlignmentArtifact(
        source_frame=source_frame,
        target_frame=target_frame,
        scale=float(scale),
        rotation=np.asarray(rotation, dtype=np.float64).tolist(),
        translation=np.asarray(translation, dtype=np.float64).reshape(3).tolist(),
        matched_pairs=int(len(reference.positions_xyz)),
        rms_error_m=rms_error_m,
        reference_source=reference_source,
        sync_max_diff_s=max_diff_s,
        method_id=method_id,
        method_label=method_label,
    )


def sim3_up_axis_tilt_deg(rotation: np.ndarray) -> float | None:
    """Return the tilt angle in degrees between the transformed and original down-axis, or None."""
    if rotation.shape != (3, 3) or not np.all(np.isfinite(rotation)):
        return None
    transformed_down_axis = rotation @ _RDF_DOWN_AXIS
    norm = float(np.linalg.norm(transformed_down_axis))
    if norm <= 0.0 or not math.isfinite(norm):
        return None
    cos_angle = float(np.clip(np.dot(transformed_down_axis / norm, _RDF_DOWN_AXIS), -1.0, 1.0))
    return math.degrees(math.acos(cos_angle))
