"""Stage-local reconstruction visualization adapter.

This module translates reconstruction-owned durable artifacts into neutral
sink-facing visualization descriptors. It intentionally does not know Rerun
entity paths, timelines, styling, or SDK objects.
"""

from __future__ import annotations

from collections.abc import Mapping

from prml_vslam.interfaces.artifacts import ArtifactRef
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent, VisualizationItem
from prml_vslam.reconstruction import ReconstructionArtifacts

POINT_CLOUD_ARTIFACT = "point_cloud"
MESH_ARTIFACT = "mesh"

ROLE_RECONSTRUCTION_POINT_CLOUD = "reconstruction_point_cloud"
ROLE_RECONSTRUCTION_MESH = "reconstruction_mesh"


class ReconstructionVisualizationAdapter:
    """Build neutral visualization descriptors for reconstruction artifacts.

    The adapter keeps reconstruction output sink-ready without importing Rerun.
    It maps durable reconstruction artifacts into roles and intents that the
    observer layer can place into the viewer according to visualization policy.
    """

    def build_items(
        self,
        artifacts: ReconstructionArtifacts,
        artifact_refs: Mapping[str, ArtifactRef],
        *,
        reconstruction_id: str = "reference",
    ) -> list[VisualizationItem]:
        """Return sink-facing visualization items for completed reconstruction outputs.

        Args:
            artifacts: Reconstruction-owned durable artifact bundle.
            artifact_refs: Pipeline artifact refs keyed by stage artifact name.
            reconstruction_id: Stable role suffix for the reconstruction mode.

        Returns:
            Neutral point-cloud or mesh visualization descriptors, when the
            corresponding durable artifacts exist.
        """
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
