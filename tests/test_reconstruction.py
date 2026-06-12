"""Tests for NKSR and Poisson reconstruction backends."""

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
    NksrBackend,
    NksrBackendConfig,
    PoissonBackend,
    PoissonBackendConfig,
    ReconstructionMethodId,
)
from prml_vslam.reconstruction.protocols import OfflineReconstructionBackend
from prml_vslam.utils.geometry import load_point_cloud_ply, write_point_cloud_ply


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


def test_nksr_backend_config_defaults_to_expected_method() -> None:
    config = NksrBackendConfig()

    assert config.method_id is ReconstructionMethodId.NKSR
    assert config.display_name == "Neural Kernel Surface Reconstruction"


def test_poisson_backend_config_defaults_to_expected_method() -> None:
    config = PoissonBackendConfig()

    assert config.method_id is ReconstructionMethodId.POISSON
    assert config.display_name == "Screened Poisson Surface Reconstruction"


def test_reconstruction_config_builds_nksr_offline_backend() -> None:
    backend = NksrBackendConfig().setup_target()

    assert isinstance(backend, NksrBackend)
    assert isinstance(backend, OfflineReconstructionBackend)
    assert backend.method_id is ReconstructionMethodId.NKSR


def test_reconstruction_config_builds_poisson_offline_backend() -> None:
    backend = PoissonBackendConfig().setup_target()

    assert isinstance(backend, PoissonBackend)
    assert isinstance(backend, OfflineReconstructionBackend)
    assert backend.method_id is ReconstructionMethodId.POISSON


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


def test_poisson_backend_reconstructs_from_aligned_point_cloud(tmp_path: Path) -> None:
    pytest.importorskip("open3d")
    # Use random points to avoid degenerate geometry errors in normal orientation
    points = np.random.rand(100, 3)
    
    source_cloud_path = write_point_cloud_ply(
        tmp_path / "point_cloud_sim3_icp_aligned.ply",
        points
    )
    backend = PoissonBackendConfig(depth=5).setup_target()

    artifacts = backend.run_point_cloud(
        source_cloud_path,
        artifact_root=tmp_path / "reference",
    )

    assert artifacts.reference_cloud_path.exists()
    assert artifacts.metadata_path.exists()
    assert artifacts.mesh_path is not None
    assert artifacts.mesh_path.exists()

    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["method_id"] == "poisson"


@pytest.mark.skipif(True, reason="NKSR requires GPU and specific environment usually not available in CI")
def test_nksr_backend_reconstructs_from_aligned_point_cloud(tmp_path: Path) -> None:
    pytest.importorskip("nksr")
    pytest.importorskip("torch")
    
    points = np.random.rand(100, 3)
    source_cloud_path = write_point_cloud_ply(
        tmp_path / "point_cloud_sim3_icp_aligned.ply",
        points
    )
    backend = NksrBackendConfig(voxel_size=0.1).setup_target()

    artifacts = backend.run_point_cloud(
        source_cloud_path,
        artifact_root=tmp_path / "reference",
    )

    assert artifacts.reference_cloud_path.exists()
    assert artifacts.mesh_path is not None
    
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert metadata["method_id"] == "nksr"
