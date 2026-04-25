"""Tests for package-root public export surfaces."""

from __future__ import annotations

import importlib

import pytest

import prml_vslam.interfaces as interfaces_package
import prml_vslam.methods as methods_package
import prml_vslam.pipeline as pipeline_package
import prml_vslam.reconstruction as reconstruction_package
import prml_vslam.sources as sources_package
import prml_vslam.sources.replay as replay_package


def test_interfaces_package_exports_only_canonical_pose_surface() -> None:
    assert "Observation" in interfaces_package.__all__
    assert "ObservationSequenceRef" in interfaces_package.__all__
    assert not hasattr(interfaces_package, "SE3Pose")


def test_sources_package_exports_source_owned_contracts() -> None:
    assert "FileObservationSequenceLoader" in sources_package.__all__
    assert "PreparedBenchmarkInputs" in sources_package.__all__
    assert "SequenceManifest" in sources_package.__all__


def test_replay_package_exports_only_replay_primitives() -> None:
    assert "ImageSequenceObservationSource" in replay_package.__all__
    assert "Image" + "Sequence" + "Row" not in replay_package.__all__
    assert "PyAvVideoObservationSource" in replay_package.__all__
    assert "ObservationStream" in replay_package.__all__
    assert not hasattr(replay_package, "Record3DStreamConfig")
    assert not hasattr(replay_package, "Record3DWifiSession")


def test_pipeline_package_exports_only_minimal_public_surface() -> None:
    assert "RunConfig" in pipeline_package.__all__
    assert "RunService" in pipeline_package.__all__
    assert "StageKey" in pipeline_package.__all__
    assert not hasattr(pipeline_package, "PipelineSessionService")
    assert not hasattr(pipeline_package, "PipelineSessionSnapshot")


def test_pipeline_contracts_package_is_not_a_compatibility_hub() -> None:
    contracts_package = importlib.import_module("prml_vslam.pipeline.contracts")

    deleted_request_symbol = "Run" + "Request"
    assert deleted_request_symbol not in dir(pipeline_package)
    assert deleted_request_symbol not in dir(contracts_package)


def test_methods_package_exports_slam_surfaces() -> None:
    assert "SlamUpdate" in methods_package.__all__
    assert "VistaSlamBackend" in methods_package.__all__


def test_vista_package_is_the_only_canonical_vista_surface() -> None:
    vista_package = importlib.import_module("prml_vslam.methods.vista")

    assert "VistaSlamBackend" in vista_package.__all__
    assert "VistaSlamRuntime" in vista_package.__all__
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("prml_vslam.methods.vista_slam")


def test_reconstruction_package_exports_runtime_surfaces_without_harness() -> None:
    assert "Open3dTsdfBackend" in reconstruction_package.__all__
    assert "OfflineReconstructionBackend" in reconstruction_package.__all__
    assert "FileObservationSequenceLoader" not in reconstruction_package.__all__
    assert "Reconstruction" + "Session" not in reconstruction_package.__all__
    assert "Streaming" + "Reconstruction" + "Backend" not in reconstruction_package.__all__
    assert not hasattr(reconstruction_package, "ReconstructionHarness")
