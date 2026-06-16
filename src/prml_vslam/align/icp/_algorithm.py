"""ICP point-cloud alignment service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import open3d as o3d

from prml_vslam.eval.contracts import CloudAlignmentArtifact, CloudAlignmentSelection
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, write_point_cloud_ply

__all__ = ["CloudAlignmentService"]


class CloudAlignmentService:
    """Materialize offline point-cloud alignment artifacts before cloud metrics."""

    def compute_cloud_alignment(self, *, selection: CloudAlignmentSelection) -> CloudAlignmentArtifact:
        """Refine a trajectory-Sim(3)-aligned cloud against a reference cloud with ICP."""
        reference_pcd = _read_non_empty_point_cloud(selection.reference_cloud_path, label="reference")
        estimate_pcd = _read_non_empty_point_cloud(selection.sim3_cloud_path, label="estimate")
        registration = o3d.pipelines.registration.registration_icp(
            estimate_pcd,
            reference_pcd,
            selection.max_correspondence_distance_m,
            np.eye(4, dtype=np.float64),
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        )
        transformation = np.asarray(registration.transformation, dtype=np.float64)
        points_xyz, colors_rgb = load_point_cloud_ply_with_colors(selection.sim3_cloud_path)
        rotation = transformation[:3, :3]
        translation = transformation[:3, 3]
        refined_points = points_xyz @ rotation.T + translation
        icp_cloud_path = self.icp_point_cloud_path(selection.artifact_root)
        write_point_cloud_ply(icp_cloud_path, refined_points, colors_rgb=colors_rgb)
        artifact = CloudAlignmentArtifact(
            path=self.result_path(selection.artifact_root),
            reference_cloud_path=selection.reference_cloud_path,
            sim3_point_cloud_path=selection.sim3_cloud_path,
            icp_point_cloud_path=icp_cloud_path,
            target_frame=selection.target_frame,
            max_correspondence_distance_m=selection.max_correspondence_distance_m,
            fitness=float(registration.fitness),
            inlier_rmse_m=float(registration.inlier_rmse),
            transformation=transformation.tolist(),
        )
        artifact.path.parent.mkdir(parents=True, exist_ok=True)
        artifact.path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return artifact

    @staticmethod
    def result_path(run_root: Path) -> Path:
        """Return the deterministic point-cloud alignment metadata path."""
        return run_root / "evaluation" / "cloud_alignment.json"

    @staticmethod
    def icp_point_cloud_path(run_root: Path) -> Path:
        """Return the deterministic ICP-refined point-cloud path."""
        return run_root / "evaluation" / "point_cloud_sim3_icp_aligned.ply"


def _read_non_empty_point_cloud(path: Path, *, label: str) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Point-cloud alignment {label} cloud does not exist: {path}")
    point_cloud = o3d.io.read_point_cloud(path.as_posix())
    points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
    if points_xyz.shape[0] == 0:
        raise ValueError(f"Point-cloud alignment {label} cloud is empty: {path}")
    if points_xyz.ndim != 2 or points_xyz.shape[1] != 3:
        raise ValueError(f"Expected {label} point cloud shape (N, 3), got {points_xyz.shape} for '{path}'.")
    if not np.isfinite(points_xyz).all():
        raise ValueError(f"Point-cloud alignment {label} cloud contains non-finite points: {path}")
    return point_cloud
