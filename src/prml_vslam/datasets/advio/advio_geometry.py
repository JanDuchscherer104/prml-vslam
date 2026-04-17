from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from evo.core.trajectory import PoseTrajectory3D
from numpy.typing import NDArray
from pytransform3d.transformations import transform, vectors_to_points

from prml_vslam.benchmark import ReferenceCloudCoordinateStatus, ReferenceCloudRef, ReferenceCloudSource
from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils import BaseData
from prml_vslam.utils.geometry import write_point_cloud_ply

from .advio_loading import load_advio_trajectory

_DEFAULT_MAX_REFERENCE_POINTS = 200_000
_DEFAULT_POINT_STRIDE = 8
_ALIGNMENT_MAX_DIFF_S = 0.02
_MIN_ALIGNMENT_PAIRS = 3
_GT_WORLD_FRAME = "advio_gt_world"


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
    per_payload_pose_applied: bool = True
    units: str = "meters"
    point_count: int
    timestamp_min_s: float | None
    timestamp_max_s: float | None
    point_cloud_count: int
    payloads_used: int
    point_stride: int
    max_reference_points: int
    alignment: dict[str, object] | None = None


class Sim3Alignment(BaseData):
    """Similarity transform mapping source-frame positions into target-frame positions."""

    source_frame: str
    target_frame: str
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
    if tango_point_cloud_index_path is None or not tango_point_cloud_index_path.exists():
        return []
    index_rows = load_tango_point_cloud_index(tango_point_cloud_index_path)
    if index_rows.size == 0:
        return []

    ground_truth = load_advio_trajectory(ground_truth_csv_path)
    refs: list[ReferenceCloudRef] = []
    source_specs = (
        (ReferenceCloudSource.TANGO_AREA_LEARNING, tango_area_learning_csv_path),
        (ReferenceCloudSource.TANGO_RAW, tango_raw_csv_path),
    )
    for source, trajectory_path in source_specs:
        if trajectory_path is None or not trajectory_path.exists():
            continue
        native_frame = f"advio_{source.value}_world"
        source_trajectory = load_advio_trajectory(trajectory_path)
        points_xyz_source, payloads_used = load_bounded_tango_point_clouds(
            index_path=tango_point_cloud_index_path,
            trajectory=source_trajectory,
            max_reference_points=max_reference_points,
            point_stride=point_stride,
        )
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
                index_rows=index_rows,
                payloads_used=payloads_used,
                point_stride=point_stride,
                max_reference_points=max_reference_points,
                alignment=None,
            )
        )

        try:
            alignment = fit_sim3_alignment(
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
                index_rows=index_rows,
                payloads_used=payloads_used,
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
) -> tuple[NDArray[np.float64], int]:
    """Load a deterministic bounded subset of Tango payloads transformed into pose-stream world."""
    if max_reference_points < 1:
        raise ValueError(f"Expected max_reference_points >= 1, got {max_reference_points}.")
    if point_stride < 1:
        raise ValueError(f"Expected point_stride >= 1, got {point_stride}.")
    index_rows = load_tango_point_cloud_index(index_path)
    chunks: list[NDArray[np.float64]] = []
    payloads_used = 0
    point_count = 0
    poses_world_payload = _poses_for_timestamps(index_rows[:, 0], trajectory)
    for (_, cloud_index_float), pose_world_payload in zip(index_rows, poses_world_payload, strict=True):
        payload = load_tango_point_cloud_payload(
            _resolve_tango_point_cloud_payload(index_path.parent, cloud_index_float)
        )
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
        return np.empty((0, 3), dtype=np.float64), payloads_used
    return np.vstack(chunks).astype(np.float64, copy=False), payloads_used


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
    points, _ = load_bounded_tango_point_clouds(
        index_path=index_path,
        trajectory=trajectory,
        max_reference_points=np.iinfo(np.int64).max,
        point_stride=point_stride,
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
        scale=scale,
        rotation=rotation.tolist(),
        translation=translation.tolist(),
        matched_pairs=int(len(source_xyz)),
        rms_error_m=rms_error_m,
    )


def apply_sim3(points_xyz_source: NDArray[np.float64], alignment: Sim3Alignment) -> NDArray[np.float64]:
    """Apply one stored Sim(3) alignment to XYZ points."""
    points = np.asarray(points_xyz_source, dtype=np.float64)
    rotation = np.asarray(alignment.rotation, dtype=np.float64)
    translation = np.asarray(alignment.translation, dtype=np.float64)
    return alignment.scale * (points @ rotation.T) + translation


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


def _poses_for_timestamps(timestamps_s: NDArray[np.float64], trajectory: PoseTrajectory3D) -> list[FrameTransform]:
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
            target_frame="world",
            source_frame="tango_depth_sensor",
        )
        poses.append(
            FrameTransform(
                target_frame=nearest_pose.target_frame,
                source_frame=nearest_pose.source_frame,
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
    index_rows: NDArray[np.float64],
    payloads_used: int,
    point_stride: int,
    max_reference_points: int,
    alignment: Sim3Alignment | None,
) -> ReferenceCloudRef:
    stem = f"{source.value}_{coordinate_status.value}"
    cloud_path = write_point_cloud_ply(output_dir / f"{stem}.ply", points_xyz)
    metadata_path = output_dir / f"{stem}.metadata.json"
    metadata = TangoCloudMetadata(
        sequence_id=sequence_slug,
        source=source,
        coordinate_status=coordinate_status,
        target_frame=target_frame,
        native_frame=native_frame,
        source_world_frame=native_frame,
        point_count=int(len(points_xyz)),
        timestamp_min_s=float(index_rows[:, 0].min()) if index_rows.size else None,
        timestamp_max_s=float(index_rows[:, 0].max()) if index_rows.size else None,
        point_cloud_count=int(len(index_rows)),
        payloads_used=payloads_used,
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


def _resolve_tango_point_cloud_payload(tango_dir: Path, cloud_index: float) -> Path:
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
    "load_bounded_tango_point_clouds",
    "load_tango_point_cloud_index",
    "load_tango_point_cloud_payload",
    "transform_tango_payloads_to_pose_world",
]
