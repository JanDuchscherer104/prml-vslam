from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray
from pytransform3d.transformations import transform, vectors_to_points

from prml_vslam.datasets.contracts import AdvioPoseSource
from prml_vslam.interfaces import FrameTransform
from prml_vslam.interfaces.transforms import project_rotation_to_so3
from prml_vslam.sources.contracts import ReferenceCloudCoordinateStatus, ReferenceCloudRef, ReferenceCloudSource
from prml_vslam.utils import BaseData, Console
from prml_vslam.utils.geometry import write_point_cloud_ply

from .advio_frames import (
    AdvioRawCoordinateBasis,
    advio_basis_metadata,
    transform_advio_points_to_rdf,
    transform_advio_trajectory_to_rdf,
)
from .advio_loading import load_advio_trajectory

_DEFAULT_MAX_REFERENCE_POINTS = 200_000
_DEFAULT_POINT_STRIDE = 1
_ALIGNMENT_MAX_DIFF_S = 0.02
_MIN_ALIGNMENT_PAIRS = 3
_GT_WORLD_FRAME = "advio_gt_world"
_RDF_HORIZONTAL_AXES = (0, 2)
_CONSOLE = Console(__name__).child("tango_reference_clouds")
_JsonAlignmentValue = str | int | float | bool | None | list[float] | list[list[float]]


class TangoCloudMetadata(BaseData):
    """Side metadata for one materialized ADVIO Tango reference cloud."""

    dataset: str = "ADVIO"
    sequence_id: str
    source: ReferenceCloudSource
    coordinate_status: ReferenceCloudCoordinateStatus
    target_frame: str
    native_frame: str
    payload_frame: str = "tango_depth_sensor"
    source_world_frame: str
    raw_coordinate_basis: AdvioRawCoordinateBasis
    rdf_basis_transform: list[list[float]]
    per_payload_pose_applied: bool = True
    units: str = "meters"
    point_count: int
    timestamp_min_s: float | None
    timestamp_max_s: float | None
    point_cloud_count: int
    payloads_used: int
    skipped_out_of_range_payloads: int = 0
    point_stride: int
    max_reference_points: int
    alignment: dict[str, _JsonAlignmentValue] | None = None


class Sim3Alignment(BaseData):
    """Stored trajectory alignment mapping source-frame positions into target-frame positions."""

    source_frame: str
    target_frame: str
    alignment_type: Literal["sim3", "planar_rigid"] = "sim3"
    scale: float
    rotation: list[list[float]]
    translation: list[float]
    matched_pairs: int
    rms_error_m: float


def build_advio_tango_reference_clouds(
    *,
    sequence_slug: str,
    ground_truth_csv_path: Path,
    tango_raw_csv_path: Path | None,
    tango_area_learning_csv_path: Path | None,
    tango_point_cloud_index_path: Path | None,
    output_dir: Path,
    max_reference_points: int = _DEFAULT_MAX_REFERENCE_POINTS,
    point_stride: int = _DEFAULT_POINT_STRIDE,
) -> list[ReferenceCloudRef]:
    """Materialize ADVIO Tango source-native and GT-world reference cloud artifacts."""
    del tango_raw_csv_path
    if tango_point_cloud_index_path is None or not tango_point_cloud_index_path.exists():
        return []
    index_rows = load_tango_point_cloud_index(tango_point_cloud_index_path)
    if index_rows.size == 0:
        return []

    ground_truth = transform_advio_trajectory_to_rdf(
        load_advio_trajectory(ground_truth_csv_path),
        source=AdvioPoseSource.GROUND_TRUTH,
    )
    refs: list[ReferenceCloudRef] = []
    source_specs = ((ReferenceCloudSource.TANGO_AREA_LEARNING, tango_area_learning_csv_path),)
    for source, trajectory_path in source_specs:
        if trajectory_path is None or not trajectory_path.exists():
            continue
        native_frame = f"advio_{source.value}_world"
        payload_frame = f"advio_{source.value}_depth_sensor"
        try:
            source_trajectory = transform_advio_trajectory_to_rdf(load_advio_trajectory(trajectory_path), source=source)
            points_xyz_source, payloads_used, skipped_out_of_range_payloads = load_bounded_tango_point_clouds(
                index_path=tango_point_cloud_index_path,
                trajectory=source_trajectory,
                max_reference_points=max_reference_points,
                point_stride=point_stride,
                target_frame=native_frame,
                source_frame=payload_frame,
                point_source=source,
            )
        except ValueError as exc:
            _CONSOLE.warning(
                "Skipping invalid optional ADVIO %s reference cloud trajectory '%s': %s",
                source.value,
                trajectory_path,
                exc,
            )
            continue
        if len(points_xyz_source) == 0:
            continue
        refs.append(
            _write_cloud_ref(
                sequence_slug=sequence_slug,
                source=source,
                points_xyz=points_xyz_source,
                output_dir=output_dir,
                coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
                target_frame=native_frame,
                native_frame=native_frame,
                payload_frame=payload_frame,
                index_rows=index_rows,
                payloads_used=payloads_used,
                skipped_out_of_range_payloads=skipped_out_of_range_payloads,
                point_stride=point_stride,
                max_reference_points=max_reference_points,
                alignment=None,
            )
        )

        try:
            alignment = fit_planar_rigid_alignment(
                source_trajectory=source_trajectory,
                target_trajectory=ground_truth,
                source_frame=native_frame,
                target_frame=_GT_WORLD_FRAME,
            )
        except ValueError:
            continue
        points_xyz_gt = apply_sim3(points_xyz_source, alignment)
        refs.append(
            _write_cloud_ref(
                sequence_slug=sequence_slug,
                source=source,
                points_xyz=points_xyz_gt,
                output_dir=output_dir,
                coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                target_frame=_GT_WORLD_FRAME,
                native_frame=native_frame,
                payload_frame=payload_frame,
                index_rows=index_rows,
                payloads_used=payloads_used,
                skipped_out_of_range_payloads=skipped_out_of_range_payloads,
                point_stride=point_stride,
                max_reference_points=max_reference_points,
                alignment=alignment,
            )
        )
    return refs


def load_tango_point_cloud_index(path: Path) -> NDArray[np.float64]:
    """Load Tango point-cloud timestamps and integer payload indices."""
    rows = np.loadtxt(path, delimiter=",", dtype=np.float64)
    rows = np.atleast_2d(rows)
    if rows.shape[1] < 2:
        raise ValueError(f"Expected `timestamp,index` rows in {path}, got shape {rows.shape}.")
    return rows[:, :2]


def load_bounded_tango_point_clouds(
    *,
    index_path: Path,
    trajectory: PoseTrajectory3D,
    max_reference_points: int,
    point_stride: int,
    target_frame: str = "world",
    source_frame: str = "tango_depth_sensor",
    point_source: ReferenceCloudSource = ReferenceCloudSource.TANGO_AREA_LEARNING,
) -> tuple[NDArray[np.float64], int, int]:
    """Load a deterministic bounded subset of Tango payloads transformed into pose-stream world."""
    if max_reference_points < 1:
        raise ValueError(f"Expected max_reference_points >= 1, got {max_reference_points}.")
    if point_stride < 1:
        raise ValueError(f"Expected point_stride >= 1, got {point_stride}.")
    index_rows = load_tango_point_cloud_index(index_path)
    if index_rows.size == 0:
        return np.empty((0, 3), dtype=np.float64), 0, 0
    source_timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    if source_timestamps_s.size == 0:
        return np.empty((0, 3), dtype=np.float64), 0, int(len(index_rows))
    first_timestamp_s = float(source_timestamps_s.min())
    last_timestamp_s = float(source_timestamps_s.max())
    in_range = (index_rows[:, 0] >= first_timestamp_s) & (index_rows[:, 0] <= last_timestamp_s)
    filtered_index_rows = index_rows[in_range]
    skipped_out_of_range_payloads = int(len(index_rows) - len(filtered_index_rows))
    if filtered_index_rows.size == 0:
        return np.empty((0, 3), dtype=np.float64), 0, skipped_out_of_range_payloads
    poses_world_payload = interpolate_trajectory_poses(
        trajectory,
        filtered_index_rows[:, 0],
        target_frame=target_frame,
        source_frame=source_frame,
    )
    chunks: list[NDArray[np.float64]] = []
    payloads_used = 0
    point_count = 0
    for (_, cloud_index_float), pose_world_payload in zip(filtered_index_rows, poses_world_payload, strict=True):
        payload = load_tango_point_cloud_payload(
            resolve_tango_point_cloud_payload(index_path.parent, cloud_index_float)
        )
        payload = transform_advio_points_to_rdf(payload, point_source)
        points_xyz_world = transform(pose_world_payload.as_matrix(), vectors_to_points(payload))[:, :3]
        sampled = points_xyz_world[::point_stride]
        if len(sampled) == 0:
            continue
        remaining = max_reference_points - point_count
        if remaining <= 0:
            break
        chunks.append(sampled[:remaining])
        payloads_used += 1
        point_count += int(min(len(sampled), remaining))
        if point_count >= max_reference_points:
            break
    if not chunks:
        return np.empty((0, 3), dtype=np.float64), payloads_used, skipped_out_of_range_payloads
    return np.vstack(chunks).astype(np.float64, copy=False), payloads_used, skipped_out_of_range_payloads


def load_tango_point_cloud_payload(path: Path) -> NDArray[np.float64]:
    """Load one Tango point-cloud payload as metric XYZ rows."""
    points = np.loadtxt(path, delimiter=",", dtype=np.float64)
    points = np.atleast_2d(points)
    if points.shape[1] < 3:
        raise ValueError(f"Expected Tango point-cloud payload XYZ rows in {path}, got shape {points.shape}.")
    points = points[:, :3]
    return points[np.all(np.isfinite(points), axis=1)]


def transform_tango_payloads_to_pose_world(
    *,
    index_path: Path,
    trajectory: PoseTrajectory3D,
    point_stride: int = 1,
) -> NDArray[np.float64]:
    """Transform all Tango point-cloud payloads into the selected Tango pose-stream world."""
    points, _payloads_used, _skipped_out_of_range_payloads = load_bounded_tango_point_clouds(
        index_path=index_path,
        trajectory=trajectory,
        max_reference_points=np.iinfo(np.int64).max,
        point_stride=point_stride,
        point_source=ReferenceCloudSource.TANGO_AREA_LEARNING,
    )
    return points


def fit_sim3_alignment(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    source_frame: str,
    target_frame: str,
    max_diff_s: float = _ALIGNMENT_MAX_DIFF_S,
) -> Sim3Alignment:
    """Fit a Sim(3) transform from source trajectory positions to target trajectory positions."""
    source_xyz, target_xyz = _associate_trajectory_positions(
        source_trajectory=source_trajectory,
        target_trajectory=target_trajectory,
        max_diff_s=max_diff_s,
    )
    if len(source_xyz) < _MIN_ALIGNMENT_PAIRS:
        raise ValueError(f"Expected at least {_MIN_ALIGNMENT_PAIRS} matched pairs for Sim(3), got {len(source_xyz)}.")

    source_mean = source_xyz.mean(axis=0)
    target_mean = target_xyz.mean(axis=0)
    source_centered = source_xyz - source_mean
    target_centered = target_xyz - target_mean
    covariance = (target_centered.T @ source_centered) / len(source_xyz)
    u, singular_values, vh = np.linalg.svd(covariance)
    correction = np.eye(3, dtype=np.float64)
    if np.linalg.det(u @ vh) < 0.0:
        correction[-1, -1] = -1.0
    rotation = u @ correction @ vh
    variance = float(np.mean(np.sum(source_centered**2, axis=1)))
    if variance == 0.0:
        raise ValueError("Cannot fit Sim(3) alignment from a degenerate source trajectory.")
    scale = float(np.sum(singular_values * np.diag(correction)) / variance)
    translation = target_mean - scale * (rotation @ source_mean)
    residual = target_xyz - (scale * (source_xyz @ rotation.T) + translation)
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return Sim3Alignment(
        source_frame=source_frame,
        target_frame=target_frame,
        alignment_type="sim3",
        scale=scale,
        rotation=rotation.tolist(),
        translation=translation.tolist(),
        matched_pairs=int(len(source_xyz)),
        rms_error_m=rms_error_m,
    )


def fit_planar_rigid_alignment(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    source_frame: str,
    target_frame: str,
    max_diff_s: float = _ALIGNMENT_MAX_DIFF_S,
) -> Sim3Alignment:
    """Fit ADVIO-style metric planar rigid alignment from source to target.

    The ADVIO paper aligns device tracks with a horizontal-plane rigid
    transform because all devices are already gravity-aligned and metric. In
    the repo viewer convention that plane is X/Z and the vertical axis is Y.
    This preserves scale and avoids introducing pitch/roll corrections into
    native Tango/AR provider worlds.
    """
    source_xyz, target_xyz = _associate_trajectory_positions(
        source_trajectory=source_trajectory,
        target_trajectory=target_trajectory,
        max_diff_s=max_diff_s,
    )
    if len(source_xyz) < _MIN_ALIGNMENT_PAIRS:
        raise ValueError(
            f"Expected at least {_MIN_ALIGNMENT_PAIRS} matched pairs for planar rigid alignment, got {len(source_xyz)}."
        )

    source_mean = source_xyz.mean(axis=0)
    target_mean = target_xyz.mean(axis=0)
    horizontal_axes = np.asarray(_RDF_HORIZONTAL_AXES, dtype=np.int64)
    source_horizontal_centered = source_xyz[:, horizontal_axes] - source_mean[horizontal_axes]
    target_horizontal_centered = target_xyz[:, horizontal_axes] - target_mean[horizontal_axes]
    covariance = (source_horizontal_centered.T @ target_horizontal_centered) / len(source_xyz)
    u, _singular_values, vh = np.linalg.svd(covariance)
    correction = np.eye(2, dtype=np.float64)
    if np.linalg.det(vh.T @ u.T) < 0.0:
        correction[-1, -1] = -1.0
    rotation_xy = vh.T @ correction @ u.T
    rotation = np.eye(3, dtype=np.float64)
    rotation[np.ix_(horizontal_axes, horizontal_axes)] = rotation_xy
    translation = target_mean - rotation @ source_mean
    residual = target_xyz - (source_xyz @ rotation.T + translation)
    rms_error_m = float(np.sqrt(np.mean(np.sum(residual**2, axis=1))))
    return Sim3Alignment(
        source_frame=source_frame,
        target_frame=target_frame,
        alignment_type="planar_rigid",
        scale=1.0,
        rotation=rotation.tolist(),
        translation=translation.tolist(),
        matched_pairs=int(len(source_xyz)),
        rms_error_m=rms_error_m,
    )


def apply_sim3(points_xyz_source: NDArray[np.float64], alignment: Sim3Alignment) -> NDArray[np.float64]:
    """Apply one stored trajectory alignment to XYZ points."""
    points = np.asarray(points_xyz_source, dtype=np.float64)
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    return alignment.scale * (points @ rotation.T) + translation


def transform_trajectory_with_alignment(
    trajectory: PoseTrajectory3D,
    alignment: Sim3Alignment,
) -> PoseTrajectory3D:
    """Apply one stored similarity/rigid alignment to a trajectory."""
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    scale = float(alignment.scale)
    transformed_poses: list[np.ndarray] = []
    for pose in trajectory.poses_se3:
        pose_matrix = np.asarray(pose, dtype=np.float64)
        transformed_pose = np.eye(4, dtype=np.float64)
        transformed_pose[:3, :3] = project_rotation_to_so3(rotation @ pose_matrix[:3, :3])
        transformed_pose[:3, 3] = scale * (rotation @ pose_matrix[:3, 3]) + translation
        transformed_poses.append(transformed_pose)
    positions_xyz = np.asarray([pose[:3, 3] for pose in transformed_poses], dtype=np.float64)
    orientations_quat_wxyz = np.asarray(
        [
            FrameTransform.from_matrix(np.asarray(pose, dtype=np.float64)).quaternion_xyzw()[[3, 0, 1, 2]]
            for pose in transformed_poses
        ],
        dtype=np.float64,
    )
    return PoseTrajectory3D(
        positions_xyz=positions_xyz,
        orientations_quat_wxyz=orientations_quat_wxyz,
        timestamps=np.asarray(trajectory.timestamps, dtype=np.float64),
    )


def _associate_trajectory_positions(
    *,
    source_trajectory: PoseTrajectory3D,
    target_trajectory: PoseTrajectory3D,
    max_diff_s: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    source_timestamps = np.asarray(source_trajectory.timestamps, dtype=np.float64)
    target_timestamps = np.asarray(target_trajectory.timestamps, dtype=np.float64)
    if source_timestamps.size == 0 or target_timestamps.size == 0:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.float64)
    nearest_indices = np.searchsorted(target_timestamps, source_timestamps, side="left")
    nearest_indices = np.clip(nearest_indices, 0, max(len(target_timestamps) - 1, 0))
    previous_indices = np.clip(nearest_indices - 1, 0, max(len(target_timestamps) - 1, 0))
    pick_previous = np.abs(source_timestamps - target_timestamps[previous_indices]) <= np.abs(
        target_timestamps[nearest_indices] - source_timestamps
    )
    nearest_indices = np.where(pick_previous, previous_indices, nearest_indices)
    keep = np.abs(target_timestamps[nearest_indices] - source_timestamps) <= max_diff_s
    return (
        np.asarray(source_trajectory.positions_xyz[keep], dtype=np.float64),
        np.asarray(target_trajectory.positions_xyz[nearest_indices[keep]], dtype=np.float64),
    )


def interpolate_trajectory_poses(
    trajectory: PoseTrajectory3D,
    timestamps_s: NDArray[np.float64],
    *,
    target_frame: str = "world",
    source_frame: str = "camera",
) -> list[FrameTransform]:
    source_timestamps_s = np.asarray(trajectory.timestamps, dtype=np.float64)
    target_timestamps_s = np.asarray(timestamps_s, dtype=np.float64)
    if source_timestamps_s.size == 0:
        return []
    interpolated_positions = np.column_stack(
        [np.interp(target_timestamps_s, source_timestamps_s, trajectory.positions_xyz[:, axis]) for axis in range(3)]
    )
    nearest_indices = np.searchsorted(source_timestamps_s, target_timestamps_s, side="left")
    nearest_indices = np.clip(nearest_indices, 0, max(len(source_timestamps_s) - 1, 0))
    previous_indices = np.clip(nearest_indices - 1, 0, max(len(source_timestamps_s) - 1, 0))
    pick_previous = np.abs(target_timestamps_s - source_timestamps_s[previous_indices]) <= np.abs(
        source_timestamps_s[nearest_indices] - target_timestamps_s
    )
    nearest_indices = np.where(pick_previous, previous_indices, nearest_indices)
    poses: list[FrameTransform] = []
    for position, nearest_index in zip(interpolated_positions, nearest_indices, strict=True):
        nearest_pose = FrameTransform.from_matrix(
            np.asarray(trajectory.poses_se3[int(nearest_index)], dtype=np.float64),
            target_frame=target_frame,
            source_frame=source_frame,
        )
        poses.append(
            FrameTransform(
                target_frame=target_frame,
                source_frame=source_frame,
                qx=nearest_pose.qx,
                qy=nearest_pose.qy,
                qz=nearest_pose.qz,
                qw=nearest_pose.qw,
                tx=float(position[0]),
                ty=float(position[1]),
                tz=float(position[2]),
            )
        )
    return poses


def _write_cloud_ref(
    *,
    sequence_slug: str,
    source: ReferenceCloudSource,
    points_xyz: NDArray[np.float64],
    output_dir: Path,
    coordinate_status: ReferenceCloudCoordinateStatus,
    target_frame: str,
    native_frame: str,
    payload_frame: str,
    index_rows: NDArray[np.float64],
    payloads_used: int,
    skipped_out_of_range_payloads: int,
    point_stride: int,
    max_reference_points: int,
    alignment: Sim3Alignment | None,
) -> ReferenceCloudRef:
    stem = f"{source.value}_{coordinate_status.value}"
    cloud_path = write_point_cloud_ply(output_dir / f"{stem}.ply", points_xyz)
    metadata_path = output_dir / f"{stem}.metadata.json"
    basis_metadata = advio_basis_metadata(source=source, target_frame=target_frame, native_frame=native_frame)
    metadata = TangoCloudMetadata(
        sequence_id=sequence_slug,
        source=source,
        coordinate_status=coordinate_status,
        target_frame=target_frame,
        native_frame=native_frame,
        payload_frame=payload_frame,
        source_world_frame=native_frame,
        raw_coordinate_basis=basis_metadata.raw_coordinate_basis,
        rdf_basis_transform=basis_metadata.rdf_basis_transform,
        point_count=int(len(points_xyz)),
        timestamp_min_s=float(index_rows[:, 0].min()) if index_rows.size else None,
        timestamp_max_s=float(index_rows[:, 0].max()) if index_rows.size else None,
        point_cloud_count=int(len(index_rows)),
        payloads_used=payloads_used,
        skipped_out_of_range_payloads=skipped_out_of_range_payloads,
        point_stride=point_stride,
        max_reference_points=max_reference_points,
        alignment=None if alignment is None else alignment.model_dump(mode="json"),
    )
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
    return ReferenceCloudRef(
        source=source,
        path=cloud_path,
        metadata_path=metadata_path.resolve(),
        target_frame=target_frame,
        coordinate_status=coordinate_status,
    )


def resolve_tango_point_cloud_payload(tango_dir: Path, cloud_index: float | int) -> Path:
    index = int(round(float(cloud_index)))
    candidates = (
        tango_dir / f"point-cloud-{index:05d}.csv",
        tango_dir / f"point-cloud-{index:03d}.csv",
        tango_dir / f"point-cloud-{index}.csv",
    )
    return next((candidate for candidate in candidates if candidate.exists()), candidates[0])


__all__ = [
    "Sim3Alignment",
    "TangoCloudMetadata",
    "apply_sim3",
    "build_advio_tango_reference_clouds",
    "fit_sim3_alignment",
    "fit_planar_rigid_alignment",
    "interpolate_trajectory_poses",
    "load_bounded_tango_point_clouds",
    "load_tango_point_cloud_index",
    "load_tango_point_cloud_payload",
    "resolve_tango_point_cloud_payload",
    "transform_trajectory_with_alignment",
    "transform_tango_payloads_to_pose_world",
]
