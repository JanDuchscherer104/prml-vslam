"""Artifact-to-visualization mapping for durable stage outputs."""

from __future__ import annotations

from collections.abc import Mapping

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent, VisualizationItem
from prml_vslam.reconstruction.stage.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
)

ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT = "slam_raw_trajectory_artifact"
ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY = "slam_sim3_aligned_trajectory"
ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD = "slam_sim3_aligned_point_cloud"


def artifact_visualizations(artifacts: Mapping[str, ArtifactRef]) -> list[VisualizationItem]:
    """Return neutral visualization items for completed durable artifacts."""
    visualizations: list[VisualizationItem] = []
    trajectory = artifacts.get("trajectory_tum")
    if trajectory is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.TRAJECTORY,
                role=ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT,
                artifact_refs={"trajectory": trajectory},
                space="vista_slam_world",
                metadata={"target_frame": "vista_slam_world", "coordinate_status": "raw"},
            )
        )
    dense_points = artifacts.get("dense_points_ply")
    if dense_points is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: dense_points},
                space="world",
                metadata={"reconstruction_id": "slam"},
            )
        )
    reference_cloud = artifacts.get("reference_cloud")
    if reference_cloud is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: reference_cloud},
                space="world",
                metadata={"reconstruction_id": "reference"},
            )
        )
    reference_mesh = artifacts.get("reference_mesh")
    if reference_mesh is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.MESH,
                role=ROLE_RECONSTRUCTION_MESH,
                artifact_refs={MESH_ARTIFACT: reference_mesh},
                space="world",
                metadata={"reconstruction_id": "reference"},
            )
        )
    aligned_trajectory = artifacts.get("aligned_estimate_tum")
    if aligned_trajectory is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.TRAJECTORY,
                role=ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY,
                artifact_refs={"trajectory": aligned_trajectory},
                space="advio_gt_world",
                metadata={"target_frame": "advio_gt_world", "coordinate_status": "sim3_aligned"},
            )
        )
    aligned_point_cloud = artifacts.get("aligned_point_cloud_ply")
    if aligned_point_cloud is not None:
        visualizations.append(
            VisualizationItem(
                intent=VisualizationIntent.POINT_CLOUD,
                role=ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD,
                artifact_refs={POINT_CLOUD_ARTIFACT: aligned_point_cloud},
                space="advio_gt_world",
                metadata={"target_frame": "advio_gt_world", "coordinate_status": "sim3_aligned"},
            )
        )
    return visualizations


__all__ = [
    "ROLE_SLAM_RAW_TRAJECTORY_ARTIFACT",
    "ROLE_SLAM_SIM3_ALIGNED_POINT_CLOUD",
    "ROLE_SLAM_SIM3_ALIGNED_TRAJECTORY",
    "artifact_visualizations",
]
