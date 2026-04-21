"""Minimal Open3D TSDF reconstruction backend."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from prml_vslam.interfaces import RgbdObservation
from prml_vslam.utils.geometry import write_point_cloud_ply

from .config import Open3dTsdfBackendConfig, ReconstructionBackendConfig
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
)


class Open3dTsdfBackend:
    """Reconstruct one world-space reference cloud using Open3D TSDF fusion."""

    method_id = ReconstructionMethodId.OPEN3D_TSDF

    def __init__(self, config: Open3dTsdfBackendConfig) -> None:
        self._config = config

    def run_sequence(
        self,
        observations: Iterable[RgbdObservation],
        *,
        backend_config: ReconstructionBackendConfig,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Integrate one offline RGB-D sequence into a fused world-space cloud."""
        if not isinstance(backend_config, Open3dTsdfBackendConfig):
            raise TypeError(f"Open3dTsdfBackend requires Open3dTsdfBackendConfig, got {type(backend_config).__name__}.")

        ordered_observations = list(observations)
        if not ordered_observations:
            raise ValueError("Open3D TSDF reconstruction requires at least one observation.")

        o3d = _import_open3d()
        volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=backend_config.voxel_length_m,
            sdf_trunc=backend_config.sdf_trunc_m,
            color_type=(
                o3d.pipelines.integration.TSDFVolumeColorType.RGB8
                if backend_config.integrate_color
                else o3d.pipelines.integration.TSDFVolumeColorType.NoColor
            ),
            volume_unit_resolution=backend_config.volume_unit_resolution,
            depth_sampling_stride=backend_config.depth_sampling_stride,
        )

        for observation in ordered_observations:
            rgbd_image, intrinsic = _rgbd_image_and_intrinsic(
                o3d,
                observation,
                depth_scale=backend_config.depth_scale,
                depth_trunc_m=backend_config.depth_trunc_m,
                convert_rgb_to_intensity=backend_config.convert_rgb_to_intensity,
                integrate_color=backend_config.integrate_color,
            )
            extrinsic_world_to_camera = np.linalg.inv(observation.T_world_camera.as_matrix())
            volume.integrate(rgbd_image, intrinsic, extrinsic_world_to_camera)

        point_cloud = volume.extract_point_cloud()
        points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
        if points_xyz.size == 0:
            raise RuntimeError("Open3D TSDF reconstruction produced an empty point cloud.")

        artifact_root.mkdir(parents=True, exist_ok=True)
        reference_cloud_path = write_point_cloud_ply(artifact_root / "reference_cloud.ply", points_xyz)

        mesh_path: Path | None = None
        if backend_config.extract_mesh:
            mesh = volume.extract_triangle_mesh()
            mesh_path = (artifact_root / "reference_mesh.ply").resolve()
            if not o3d.io.write_triangle_mesh(mesh_path, mesh, write_ascii=True):
                raise RuntimeError(f"Failed to write Open3D TSDF mesh to '{mesh_path}'.")

        metadata = ReconstructionMetadata(
            method_id=self.method_id,
            observation_count=len(ordered_observations),
            point_count=int(points_xyz.shape[0]),
            target_frame=ordered_observations[0].T_world_camera.target_frame,
            voxel_length_m=backend_config.voxel_length_m,
            sdf_trunc_m=backend_config.sdf_trunc_m,
            depth_trunc_m=backend_config.depth_trunc_m,
            depth_scale=backend_config.depth_scale,
            integrate_color=backend_config.integrate_color,
        )
        metadata_path = (artifact_root / "reconstruction_metadata.json").resolve()
        metadata_path.write_text(json.dumps(metadata.model_dump(mode="json"), indent=2), encoding="utf-8")

        return ReconstructionArtifacts(
            reference_cloud_path=reference_cloud_path,
            metadata_path=metadata_path,
            mesh_path=mesh_path,
        )


def _import_open3d():
    try:
        import open3d as o3d
    except ModuleNotFoundError as exc:
        raise RuntimeError("Reconstruction requires the repository Open3D dependency.") from exc
    return o3d


def _rgbd_image_and_intrinsic(
    o3d,
    observation: RgbdObservation,
    *,
    depth_scale: float,
    depth_trunc_m: float,
    convert_rgb_to_intensity: bool,
    integrate_color: bool,
):
    depth_map_m = np.asarray(observation.depth_map_m, dtype=np.float32)
    if depth_map_m.ndim != 2:
        raise ValueError(f"Expected a 2D depth map, got shape {depth_map_m.shape}.")
    if not np.all(np.isfinite(depth_map_m)):
        raise ValueError("Depth map must contain only finite values.")
    if np.any(depth_map_m < 0.0):
        raise ValueError("Depth map must not contain negative values.")

    height_px, width_px = depth_map_m.shape
    intrinsics = observation.camera_intrinsics
    if intrinsics.width_px is not None and intrinsics.width_px != width_px:
        raise ValueError(
            f"Intrinsics width_px={intrinsics.width_px} does not match depth width {width_px} "
            f"for observation seq={observation.seq}."
        )
    if intrinsics.height_px is not None and intrinsics.height_px != height_px:
        raise ValueError(
            f"Intrinsics height_px={intrinsics.height_px} does not match depth height {height_px} "
            f"for observation seq={observation.seq}."
        )

    image_rgb = observation.image_rgb
    if image_rgb is None:
        if integrate_color:
            raise ValueError(f"Open3D TSDF color integration requires image_rgb for observation seq={observation.seq}.")
        color_rgb = np.zeros((height_px, width_px, 3), dtype=np.uint8)
    else:
        color_rgb = np.asarray(image_rgb, dtype=np.uint8)
        if color_rgb.shape != (height_px, width_px, 3):
            raise ValueError(
                f"Expected RGB image shape {(height_px, width_px, 3)} for observation seq={observation.seq}, "
                f"got {color_rgb.shape}."
            )

    rgbd_image = o3d.geometry.RGBDImage.create_from_color_and_depth(
        o3d.geometry.Image(color_rgb),
        o3d.geometry.Image(depth_map_m),
        depth_scale=depth_scale,
        depth_trunc=depth_trunc_m,
        convert_rgb_to_intensity=convert_rgb_to_intensity,
    )
    intrinsic = o3d.camera.PinholeCameraIntrinsic(
        width_px,
        height_px,
        intrinsics.fx,
        intrinsics.fy,
        intrinsics.cx,
        intrinsics.cy,
    )
    return rgbd_image, intrinsic


__all__ = ["Open3dTsdfBackend"]
