"""Tests for the target source stage runtime."""

from __future__ import annotations

from pathlib import Path

from prml_vslam.benchmark.contracts import ReferenceSource
from prml_vslam.interfaces.ingest import (
    PreparedBenchmarkInputs,
    ReferenceTrajectoryRef,
    SequenceManifest,
    SourceStageOutput,
)
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.request import RunRequest, VideoSourceSpec
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.source.runtime import SourceRuntime, SourceRuntimeInput
from prml_vslam.utils import RunArtifactPaths


class _ManifestOnlySource:
    label = "manifest-only"

    def __init__(self, *, rgb_dir: Path) -> None:
        self._rgb_dir = rgb_dir

    def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
        del output_dir
        return SequenceManifest(sequence_id="video-seq", rgb_dir=self._rgb_dir)


class _BenchmarkSource(_ManifestOnlySource):
    def __init__(self, *, rgb_dir: Path, reference_path: Path) -> None:
        super().__init__(rgb_dir=rgb_dir)
        self._reference_path = reference_path

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        return PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(
                    source=ReferenceSource.GROUND_TRUTH,
                    path=self._reference_path,
                )
            ]
        )


def _request(tmp_path: Path) -> RunRequest:
    return RunRequest(
        experiment_name="source-runtime",
        output_dir=tmp_path / ".artifacts",
        source=VideoSourceSpec(video_path=Path("captures/demo.mp4")),
        slam={"backend": {"method_id": "mock"}},
    )


def test_source_runtime_outputs_manifest_without_benchmark_inputs(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "prepared-rgb"
    rgb_dir.mkdir()
    runtime = SourceRuntime(source=_ManifestOnlySource(rgb_dir=rgb_dir))
    artifact_root = tmp_path / "run"

    result = runtime.run_offline(SourceRuntimeInput(request=_request(tmp_path), artifact_root=artifact_root))

    assert result.stage_key is StageKey.INGEST
    assert result.outcome.status is StageStatus.COMPLETED
    assert isinstance(result.payload, SourceStageOutput)
    assert result.payload.sequence_manifest.sequence_id == "video-seq"
    assert result.payload.sequence_manifest.rgb_dir == rgb_dir
    assert result.payload.benchmark_inputs is None
    run_paths = RunArtifactPaths.build(artifact_root)
    assert run_paths.sequence_manifest_path.exists()
    assert not run_paths.benchmark_inputs_path.exists()
    assert set(result.outcome.artifacts) == {"sequence_manifest", "rgb_dir", "rotation_metadata"}
    assert runtime.status().lifecycle_state is StageStatus.COMPLETED


def test_source_runtime_preserves_benchmark_inputs_and_artifacts(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "prepared-rgb"
    rgb_dir.mkdir()
    reference_path = tmp_path / "reference.tum"
    reference_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    runtime = SourceRuntime(source=_BenchmarkSource(rgb_dir=rgb_dir, reference_path=reference_path))
    artifact_root = tmp_path / "run"

    result = runtime.run_offline(SourceRuntimeInput(request=_request(tmp_path), artifact_root=artifact_root))

    assert isinstance(result.payload, SourceStageOutput)
    assert result.payload.benchmark_inputs is not None
    assert result.payload.benchmark_inputs.trajectory_for_source(ReferenceSource.GROUND_TRUTH) is not None
    run_paths = RunArtifactPaths.build(artifact_root)
    assert run_paths.sequence_manifest_path.exists()
    assert run_paths.benchmark_inputs_path.exists()
    assert "benchmark_inputs" in result.outcome.artifacts
    assert "reference_tum:ground_truth" in result.outcome.artifacts
