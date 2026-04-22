"""Tests for reconstruction stage visualization item mapping."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.interfaces.slam import ArtifactRef
from prml_vslam.pipeline.stages.base.contracts import VisualizationIntent
from prml_vslam.pipeline.stages.reconstruction.visualization import (
    MESH_ARTIFACT,
    POINT_CLOUD_ARTIFACT,
    ROLE_RECONSTRUCTION_MESH,
    ROLE_RECONSTRUCTION_POINT_CLOUD,
    ReconstructionVisualizationAdapter,
)
from prml_vslam.reconstruction import ReconstructionArtifacts


def _artifact(path: Path, *, kind: str = "ply") -> ArtifactRef:
    return ArtifactRef(path=path, kind=kind, fingerprint=path.name)


def test_reconstruction_adapter_maps_cloud_only_artifacts(tmp_path: Path) -> None:
    cloud = tmp_path / "reference_cloud.ply"
    metadata = tmp_path / "metadata.json"
    artifacts = ReconstructionArtifacts(reference_cloud_path=cloud, metadata_path=metadata)

    items = ReconstructionVisualizationAdapter().build_items(
        artifacts,
        {"reference_cloud": _artifact(cloud)},
    )

    assert len(items) == 1
    assert items[0].intent is VisualizationIntent.POINT_CLOUD
    assert items[0].role == ROLE_RECONSTRUCTION_POINT_CLOUD
    assert items[0].artifact_refs[POINT_CLOUD_ARTIFACT].path == cloud
    assert items[0].payload_refs == {}
    assert items[0].frame_index is None
    assert items[0].keyframe_index is None
    assert items[0].space == "world"
    assert "entity_path" not in items[0].model_dump(mode="json")
    assert "timeline" not in items[0].model_dump(mode="json")


def test_reconstruction_adapter_maps_cloud_and_mesh_artifacts(tmp_path: Path) -> None:
    cloud = tmp_path / "reference_cloud.ply"
    metadata = tmp_path / "metadata.json"
    mesh = tmp_path / "reference_mesh.ply"
    artifacts = ReconstructionArtifacts(reference_cloud_path=cloud, metadata_path=metadata, mesh_path=mesh)

    items = ReconstructionVisualizationAdapter().build_items(
        artifacts,
        {
            "reference_cloud": _artifact(cloud),
            "reference_mesh": _artifact(mesh),
        },
        reconstruction_id="reference",
    )

    assert [(item.intent, item.role) for item in items] == [
        (VisualizationIntent.POINT_CLOUD, ROLE_RECONSTRUCTION_POINT_CLOUD),
        (VisualizationIntent.MESH, ROLE_RECONSTRUCTION_MESH),
    ]
    assert items[0].artifact_refs[POINT_CLOUD_ARTIFACT].path == cloud
    assert items[1].artifact_refs[MESH_ARTIFACT].path == mesh
    assert all(item.metadata["reconstruction_id"] == "reference" for item in items)
    assert all(item.frame_index is None for item in items)
    assert all(item.keyframe_index is None for item in items)
