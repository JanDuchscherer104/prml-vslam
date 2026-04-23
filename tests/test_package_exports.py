"""Tests for package-root public export surfaces."""

from __future__ import annotations

import importlib

import pytest

import prml_vslam.interfaces as interfaces_package
import prml_vslam.io as io_package
import prml_vslam.methods as methods_package
import prml_vslam.pipeline as pipeline_package
import prml_vslam.reconstruction as reconstruction_package


def test_interfaces_package_exports_only_canonical_pose_surface() -> None:
    assert interfaces_package.__all__ == [
        "AdvioManifestAssets",
        "AdvioRawPoseRefs",
        "CameraIntrinsics",
        "CameraIntrinsicsSample",
        "CameraIntrinsicsSeries",
        "FramePacket",
        "FramePacketProvenance",
        "FrameTransform",
        "GroundAlignmentMetadata",
        "GroundPlaneModel",
        "GroundPlaneVisualizationHint",
        "PreparedBenchmarkInputs",
        "Record3DTransportId",
        "ReferenceCloudRef",
        "ReferencePointCloudSequenceRef",
        "ReferenceTrajectoryRef",
        "RGBD_OBSERVATION_SEQUENCE_FORMAT",
        "RgbdObservation",
        "RgbdObservationIndexEntry",
        "RgbdObservationProvenance",
        "RgbdObservationSequenceIndex",
        "RgbdObservationSequenceRef",
        "SequenceManifest",
        "SlamArtifacts",
        "VisualizationArtifacts",
    ]
    assert not hasattr(interfaces_package, "SE3Pose")


def test_io_package_exports_only_minimal_public_surface() -> None:
    assert io_package.__all__ == [
        "Cv2FrameProducer",
        "Cv2ProducerConfig",
        "Cv2ReplayMode",
        "Record3DStreamConfig",
    ]
    assert not hasattr(io_package, "Record3DStreamSnapshot")
    assert not hasattr(io_package, "Record3DWifiSession")


def test_pipeline_package_exports_only_minimal_public_surface() -> None:
    assert pipeline_package.__all__ == [
        "PipelineMode",
        "RunPlan",
        "RunSummary",
    ]
    assert not hasattr(pipeline_package, "PipelineSessionService")
    assert not hasattr(pipeline_package, "PipelineSessionSnapshot")


def test_pipeline_contracts_package_is_not_a_compatibility_hub() -> None:
    contracts_package = importlib.import_module("prml_vslam.pipeline.contracts")

    assert not hasattr(pipeline_package, "RunRequest")
    assert not hasattr(contracts_package, "RunRequest")


def test_methods_package_exports_slam_surfaces() -> None:
    assert methods_package.__all__ == [
        "MethodId",
        "MockSlamBackendConfig",
        "VistaSlamBackend",
        "VistaSlamBackendConfig",
    ]
    assert not hasattr(methods_package, "MockMethodConfig")


def test_vista_package_is_the_only_canonical_vista_surface() -> None:
    vista_package = importlib.import_module("prml_vslam.methods.vista")

    assert vista_package.__all__ == [
        "VistaSlamBackend",
        "VistaSlamBackendConfig",
        "VistaSlamRuntime",
    ]
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("prml_vslam.methods.vista_slam")


def test_reconstruction_package_exports_runtime_surfaces_without_harness() -> None:
    assert reconstruction_package.__all__ == [
        "Open3dTsdfBackend",
        "Open3dTsdfBackendConfig",
        "FileRgbdObservationSource",
        "OfflineReconstructionBackend",
        "ReconstructionArtifacts",
        "ReconstructionBackendConfig",
        "ReconstructionMetadata",
        "ReconstructionMethodId",
        "ReconstructionObservation",
        "ReconstructionSession",
        "StreamingReconstructionBackend",
    ]
    assert not hasattr(reconstruction_package, "ReconstructionHarness")
