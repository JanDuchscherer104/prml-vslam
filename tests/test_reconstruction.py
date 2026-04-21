"""Tests for the minimal reconstruction harness and Open3D backend."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.interfaces import CameraIntrinsics, FrameTransform
from prml_vslam.interfaces.rgbd import RgbdObservation
from prml_vslam.reconstruction import (
    Open3dTsdfBackend,
    Open3dTsdfBackendConfig,
    ReconstructionHarness,
    ReconstructionMethodId,
    ReconstructionObservation,
)
from prml_vslam.utils.geometry import load_point_cloud_ply


def _pose_identity() -> FrameTransform:
    return FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0)


def _observation(
    *,
    seq: int = 0,
    timestamp_ns: int = 0,
    depth_m: float = 1.0,
    with_rgb: bool = False,
) -> ReconstructionObservation:
    depth_map_m = np.full((32, 32), depth_m, dtype=np.float32)
    image_rgb = None if not with_rgb else np.full((32, 32, 3), 127, dtype=np.uint8)
    return RgbdObservation(
        seq=seq,
        timestamp_ns=timestamp_ns,
        T_world_camera=_pose_identity(),
        camera_intrinsics=CameraIntrinsics(
            fx=32.0,
            fy=32.0,
            cx=15.5,
            cy=15.5,
            width_px=32,
            height_px=32,
        ),
        image_rgb=image_rgb,
        depth_map_m=depth_map_m,
    )


def test_open3d_tsdf_backend_config_defaults_to_expected_method() -> None:
    config = Open3dTsdfBackendConfig()

    assert config.method_id is ReconstructionMethodId.OPEN3D_TSDF
    assert config.display_name == "Open3D TSDF"


def test_reconstruction_harness_builds_open3d_backend() -> None:
    harness = ReconstructionHarness(Open3dTsdfBackendConfig())

    backend = harness.build_backend()

    assert isinstance(backend, Open3dTsdfBackend)
    assert backend.method_id is ReconstructionMethodId.OPEN3D_TSDF


def test_reconstruction_observation_alias_accepts_legacy_pose_name() -> None:
    observation = ReconstructionObservation(
        seq=0,
        timestamp_ns=0,
        pose_world_camera=_pose_identity(),
        camera_intrinsics=CameraIntrinsics(
            fx=32.0,
            fy=32.0,
            cx=15.5,
            cy=15.5,
            width_px=32,
            height_px=32,
        ),
        depth_map_m=np.ones((32, 32), dtype=np.float32),
    )

    assert isinstance(observation, RgbdObservation)
    assert observation.pose_world_camera == observation.T_world_camera


def test_reconstruction_harness_runs_minimal_open3d_tsdf_sequence(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    harness = ReconstructionHarness(
        Open3dTsdfBackendConfig(
            voxel_length_m=0.05,
            sdf_trunc_m=0.15,
            depth_trunc_m=2.0,
        )
    )

    artifacts = harness.run_sequence((_observation() for _ in range(1)), artifact_root=tmp_path / "reference")

    assert artifacts.reference_cloud_path.exists()
    assert artifacts.metadata_path.exists()
    assert artifacts.mesh_path is None

    points_xyz = load_point_cloud_ply(artifacts.reference_cloud_path)
    assert points_xyz.shape[0] > 0
    assert points_xyz.shape[1] == 3

    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["method_id"] == "open3d_tsdf"
    assert metadata["observation_count"] == 1
    assert metadata["target_frame"] == "world"


def test_open3d_tsdf_backend_rejects_color_integration_without_rgb(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    harness = ReconstructionHarness(Open3dTsdfBackendConfig(integrate_color=True))

    with pytest.raises(ValueError, match="requires image_rgb"):
        harness.run_sequence([_observation(with_rgb=False)], artifact_root=tmp_path / "reference")


def test_rgbd_observation_rejects_mismatched_raster_shapes() -> None:
    with pytest.raises(ValidationError, match="Expected RGB image shape"):
        ReconstructionObservation(
            seq=0,
            timestamp_ns=0,
            T_world_camera=_pose_identity(),
            camera_intrinsics=CameraIntrinsics(
                fx=32.0,
                fy=32.0,
                cx=15.5,
                cy=15.5,
                width_px=32,
                height_px=32,
            ),
            image_rgb=np.zeros((16, 16, 3), dtype=np.uint8),
            depth_map_m=np.ones((32, 32), dtype=np.float32),
        )
