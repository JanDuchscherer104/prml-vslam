"""Tests for package-root public export surfaces."""

from __future__ import annotations

import prml_vslam.io as io_package
import prml_vslam.methods as methods_package
import prml_vslam.pipeline as pipeline_package


def test_io_package_exports_only_minimal_public_surface() -> None:
    assert io_package.__all__ == [
        "Cv2FrameProducer",
        "Cv2ProducerConfig",
        "Cv2ReplayMode",
        "Record3DStreamConfig",
        "open_cv2_replay_stream",
    ]
    assert not hasattr(io_package, "Record3DStreamSnapshot")
    assert not hasattr(io_package, "Record3DWifiSession")


def test_pipeline_package_exports_only_minimal_public_surface() -> None:
    assert pipeline_package.__all__ == [
        "PipelineMode",
        "RunPlan",
        "RunRequest",
        "SequenceManifest",
        "RunSummary",
        "SlamArtifacts",
        "SlamBackend",
        "SlamSession",
    ]
    assert not hasattr(pipeline_package, "PipelineSessionService")
    assert not hasattr(pipeline_package, "PipelineSessionSnapshot")


def test_methods_package_exports_slam_surfaces() -> None:
    assert methods_package.__all__ == [
        "MethodId",
        "MockSlamBackendConfig",
        "VistaSlamBackend",
        "VistaSlamBackendConfig",
    ]
    assert not hasattr(methods_package, "MockMethodConfig")
