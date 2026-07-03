"""Screened Poisson surface reconstruction backend.

This module implements the Poisson backend using Open3D's implementation.
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
    from .config import PoissonBackendConfig


class PoissonBackend:
    """Reconstruct a surface mesh from a point cloud using Screened Poisson."""

    method_id = ReconstructionMethodId.POISSON

    def __init__(self, config: PoissonBackendConfig, **_kwargs: Any) -> None:
        self._config = config

    def run_sequence(
        self,
        observations: Iterable[Observation],
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Poisson does not integrate RGB-D sequences directly; it merges them into a cloud first."""
        raise NotImplementedError(
            "Poisson backend does not support direct RGB-D sequence integration. "
            "Use a point-cloud input source instead."
        )

    def run_point_cloud(
        self,
        point_cloud_path: Path,
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Run Screened Poisson on a pre-aligned point cloud."""
        import open3d as o3d

        # 1. Load point cloud
        pcd = o3d.io.read_point_cloud(str(point_cloud_path))
        if pcd.is_empty():
            raise RuntimeError(f"Input point cloud is empty: {point_cloud_path}")

        # 2. Estimate normals
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=self._config.normal_radius_m,
                max_nn=self._config.normal_max_nn,
            )
        )
        pcd.orient_normals_consistent_tangent_plane(k=self._config.normal_max_nn)

        # 3. Run Poisson
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=self._config.depth,
            width=self._config.width,
            scale=self._config.scale,
            linear_fit=self._config.linear_fit,
        )

        # Trim low-density areas
        if self._config.density_quantile > 0:
            densities = np.asarray(densities)
            density_threshold = np.quantile(densities, self._config.density_quantile)
            vertices_to_remove = densities < density_threshold
            mesh.remove_vertices_by_mask(vertices_to_remove)

        # 4. Save artifacts
        artifact_root.mkdir(parents=True, exist_ok=True)
        mesh_path = artifact_root / "reconstruction_mesh.ply"
        o3d.io.write_triangle_mesh(str(mesh_path), mesh)

        pcd_reconstructed = mesh.sample_points_uniformly(number_of_points=len(pcd.points))
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


__all__ = ["PoissonBackend"]
