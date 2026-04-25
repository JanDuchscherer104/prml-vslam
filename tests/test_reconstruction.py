"""Tests for the minimal reconstruction config and Open3D backend."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
    CameraIntrinsics,
    FrameTransform,
    Observation,
    ObservationProvenance,
)
from prml_vslam.reconstruction import (
    Open3dTsdfBackend,
    Open3dTsdfBackendConfig,
    ReconstructionMethodId,
)
from prml_vslam.reconstruction.protocols import OfflineReconstructionBackend
from prml_vslam.utils.geometry import load_point_cloud_ply


def _pose_identity() -> FrameTransform:
    return FrameTransform(
        qx=0.0,
        qy=0.0,
        qz=0.0,
        qw=1.0,
        tx=0.0,
        ty=0.0,
        tz=0.0,
        source_frame=CAMERA_RDF_FRAME,
    )


def _observation(
    *,
    seq: int = 0,
    timestamp_ns: int = 0,
    depth_m: float = 1.0,
    with_rgb: bool = False,
) -> Observation:
    depth_map_m = np.full((32, 32), depth_m, dtype=np.float32)
    image_rgb = None if not with_rgb else np.full((32, 32, 3), 127, dtype=np.uint8)
    return Observation(
        seq=seq,
        timestamp_ns=timestamp_ns,
        T_world_camera=_pose_identity(),
        intrinsics=CameraIntrinsics(
            fx=32.0,
            fy=32.0,
            cx=15.5,
            cy=15.5,
            width_px=32,
            height_px=32,
        ),
        rgb=image_rgb,
        depth_m=depth_map_m,
        provenance=ObservationProvenance(source_id="test"),
    )


def test_open3d_tsdf_backend_config_defaults_to_expected_method() -> None:
    config = Open3dTsdfBackendConfig()

    assert config.method_id is ReconstructionMethodId.OPEN3D_TSDF
    assert config.display_name == "Open3D TSDF"


def test_reconstruction_config_builds_open3d_offline_backend() -> None:
    backend = Open3dTsdfBackendConfig().setup_target()

    assert isinstance(backend, Open3dTsdfBackend)
    assert isinstance(backend, OfflineReconstructionBackend)
    assert backend.method_id is ReconstructionMethodId.OPEN3D_TSDF


def test_observation_requires_camera_rdf_pose_frame() -> None:
    with pytest.raises(ValidationError, match="source_frame must be 'camera_rdf'"):
        Observation(
            seq=0,
            timestamp_ns=0,
            T_world_camera=FrameTransform(
                qx=0.0,
                qy=0.0,
                qz=0.0,
                qw=1.0,
                tx=0.0,
                ty=0.0,
                tz=0.0,
                source_frame="camera",
            ),
            provenance=ObservationProvenance(source_id="test"),
        )


def test_observation_rejects_geometry_without_pose() -> None:
    with pytest.raises(ValidationError, match="Metric observation geometry requires T_world_camera"):
        Observation(
            seq=0,
            timestamp_ns=0,
            intrinsics=CameraIntrinsics(
                fx=32.0,
                fy=32.0,
                cx=15.5,
                cy=15.5,
                width_px=32,
                height_px=32,
            ),
            depth_m=np.ones((32, 32), dtype=np.float32),
            provenance=ObservationProvenance(source_id="test"),
        )


def test_reconstruction_config_runs_minimal_open3d_tsdf_sequence(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    config = Open3dTsdfBackendConfig(
        voxel_length_m=0.05,
        sdf_trunc_m=0.15,
        depth_trunc_m=2.0,
    )
    backend = config.setup_target()

    artifacts = backend.run_sequence(
        (_observation() for _ in range(1)),
        artifact_root=tmp_path / "reference",
    )

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
    config = Open3dTsdfBackendConfig(integrate_color=True)
    backend = config.setup_target()

    with pytest.raises(ValueError, match="requires image_rgb"):
        backend.run_sequence(
            [_observation(with_rgb=False)],
            artifact_root=tmp_path / "reference",
        )


def test_observation_rejects_mismatched_raster_shapes() -> None:
    with pytest.raises(ValidationError, match="Expected RGB image shape"):
        Observation(
            seq=0,
            timestamp_ns=0,
            T_world_camera=_pose_identity(),
            intrinsics=CameraIntrinsics(
                fx=32.0,
                fy=32.0,
                cx=15.5,
                cy=15.5,
                width_px=32,
                height_px=32,
            ),
            rgb=np.zeros((16, 16), dtype=np.uint8),
            depth_m=np.ones((32, 32), dtype=np.float32),
            provenance=ObservationProvenance(source_id="test"),
        )
