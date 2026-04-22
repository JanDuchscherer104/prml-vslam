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
from prml_vslam.pipeline.stages.source.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.pipeline.stages.source.runtime import SourceRuntime, SourceRuntimeInput
from prml_vslam.utils import PathConfig, RunArtifactPaths


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


def test_video_source_config_constructs_video_adapter(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, captures_dir=tmp_path / "captures")
    path_config.captures_dir.mkdir()
    video_path = path_config.captures_dir / "demo.mp4"
    video_path.write_bytes(b"video")

    video_source = VideoSourceConfig(video_path=Path("demo.mp4"), frame_stride=2).setup_target(path_config=path_config)

    assert video_source.label == "Video 'demo.mp4'"


def test_dataset_source_configs_construct_dataset_adapters(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeDatasetService:
        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def resolve_sequence_id(self, sequence_id: str) -> str:
            return f"resolved-{sequence_id}"

        def build_streaming_source(self, **kwargs):
            calls.append(("streaming", kwargs))
            return _ManifestOnlySource(rgb_dir=tmp_path)

    monkeypatch.setattr("prml_vslam.pipeline.stages.source.config.AdvioDatasetService", FakeDatasetService)
    monkeypatch.setattr("prml_vslam.pipeline.stages.source.config.TumRgbdDatasetService", FakeDatasetService)

    path_config = PathConfig(root=tmp_path)
    tum_source = TumRgbdSourceConfig(sequence_id="freiburg1_room", target_fps=15.0).setup_target(
        path_config=path_config
    )
    advio_source = AdvioSourceConfig(sequence_id="advio-20", frame_stride=3).setup_target(path_config=path_config)

    assert tum_source.label == "manifest-only"
    assert advio_source.label == "manifest-only"
    assert calls[0][1]["sequence_id"] == "resolved-freiburg1_room"
    assert calls[0][1]["frame_selection"].target_fps == 15.0
    assert calls[1][1]["sequence_id"] == "resolved-advio-20"
    assert calls[1][1]["frame_selection"].frame_stride == 3


def test_record3d_source_config_constructs_sampled_live_adapter(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeRecord3DSourceConfig:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def setup_target(self):
            calls.append(("record3d", self.kwargs))
            return _StreamingManifestSource(rgb_dir=tmp_path)

    monkeypatch.setattr(
        "prml_vslam.pipeline.stages.source.config.Record3DStreamingSourceConfig", FakeRecord3DSourceConfig
    )

    record3d_source = Record3DSourceConfig(frame_stride=2).setup_target(path_config=PathConfig(root=tmp_path))

    assert record3d_source.label == "streaming-manifest"
    assert calls[0][1]["transport"].value == "usb"


class _StreamingManifestSource(_ManifestOnlySource):
    label = "streaming-manifest"

    def open_stream(self, *, loop: bool):
        del loop
        raise EOFError
