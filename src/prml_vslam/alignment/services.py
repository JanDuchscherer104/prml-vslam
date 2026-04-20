"""Open3D-backed dominant-ground detection and viewer alignment helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import numpy as np
from numpy.typing import NDArray
from scipy.spatial.transform import Rotation

from prml_vslam.interfaces import FrameTransform
from prml_vslam.utils.geometry import load_point_cloud_ply, load_tum_trajectory

from .contracts import (
    GroundAlignmentConfig,
    GroundAlignmentMetadata,
    GroundPlaneModel,
    GroundPlaneVisualizationHint,
)

if TYPE_CHECKING:
    from prml_vslam.pipeline.contracts.artifacts import SlamArtifacts

_RANSAC_DISTANCE_THRESHOLD_M = 0.03
_RANSAC_NUM_POINTS = 3
_RANSAC_ITERATIONS = 500
_VOXEL_SIZE_M = 0.05
_MAX_PLANE_CANDIDATES = 5
_MIN_INPUT_POINTS = 200
_MIN_INLIER_COUNT = 150
_MIN_INLIER_RATIO = 0.02
_MIN_CAMERA_SIDE_FRACTION = 0.75
_MIN_CAMERA_HEIGHT_M = 0.05
_MIN_CAMERA_DOWN_ALIGNMENT = 0.55
_TRAJECTORY_SPREAD_EPS_M = 0.25
_PATCH_LOW_PERCENTILE = 5.0
_PATCH_HIGH_PERCENTILE = 95.0
_EXTENT_SCALE_M = 5.0
_EPS = 1e-9


@dataclass(slots=True, frozen=True)
class _PlaneCandidate:
    normal_xyz_world: NDArray[np.float64]
    offset_world: float
    inlier_points_xyz_world: NDArray[np.float64]
    inlier_count: int
    inlier_ratio: float
    median_camera_height_world: float
    camera_height_spread_world: float
    camera_side_fraction: float
    camera_down_alignment: float
    patch_corners_xyz_world: list[tuple[float, float, float]]
    confidence: float


class GroundAlignmentService:
    """Detect a dominant ground plane and derive a viewer-scoped transform."""

    def __init__(self, *, config: GroundAlignmentConfig | None = None) -> None:
        self._config = GroundAlignmentConfig() if config is None else config

    def estimate_from_slam_artifacts(self, *, slam: SlamArtifacts) -> GroundAlignmentMetadata:
        """Estimate one dominant ground plane from normalized SLAM artifacts."""
        point_cloud_source, point_cloud_path = self._resolve_point_cloud_path(slam)
        if point_cloud_path is None:
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.0,
                point_cloud_source="none",
                skip_reason="No point-cloud artifact is available for ground-plane detection.",
            )

        points_xyz_world = load_point_cloud_ply(point_cloud_path)
        if len(points_xyz_world) < _MIN_INPUT_POINTS:
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.0,
                point_cloud_source=point_cloud_source,
                skip_reason=f"Point cloud '{point_cloud_path.name}' contains too few points for RANSAC.",
            )

        trajectory = load_tum_trajectory(slam.trajectory_tum.path)
        camera_positions_xyz_world = np.asarray(trajectory.positions_xyz, dtype=np.float64)
        poses_world_camera = np.asarray(trajectory.poses_se3, dtype=np.float64)
        processed_points_xyz_world = self._prepare_points(points_xyz_world)
        if len(processed_points_xyz_world) < _MIN_INPUT_POINTS:
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.0,
                point_cloud_source=point_cloud_source,
                skip_reason="Filtered point cloud contains too few samples for ground-plane detection.",
            )

        candidates = self._extract_plane_candidates(
            processed_points_xyz_world=processed_points_xyz_world,
            camera_positions_xyz_world=camera_positions_xyz_world,
            poses_world_camera=poses_world_camera,
        )
        if not candidates:
            return GroundAlignmentMetadata(
                applied=False,
                confidence=0.0,
                point_cloud_source=point_cloud_source,
                candidate_count=0,
                skip_reason="No plane candidate satisfied the minimum RANSAC support thresholds.",
            )

        best_candidate = max(candidates, key=lambda candidate: candidate.confidence)
        if best_candidate.confidence < self._config.min_confidence:
            return GroundAlignmentMetadata(
                applied=False,
                confidence=float(best_candidate.confidence),
                point_cloud_source=point_cloud_source,
                candidate_count=len(candidates),
                support_ratio=float(best_candidate.inlier_ratio),
                median_camera_height_world=float(best_candidate.median_camera_height_world),
                camera_height_spread_world=float(best_candidate.camera_height_spread_world),
                camera_down_alignment=float(best_candidate.camera_down_alignment),
                skip_reason=(
                    f"Best plane confidence {best_candidate.confidence:.3f} is below the configured threshold "
                    f"{self._config.min_confidence:.3f}."
                ),
            )

        yaw_source, rotation_viewer_world = self._build_viewer_rotation(
            normal_xyz_world=best_candidate.normal_xyz_world,
            camera_positions_xyz_world=camera_positions_xyz_world,
        )
        transform_viewer_world_world = self._build_viewer_transform(
            rotation_viewer_world=rotation_viewer_world,
            plane_offset_world=best_candidate.offset_world,
        )
        return GroundAlignmentMetadata(
            applied=True,
            confidence=float(best_candidate.confidence),
            point_cloud_source=point_cloud_source,
            ground_plane_world=GroundPlaneModel(
                normal_xyz_world=tuple(float(value) for value in best_candidate.normal_xyz_world),
                offset_world=float(best_candidate.offset_world),
                inlier_count=best_candidate.inlier_count,
                inlier_ratio=float(best_candidate.inlier_ratio),
            ),
            T_viewer_world_world=transform_viewer_world_world,
            yaw_source=yaw_source,
            candidate_count=len(candidates),
            support_ratio=float(best_candidate.inlier_ratio),
            median_camera_height_world=float(best_candidate.median_camera_height_world),
            camera_height_spread_world=float(best_candidate.camera_height_spread_world),
            camera_down_alignment=float(best_candidate.camera_down_alignment),
            visualization=GroundPlaneVisualizationHint(
                corners_xyz_world=best_candidate.patch_corners_xyz_world,
            ),
        )

    @staticmethod
    def _resolve_point_cloud_path(slam: SlamArtifacts) -> tuple[str, Path | None]:
        if slam.dense_points_ply is not None:
            return "dense_points_ply", slam.dense_points_ply.path
        if slam.sparse_points_ply is not None:
            return "sparse_points_ply", slam.sparse_points_ply.path
        return "none", None

    def _extract_plane_candidates(
        self,
        *,
        processed_points_xyz_world: NDArray[np.float64],
        camera_positions_xyz_world: NDArray[np.float64],
        poses_world_camera: NDArray[np.float64],
    ) -> list[_PlaneCandidate]:
        o3d = _import_open3d()
        candidates: list[_PlaneCandidate] = []
        working_points_xyz_world = processed_points_xyz_world.copy()
        total_points = len(processed_points_xyz_world)
        for _ in range(_MAX_PLANE_CANDIDATES):
            if len(working_points_xyz_world) < _MIN_INPUT_POINTS:
                break
            point_cloud = o3d.geometry.PointCloud()
            point_cloud.points = o3d.utility.Vector3dVector(working_points_xyz_world)
            plane_model, inlier_indices = point_cloud.segment_plane(
                distance_threshold=_RANSAC_DISTANCE_THRESHOLD_M,
                ransac_n=_RANSAC_NUM_POINTS,
                num_iterations=_RANSAC_ITERATIONS,
            )
            if len(inlier_indices) < _MIN_INLIER_COUNT:
                break
            inlier_ratio = len(inlier_indices) / max(total_points, 1)
            if inlier_ratio < _MIN_INLIER_RATIO:
                break
            candidate = self._score_plane_candidate(
                plane_model=np.asarray(plane_model, dtype=np.float64),
                inlier_points_xyz_world=working_points_xyz_world[np.asarray(inlier_indices, dtype=np.int64)],
                total_points=total_points,
                camera_positions_xyz_world=camera_positions_xyz_world,
                poses_world_camera=poses_world_camera,
            )
            if candidate is not None:
                candidates.append(candidate)
            keep_mask = np.ones(len(working_points_xyz_world), dtype=bool)
            keep_mask[np.asarray(inlier_indices, dtype=np.int64)] = False
            working_points_xyz_world = working_points_xyz_world[keep_mask]
        return candidates

    def _score_plane_candidate(
        self,
        *,
        plane_model: NDArray[np.float64],
        inlier_points_xyz_world: NDArray[np.float64],
        total_points: int,
        camera_positions_xyz_world: NDArray[np.float64],
        poses_world_camera: NDArray[np.float64],
    ) -> _PlaneCandidate | None:
        normal_xyz_world = np.asarray(plane_model[:3], dtype=np.float64)
        normal_norm = np.linalg.norm(normal_xyz_world)
        if not np.isfinite(normal_norm) or normal_norm <= _EPS:
            return None
        normal_xyz_world = normal_xyz_world / normal_norm
        offset_world = float(plane_model[3]) / normal_norm

        signed_camera_heights = camera_positions_xyz_world @ normal_xyz_world + offset_world
        if np.median(signed_camera_heights) < 0.0:
            normal_xyz_world = -normal_xyz_world
            offset_world = -offset_world
            signed_camera_heights = -signed_camera_heights

        camera_side_fraction = float(np.mean(signed_camera_heights > 0.0))
        median_camera_height_world = float(np.median(signed_camera_heights))
        camera_height_spread_world = float(np.std(signed_camera_heights))
        camera_down_alignment = self._camera_down_alignment(
            normal_xyz_world=normal_xyz_world,
            poses_world_camera=poses_world_camera,
        )
        if (
            camera_side_fraction < _MIN_CAMERA_SIDE_FRACTION
            or median_camera_height_world <= _MIN_CAMERA_HEIGHT_M
            or camera_down_alignment < _MIN_CAMERA_DOWN_ALIGNMENT
        ):
            confidence = 0.0
        else:
            inlier_ratio = len(inlier_points_xyz_world) / max(total_points, 1)
            support_score = np.clip((inlier_ratio - _MIN_INLIER_RATIO) / 0.35, 0.0, 1.0)
            height_consistency = 1.0 / (
                1.0 + (camera_height_spread_world / max(median_camera_height_world, _MIN_CAMERA_HEIGHT_M))
            )
            patch_corners_xyz_world = _plane_patch_corners(
                inlier_points_xyz_world=inlier_points_xyz_world,
                normal_xyz_world=normal_xyz_world,
                offset_world=offset_world,
            )
            patch_extent = _patch_extent_m(patch_corners_xyz_world)
            extent_score = float(np.clip(patch_extent / _EXTENT_SCALE_M, 0.0, 1.0))
            confidence = float(
                (0.40 * support_score + 0.25 * camera_side_fraction + 0.25 * height_consistency + 0.10 * extent_score)
                * camera_down_alignment
            )
            return _PlaneCandidate(
                normal_xyz_world=normal_xyz_world,
                offset_world=offset_world,
                inlier_points_xyz_world=inlier_points_xyz_world,
                inlier_count=len(inlier_points_xyz_world),
                inlier_ratio=inlier_ratio,
                median_camera_height_world=median_camera_height_world,
                camera_height_spread_world=camera_height_spread_world,
                camera_side_fraction=camera_side_fraction,
                camera_down_alignment=camera_down_alignment,
                patch_corners_xyz_world=patch_corners_xyz_world,
                confidence=confidence,
            )
        return _PlaneCandidate(
            normal_xyz_world=normal_xyz_world,
            offset_world=offset_world,
            inlier_points_xyz_world=inlier_points_xyz_world,
            inlier_count=len(inlier_points_xyz_world),
            inlier_ratio=len(inlier_points_xyz_world) / max(total_points, 1),
            median_camera_height_world=median_camera_height_world,
            camera_height_spread_world=camera_height_spread_world,
            camera_side_fraction=camera_side_fraction,
            camera_down_alignment=camera_down_alignment,
            patch_corners_xyz_world=_plane_patch_corners(
                inlier_points_xyz_world=inlier_points_xyz_world,
                normal_xyz_world=normal_xyz_world,
                offset_world=offset_world,
            ),
            confidence=confidence,
        )

    @staticmethod
    def _prepare_points(points_xyz_world: NDArray[np.float64]) -> NDArray[np.float64]:
        o3d = _import_open3d()
        finite_points_xyz_world = np.asarray(points_xyz_world, dtype=np.float64)
        finite_points_xyz_world = finite_points_xyz_world[np.all(np.isfinite(finite_points_xyz_world), axis=1)]
        if len(finite_points_xyz_world) == 0:
            return np.empty((0, 3), dtype=np.float64)
        point_cloud = o3d.geometry.PointCloud()
        point_cloud.points = o3d.utility.Vector3dVector(finite_points_xyz_world)
        downsampled = point_cloud.voxel_down_sample(voxel_size=_VOXEL_SIZE_M)
        if len(downsampled.points) == 0:
            return np.empty((0, 3), dtype=np.float64)
        if len(downsampled.points) >= _MIN_INPUT_POINTS:
            downsampled, _ = downsampled.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
        return np.asarray(downsampled.points, dtype=np.float64)

    @staticmethod
    def _camera_down_alignment(
        *,
        normal_xyz_world: NDArray[np.float64],
        poses_world_camera: NDArray[np.float64],
    ) -> float:
        if poses_world_camera.size == 0:
            return 0.0
        normals_xyz_camera = np.einsum("nij,j->ni", poses_world_camera[:, :3, :3].transpose(0, 2, 1), normal_xyz_world)
        return float(np.median(np.abs(normals_xyz_camera[:, 1])))

    def _build_viewer_rotation(
        self,
        *,
        normal_xyz_world: NDArray[np.float64],
        camera_positions_xyz_world: NDArray[np.float64],
    ) -> tuple[Literal["trajectory_pca", "identity"], NDArray[np.float64]]:
        up_xyz_viewer = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        rotation_up = _rotation_matrix_aligning_vectors(source=normal_xyz_world, target=up_xyz_viewer)
        yaw_source = "identity"
        rotation_yaw = np.eye(3, dtype=np.float64)
        viewer_positions_xyz = (rotation_up @ np.asarray(camera_positions_xyz_world, dtype=np.float64).T).T
        centered_xz = viewer_positions_xyz[:, [0, 2]] - np.mean(viewer_positions_xyz[:, [0, 2]], axis=0, keepdims=True)
        if len(centered_xz) >= 2:
            covariance = centered_xz.T @ centered_xz
            eigenvalues, eigenvectors = np.linalg.eigh(covariance)
            principal_direction_xz = eigenvectors[:, int(np.argmax(eigenvalues))]
            principal_spread = float(np.sqrt(np.max(eigenvalues)))
            if np.isfinite(principal_spread) and principal_spread >= _TRAJECTORY_SPREAD_EPS_M:
                yaw_source = "trajectory_pca"
                yaw_rad = float(np.arctan2(principal_direction_xz[0], principal_direction_xz[1]))
                rotation_yaw = Rotation.from_euler("y", -yaw_rad).as_matrix()
        rotation_viewer_world = Rotation.from_matrix(rotation_yaw @ rotation_up).as_matrix()
        return yaw_source, rotation_viewer_world

    @staticmethod
    def _build_viewer_transform(
        *,
        rotation_viewer_world: NDArray[np.float64],
        plane_offset_world: float,
    ) -> FrameTransform:
        transform_viewer_world_world = np.eye(4, dtype=np.float64)
        transform_viewer_world_world[:3, :3] = rotation_viewer_world
        transform_viewer_world_world[:3, 3] = np.array([0.0, plane_offset_world, 0.0], dtype=np.float64)
        return FrameTransform.from_matrix(
            transform_viewer_world_world,
            target_frame="viewer_world",
            source_frame="world",
        )


def _import_open3d() -> object:
    try:
        import open3d as o3d
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency is pinned in the repo
        raise RuntimeError("Ground-plane detection requires the repository Open3D dependency.") from exc
    return o3d


def _plane_patch_corners(
    *,
    inlier_points_xyz_world: NDArray[np.float64],
    normal_xyz_world: NDArray[np.float64],
    offset_world: float,
) -> list[tuple[float, float, float]]:
    basis_u_xyz_world, basis_v_xyz_world = _plane_basis(normal_xyz_world)
    projected_u = inlier_points_xyz_world @ basis_u_xyz_world
    projected_v = inlier_points_xyz_world @ basis_v_xyz_world
    u_min, u_max = np.percentile(projected_u, [_PATCH_LOW_PERCENTILE, _PATCH_HIGH_PERCENTILE])
    v_min, v_max = np.percentile(projected_v, [_PATCH_LOW_PERCENTILE, _PATCH_HIGH_PERCENTILE])
    point_on_plane_xyz_world = -offset_world * normal_xyz_world
    corners = [
        point_on_plane_xyz_world + u_min * basis_u_xyz_world + v_min * basis_v_xyz_world,
        point_on_plane_xyz_world + u_min * basis_u_xyz_world + v_max * basis_v_xyz_world,
        point_on_plane_xyz_world + u_max * basis_u_xyz_world + v_max * basis_v_xyz_world,
        point_on_plane_xyz_world + u_max * basis_u_xyz_world + v_min * basis_v_xyz_world,
    ]
    return [tuple(float(value) for value in corner) for corner in corners]


def _patch_extent_m(corners_xyz_world: list[tuple[float, float, float]]) -> float:
    if len(corners_xyz_world) != 4:
        return 0.0
    corners_xyz = np.asarray(corners_xyz_world, dtype=np.float64)
    edge_lengths = np.linalg.norm(np.roll(corners_xyz, -1, axis=0) - corners_xyz, axis=1)
    return float(np.mean(edge_lengths[:2]))


def _plane_basis(normal_xyz_world: NDArray[np.float64]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    reference_axis = np.array([1.0, 0.0, 0.0], dtype=np.float64)
    if np.abs(np.dot(reference_axis, normal_xyz_world)) > 0.9:
        reference_axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    basis_u_xyz_world = np.cross(normal_xyz_world, reference_axis)
    basis_u_xyz_world /= np.linalg.norm(basis_u_xyz_world)
    basis_v_xyz_world = np.cross(normal_xyz_world, basis_u_xyz_world)
    basis_v_xyz_world /= np.linalg.norm(basis_v_xyz_world)
    return basis_u_xyz_world, basis_v_xyz_world


def _rotation_matrix_aligning_vectors(
    *,
    source: NDArray[np.float64],
    target: NDArray[np.float64],
) -> NDArray[np.float64]:
    source_unit = np.asarray(source, dtype=np.float64)
    source_unit /= np.linalg.norm(source_unit)
    target_unit = np.asarray(target, dtype=np.float64)
    target_unit /= np.linalg.norm(target_unit)
    cross_product = np.cross(source_unit, target_unit)
    cross_norm = np.linalg.norm(cross_product)
    dot_product = float(np.clip(np.dot(source_unit, target_unit), -1.0, 1.0))
    if cross_norm <= _EPS:
        if dot_product > 0.0:
            return np.eye(3, dtype=np.float64)
        axis = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        if np.abs(np.dot(axis, source_unit)) > 0.9:
            axis = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        axis = axis - source_unit * np.dot(axis, source_unit)
        axis /= np.linalg.norm(axis)
        return Rotation.from_rotvec(np.pi * axis).as_matrix()
    skew = np.array(
        [
            [0.0, -cross_product[2], cross_product[1]],
            [cross_product[2], 0.0, -cross_product[0]],
            [-cross_product[1], cross_product[0], 0.0],
        ],
        dtype=np.float64,
    )
    return np.eye(3, dtype=np.float64) + skew + (skew @ skew) * ((1.0 - dot_product) / (cross_norm**2))


__all__ = ["GroundAlignmentService"]
