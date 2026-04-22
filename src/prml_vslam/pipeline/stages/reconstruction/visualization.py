"""Stage-local reconstruction visualization adapter.

This module translates reconstruction-owned durable artifacts into neutral
sink-facing visualization descriptors. It intentionally does not know Rerun
entity paths, timelines, styling, or SDK objects.
"""

from __future__ import annotations

from collections.abc import Mapping

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent, VisualizationItem
from prml_vslam.reconstruction import ReconstructionArtifacts

POINT_CLOUD_ARTIFACT = "point_cloud"
MESH_ARTIFACT = "mesh"

ROLE_RECONSTRUCTION_POINT_CLOUD = "reconstruction_point_cloud"
ROLE_RECONSTRUCTION_MESH = "reconstruction_mesh"


class ReconstructionVisualizationAdapter:
    """Build neutral visualization descriptors for reconstruction artifacts."""

    def build_items(
        self,
        artifacts: ReconstructionArtifacts,
        artifact_refs: Mapping[str, ArtifactRef],
        *,
        reconstruction_id: str = "reference",
    ) -> list[VisualizationItem]:
        """Return sink-facing visualization items for completed reconstruction outputs."""
        items: list[VisualizationItem] = []
        point_cloud_ref = artifact_refs.get("reference_cloud")
        if point_cloud_ref is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.POINT_CLOUD,
                    role=ROLE_RECONSTRUCTION_POINT_CLOUD,
                    artifact_refs={POINT_CLOUD_ARTIFACT: point_cloud_ref},
                    space="world",
                    metadata={"reconstruction_id": reconstruction_id},
                )
            )
        mesh_ref = artifact_refs.get("reference_mesh")
        if artifacts.mesh_path is not None and mesh_ref is not None:
            items.append(
                VisualizationItem(
                    intent=VisualizationIntent.MESH,
                    role=ROLE_RECONSTRUCTION_MESH,
                    artifact_refs={MESH_ARTIFACT: mesh_ref},
                    space="world",
                    metadata={"reconstruction_id": reconstruction_id},
                )
            )
        return items


__all__ = [
    "MESH_ARTIFACT",
    "POINT_CLOUD_ARTIFACT",
    "ROLE_RECONSTRUCTION_MESH",
    "ROLE_RECONSTRUCTION_POINT_CLOUD",
    "ReconstructionVisualizationAdapter",
]
