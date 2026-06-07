"""Minimal Open3D TSDF reconstruction backend.

This module is the first executable reconstruction implementation. It adapts
repo-normalized RGB-D observations into Open3D's ScalableTSDFVolume API and
writes normalized reconstruction artifacts without owning pipeline stage
policy, benchmark enablement, or Rerun logging.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from prml_vslam.interfaces import Observation
from prml_vslam.utils.geometry import write_point_cloud_ply

from prml_vslam.reconstruction.stage.contracts import ReconstructionStageInput

from .config import Open3dTsdfBackendConfig
from .contracts import (
    ReconstructionArtifacts,
    ReconstructionMetadata,
    ReconstructionMethodId,
)


class Open3dTsdfBackend:
    """Reconstruct one world-space reference cloud using Open3D TSDF fusion.

    The backend expects each observation to provide metric depth in meters,
    matching intrinsics, optional RGB, and a canonical ``T_world_camera`` pose.
    It implements the reconstruction package protocol directly against the
    repository-pinned Open3D API.
    """

    method_id = ReconstructionMethodId.OPEN3D_TSDF

    def __init__(self, config: Open3dTsdfBackendConfig, input_payload: ReconstructionStageInput | None = None) -> None:
        self._config = config
        self._input_payload = input_payload

    def run_sequence(
        self,
        observations: Iterable[Observation],
        *,
        artifact_root: Path,
    ) -> ReconstructionArtifacts:
        """Integrate one offline RGB-D sequence into a fused world-space cloud.

        The output point cloud is extracted in the observation world frame and
        persisted as ``reconstruction_cloud.ply`` alongside typed side metadata.
        """
        config = self._config
        ordered_observations = list(observations)
        if not ordered_observations:
            raise ValueError("Open3D TSDF reconstruction requires at least one observation.")

        o3d = _import_open3d()
        volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=config.voxel_length_m,
            sdf_trunc=config.sdf_trunc_m,
            color_type=(
                o3d.pipelines.integration.TSDFVolumeColorType.RGB8
                if config.integrate_color
                else o3d.pipelines.integration.TSDFVolumeColorType.NoColor
            ),
            volume_unit_resolution=config.volume_unit_resolution,
            depth_sampling_stride=config.depth_sampling_stride,
        )

        traj_timestamps = None
        traj_poses = None
        if self._input_payload is not None and self._input_payload.aligned_trajectory is not None:
            # Parse TUM trajectory
            traj_timestamps_list = []
            traj_poses_list = []
            from scipy.spatial.transform import Rotation
            with open(self._input_payload.aligned_trajectory.path, "r") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    parts = line.strip().split()
                    if len(parts) != 8:
                        continue
                    ts = float(parts[0])
                    tx, ty, tz = float(parts[1]), float(parts[2]), float(parts[3])
                    qx, qy, qz, qw = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                    
                    rot = Rotation.from_quat([qx, qy, qz, qw]).as_matrix()
                    pose = np.eye(4, dtype=np.float64)
                    pose[:3, :3] = rot
                    pose[:3, 3] = [tx, ty, tz]
                    
                    traj_timestamps_list.append(ts)
                    traj_poses_list.append(pose)
            
            if traj_timestamps_list:
                traj_timestamps = np.asarray(traj_timestamps_list, dtype=np.float64)
                traj_poses = np.asarray(traj_poses_list, dtype=np.float64)

        matched_observations = 0
        for observation in ordered_observations:
            if traj_timestamps is not None and traj_poses is not None:
                # Match timestamp to trajectory
                diffs = np.abs(traj_timestamps - (observation.timestamp_ns / 1e9))
                min_idx = int(np.argmin(diffs))
                if diffs[min_idx] > 0.01:
                    continue
                pose_matrix = traj_poses[min_idx]
            else:
                if observation.T_world_camera is None:
                    continue
                pose_matrix = observation.T_world_camera.as_matrix()

            matched_observations += 1

            rgbd_image, intrinsic = _rgbd_image_and_intrinsic(
                o3d,
                observation,
                depth_scale=config.depth_scale,
                depth_trunc_m=config.depth_trunc_m,
                convert_rgb_to_intensity=config.convert_rgb_to_intensity,
                integrate_color=config.integrate_color,
            )
            extrinsic_world_to_camera = np.linalg.inv(pose_matrix)
            volume.integrate(rgbd_image, intrinsic, extrinsic_world_to_camera)

        if matched_observations == 0:
            raise RuntimeError("No observations matched the trajectory for TSDF integration.")

        point_cloud = volume.extract_point_cloud()
        points_xyz = np.asarray(point_cloud.points, dtype=np.float64)
        if points_xyz.size == 0:
            raise RuntimeError("Open3D TSDF reconstruction produced an empty point cloud.")

        artifact_root.mkdir(parents=True, exist_ok=True)
        colors_rgb = np.asarray(point_cloud.colors, dtype=np.float64) if point_cloud.has_colors() else None
        reference_cloud_path = write_point_cloud_ply(artifact_root / "reconstruction_cloud.ply", points_xyz, colors_rgb=colors_rgb)

        mesh_path: Path | None = None
        if config.extract_mesh:
            mesh = volume.extract_triangle_mesh()
            mesh_path = (artifact_root / "reconstruction_mesh.ply").resolve()
            if not o3d.io.write_triangle_mesh(mesh_path.as_posix(), mesh, write_ascii=True):
                raise RuntimeError(f"Failed to write Open3D TSDF mesh to '{mesh_path}'.")

        metadata = ReconstructionMetadata(
            method_id=self.method_id,
            observation_count=matched_observations,
            point_count=int(points_xyz.shape[0]),
            target_frame=ordered_observations[0].T_world_camera.target_frame if ordered_observations[0].T_world_camera else "world",
            voxel_length_m=config.voxel_length_m,
            sdf_trunc_m=config.sdf_trunc_m,
            depth_trunc_m=config.depth_trunc_m,
            depth_scale=config.depth_scale,
            integrate_color=config.integrate_color,
        )
        metadata_dict = metadata.model_dump(mode="json")
        if self._input_payload is not None and self._input_payload.cloud_alignment is not None:
            metadata_dict["cloud_alignment"] = json.loads(self._input_payload.cloud_alignment.path.read_text(encoding="utf-8"))

        metadata_path = (artifact_root / "reconstruction_metadata.json").resolve()
        metadata_path.write_text(json.dumps(metadata_dict, indent=2), encoding="utf-8")

        return ReconstructionArtifacts(
            reference_cloud_path=reference_cloud_path,
            metadata_path=metadata_path,
            mesh_path=mesh_path,
        )


# TODO: this is a shared util helper!
def _import_open3d():
    try:
        import open3d as o3d
    except ModuleNotFoundError as exc:
        raise RuntimeError("Reconstruction requires the repository Open3D dependency.") from exc
    return o3d


# TODO: This is a shared i/o helper that convers our canonical Observation into Open3D types. Where should we optimally define this so that it can be shared? Also fix: passing o3d like this kills typing support!
def _rgbd_image_and_intrinsic(
    o3d,
    observation: Observation,
    *,
    depth_scale: float,
    depth_trunc_m: float,
    convert_rgb_to_intensity: bool,
    integrate_color: bool,
):
    if observation.depth_m is None:
        raise ValueError(f"Open3D TSDF requires depth_m for observation seq={observation.seq}.")
    if observation.intrinsics is None:
        raise ValueError(f"Open3D TSDF requires intrinsics for observation seq={observation.seq}.")
    if observation.T_world_camera is None:
        raise ValueError(f"Open3D TSDF requires T_world_camera for observation seq={observation.seq}.")

    depth_map_m = np.asarray(observation.depth_m, dtype=np.float32)
    if depth_map_m.ndim != 2:
        raise ValueError(f"Expected a 2D depth map, got shape {depth_map_m.shape}.")
    if not np.all(np.isfinite(depth_map_m)):
        raise ValueError("Depth map must contain only finite values.")
    if np.any(depth_map_m < 0.0):
        raise ValueError("Depth map must not contain negative values.")

    height_px, width_px = depth_map_m.shape
    intrinsics = observation.intrinsics
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

    image_rgb = observation.rgb
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
