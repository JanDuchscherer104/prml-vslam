"""Neural Kernel Surface Reconstruction (NKSR) backend.

This module implements the NKSR backend for high-fidelity surface reconstruction
from point clouds. It requires torch and nksr to be installed.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from prml_vslam.interfaces import Observation
from prml_vslam.reconstruction.contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
)

if TYPE_CHECKING:
    from .config import NksrBackendConfig


class NksrBackend:
    """Reconstruct a surface mesh from a point cloud using NKSR."""

    method_id = ReconstructionMethodId.NKSR

    def __init__(self, config: NksrBackendConfig, **_kwargs: Any) -> None:
        self._config = config

    def run_sequence(
        self,
        observations: Iterable[Observation],
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """NKSR does not integrate RGB-D sequences directly; it merges them into a cloud first."""
        # For now, we don't support direct sequence integration if it's too complex.
        # But we could implement it by accumulating points.
        raise NotImplementedError(
            "NKSR backend does not support direct RGB-D sequence integration. Use a point-cloud input source instead."
        )

    def run_point_cloud(
        self,
        point_cloud_path: Path,
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Run NKSR on a pre-aligned point cloud."""
        import nksr
        import open3d as o3d
        import torch

        device = torch.device(self._config.device)

        # 1. Load point cloud
        pcd = o3d.io.read_point_cloud(str(point_cloud_path))
        if pcd.is_empty():
            raise RuntimeError(f"Input point cloud is empty: {point_cloud_path}")

        # 2. Estimate normals if requested or missing
        if self._config.preprocess_normals or not pcd.has_normals():
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(
                    radius=self._config.normal_radius_m,
                    max_nn=self._config.normal_max_nn,
                )
            )
            # Ensure normals are oriented towards the camera or generally consistent.
            # Open3D's estimate_normals doesn't guarantee global orientation.
            pcd.orient_normals_consistent_tangent_plane(k=self._config.normal_max_nn)

        points = torch.from_numpy(np.asarray(pcd.points)).to(device).float()
        normals = torch.from_numpy(np.asarray(pcd.normals)).to(device).float()

        # 3. Run NKSR
        reconstructor = nksr.Reconstructor(device)
        # detail determines the resolution
        field = reconstructor.reconstruct(points, normals)
        mesh_nksr = field.extract_mesh(voxel_size=self._config.voxel_size)

        # 4. Save artifacts
        artifact_root.mkdir(parents=True, exist_ok=True)
        mesh_path = artifact_root / "reconstruction_mesh.ply"
        mesh_nksr.save(str(mesh_path))

        # NKSR output is a mesh. We might want to export a point cloud from it too
        # to satisfy the ReconstructionArtifacts contract's reference_cloud_path.
        # Or just use the input cloud if it's already aligned.
        # The contract says: "reference_cloud_path: Filesystem path to the normalized world-space reference cloud."
        # Usually this means the point cloud extracted from the reconstruction.

        # Load the mesh back to Open3D to extract points or just save it.
        o3d_mesh = o3d.io.read_triangle_mesh(str(mesh_path))
        pcd_reconstructed = o3d_mesh.sample_points_uniformly(number_of_points=len(pcd.points))

        reconstructed_cloud_path = artifact_root / "reconstruction_cloud.ply"
        o3d.io.write_point_cloud(str(reconstructed_cloud_path), pcd_reconstructed)

        metadata = ReconstructionMetadata(
            method_id=self.method_id,
            point_count=len(pcd_reconstructed.points),
            target_frame="world",
            config_dump=self._config.model_dump(mode="json"),
        )
        metadata_path = artifact_root / "reconstruction_metadata.json"
        with metadata_path.open("w") as f:
            json.dump(metadata.model_dump(mode="json"), f, indent=2)

        return ReconstructionArtifacts(
            reference_cloud_path=reconstructed_cloud_path,
            metadata_path=metadata_path,
            mesh_path=mesh_path,
        )


__all__ = ["NksrBackend"]
