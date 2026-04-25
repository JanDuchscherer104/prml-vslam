"""Tests for the target source stage runtime."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
    CameraIntrinsics,
    FrameTransform,
    Observation,
    ObservationProvenance,
)
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceCloudSource,
    ReferencePointCloudSequenceRef,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
    SourceStageOutput,
)
from prml_vslam.sources.materialization import materialize_manifest
from prml_vslam.sources.runtime import SourceRuntime, SourceStageInput
from prml_vslam.sources.visualization import (
    ROLE_SOURCE_CAMERA_POSE,
    ROLE_SOURCE_CAMERA_RGB,
    ROLE_SOURCE_DEPTH,
    ROLE_SOURCE_PINHOLE,
    ROLE_SOURCE_POINTMAP,
    ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ROLE_SOURCE_REFERENCE_TRAJECTORY,
    ROLE_SOURCE_RGB,
    SourceVisualizationAdapter,
    reference_trajectory_artifact_key,
)
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


class _ReferenceGeometrySource(_ManifestOnlySource):
    def __init__(self, *, rgb_dir: Path, reference_path: Path, cloud_path: Path, metadata_path: Path) -> None:
        super().__init__(rgb_dir=rgb_dir)
        self._reference_path = reference_path
        self._cloud_path = cloud_path
        self._metadata_path = metadata_path

    def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
        output_dir.mkdir(parents=True, exist_ok=True)
        return PreparedBenchmarkInputs(
            reference_trajectories=[
                ReferenceTrajectoryRef(source=ReferenceSource.GROUND_TRUTH, path=self._reference_path)
            ],
            reference_clouds=[
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    path=self._cloud_path,
                    metadata_path=self._metadata_path,
                    target_frame="advio_gt_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                )
            ],
            reference_point_cloud_sequences=[
                ReferencePointCloudSequenceRef(
                    source=ReferenceCloudSource.TANGO_AREA_LEARNING,
                    index_path=output_dir / "point-cloud.csv",
                    payload_root=output_dir,
                    trajectory_path=output_dir / "tango_area_learning.tum",
                    target_frame="advio_tango_area_learning_world",
                    native_frame="advio_tango_area_learning_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
                )
            ],
        )


def _config_input(
    *,
    mode: PipelineMode = PipelineMode.OFFLINE,
    frame_stride: int = 1,
    streaming_max_frames: int | None = None,
) -> dict[str, object]:
    return {
        "mode": mode,
        "frame_stride": frame_stride,
        "streaming_max_frames": streaming_max_frames,
        "config_hash": "source-config",
        "input_fingerprint": "source-input",
    }


def test_source_runtime_outputs_manifest_without_benchmark_inputs(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "prepared-rgb"
    rgb_dir.mkdir()
    runtime = SourceRuntime(source=_ManifestOnlySource(rgb_dir=rgb_dir))
    artifact_root = tmp_path / "run"

    result = runtime.run_offline(SourceStageInput(**_config_input(), artifact_root=artifact_root))

    assert result.stage_key is StageKey.SOURCE
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

    result = runtime.run_offline(SourceStageInput(**_config_input(), artifact_root=artifact_root))

    assert isinstance(result.payload, SourceStageOutput)
    assert result.payload.benchmark_inputs is not None
    assert result.payload.benchmark_inputs.trajectory_for_source(ReferenceSource.GROUND_TRUTH) is not None
    run_paths = RunArtifactPaths.build(artifact_root)
    assert run_paths.sequence_manifest_path.exists()
    assert run_paths.benchmark_inputs_path.exists()
    assert "benchmark_inputs" in result.outcome.artifacts
    reference = result.payload.benchmark_inputs.trajectory_for_source(ReferenceSource.GROUND_TRUTH)
    assert reference is not None
    assert reference_trajectory_artifact_key(reference) in result.outcome.artifacts


def test_source_runtime_registers_reference_geometry_and_adapter_items(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "prepared-rgb"
    rgb_dir.mkdir()
    reference_path = tmp_path / "reference.tum"
    reference_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    cloud_path = tmp_path / "cloud.ply"
    cloud_path.write_text("ply\n", encoding="utf-8")
    metadata_path = tmp_path / "cloud.metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    runtime = SourceRuntime(
        source=_ReferenceGeometrySource(
            rgb_dir=rgb_dir,
            reference_path=reference_path,
            cloud_path=cloud_path,
            metadata_path=metadata_path,
        )
    )

    result = runtime.run_offline(SourceStageInput(**_config_input(), artifact_root=tmp_path / "run"))

    assert isinstance(result.payload, SourceStageOutput)
    assert "reference_cloud:tango_area_learning:aligned" in result.outcome.artifacts
    assert "reference_cloud_metadata:tango_area_learning:aligned" in result.outcome.artifacts
    items = SourceVisualizationAdapter().build_reference_items(
        output=result.payload,
        artifact_refs=result.outcome.artifacts,
    )
    assert [item.role for item in items] == [
        ROLE_SOURCE_REFERENCE_TRAJECTORY,
        ROLE_SOURCE_REFERENCE_TRAJECTORY,
        ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ]
    assert items[0].space == "world"
    assert items[1].space == "advio_tango_area_learning_world"
    assert items[1].metadata["reference_source"] == "tango_area_learning"
    assert items[2].space == "advio_gt_world"


def test_source_visualization_adapter_emits_posed_packet_geometry_items() -> None:
    packet = Observation(
        seq=7,
        timestamp_ns=1,
        T_world_camera=FrameTransform(
            target_frame="tum_rgbd_mocap_world",
            source_frame=CAMERA_RDF_FRAME,
            qx=0.0,
            qy=0.0,
            qz=0.0,
            qw=1.0,
            tx=1.0,
            ty=2.0,
            tz=3.0,
        ),
        intrinsics=CameraIntrinsics(fx=2.0, fy=2.0, cx=1.0, cy=1.0, width_px=4, height_px=3),
        provenance=ObservationProvenance(source_id="test"),
    )
    image_ref = TransientPayloadRef(handle_id="rgb", payload_kind="image")
    depth_ref = TransientPayloadRef(handle_id="depth", payload_kind="depth")
    pointmap_ref = TransientPayloadRef(handle_id="pointmap", payload_kind="point_cloud")

    items = SourceVisualizationAdapter().build_packet_items(
        packet=packet,
        frame_payload_ref=image_ref,
        depth_payload_ref=depth_ref,
        pointmap_payload_ref=pointmap_ref,
    )

    assert [item.role for item in items] == [
        ROLE_SOURCE_RGB,
        ROLE_SOURCE_CAMERA_POSE,
        ROLE_SOURCE_PINHOLE,
        ROLE_SOURCE_CAMERA_RGB,
        ROLE_SOURCE_DEPTH,
        ROLE_SOURCE_POINTMAP,
    ]
    assert items[1].pose == packet.T_world_camera
    assert items[2].intrinsics == packet.intrinsics
    assert items[-1].space == "camera_local"


def test_source_runtime_materialization_reuses_extraction_cache(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    run_paths.input_frames_dir.mkdir(parents=True, exist_ok=True)
    video_path = tmp_path / "captures" / "demo.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"")
    (run_paths.input_frames_dir / "000000.png").write_bytes(b"png")
    (run_paths.input_frames_dir / ".ingest_metadata.json").write_text(
        f'{{"video_path": "{video_path.resolve()}", "frame_stride": 1, "max_frames": null}}',
        encoding="utf-8",
    )
    manifest = materialize_manifest(
        input_payload=SourceStageInput(**_config_input(frame_stride=1), artifact_root=run_paths.artifact_root),
        prepared_manifest=SequenceManifest(sequence_id="ingest-cache", video_path=video_path),
        run_paths=run_paths,
    )

    assert manifest.rgb_dir == run_paths.input_frames_dir.resolve()


def test_source_runtime_materialization_normalizes_tum_rgbd_timestamps(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "rgb.txt"
    timestamps_path.write_text(
        "\n".join(
            [
                "# color images",
                "# timestamp filename",
                "0.000000000 rgb/000000.png",
                "0.200000000 rgb/000001.png",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = materialize_manifest(
        input_payload=SourceStageInput(**_config_input(), artifact_root=run_paths.artifact_root),
        prepared_manifest=SequenceManifest(
            sequence_id="freiburg1_room",
            rgb_dir=rgb_dir,
            timestamps_path=timestamps_path,
        ),
        run_paths=run_paths,
    )

    assert manifest.timestamps_path == run_paths.input_timestamps_path.resolve()
    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 200_000_000]}


def test_source_runtime_materialization_normalizes_advio_csv_timestamps(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "frames.csv"
    timestamps_path.write_text("0.000000000,1\n0.100000000,2\n", encoding="utf-8")
    manifest = materialize_manifest(
        input_payload=SourceStageInput(**_config_input(), artifact_root=run_paths.artifact_root),
        prepared_manifest=SequenceManifest(
            sequence_id="advio-15",
            rgb_dir=rgb_dir,
            timestamps_path=timestamps_path,
        ),
        run_paths=run_paths,
    )

    assert manifest.timestamps_path == run_paths.input_timestamps_path.resolve()
    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 100_000_000]}


def test_source_runtime_materialization_applies_advio_video_frame_stride(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    video_path = tmp_path / "advio" / "iphone" / "frames.mov"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"video")
    timestamps_path = tmp_path / "advio" / "iphone" / "frames.csv"
    timestamps_path.write_text(
        "0.000000000,0\n0.100000000,1\n0.200000000,2\n0.300000000,3\n",
        encoding="utf-8",
    )
    calls: list[dict[str, object]] = []

    def fake_extract_video_frames(**kwargs):
        calls.append(kwargs)
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "000000.png").write_bytes(b"png")
        (output_dir / "000001.png").write_bytes(b"png")
        return SimpleNamespace(rgb_dir=output_dir.resolve(), timestamps_ns=[0, 300_000_000])

    monkeypatch.setattr("prml_vslam.sources.materialization.extract_video_frames", fake_extract_video_frames)

    manifest = materialize_manifest(
        input_payload=SourceStageInput(**_config_input(frame_stride=3), artifact_root=run_paths.artifact_root),
        prepared_manifest=SequenceManifest(
            sequence_id="advio-15",
            video_path=video_path,
            timestamps_path=timestamps_path,
        ),
        run_paths=run_paths,
    )

    assert calls[0]["frame_stride"] == 3
    assert manifest.rgb_dir == run_paths.input_frames_dir.resolve()
    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 3, "timestamps_ns": [0, 300_000_000]}


def test_source_runtime_materialization_does_not_double_sample_dataset_timestamps(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "sampled-rgb.txt"
    timestamps_path.write_text("0.000000000 rgb/000000.png\n0.200000000 rgb/000001.png\n", encoding="utf-8")
    manifest = materialize_manifest(
        input_payload=SourceStageInput(**_config_input(frame_stride=2), artifact_root=run_paths.artifact_root),
        prepared_manifest=SequenceManifest(
            sequence_id="freiburg1_room",
            rgb_dir=rgb_dir,
            timestamps_path=timestamps_path,
        ),
        run_paths=run_paths,
    )

    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 200_000_000]}


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

    monkeypatch.setattr("prml_vslam.sources.config.AdvioDatasetService", FakeDatasetService)
    monkeypatch.setattr("prml_vslam.sources.config.TumRgbdDatasetService", FakeDatasetService)

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

    monkeypatch.setattr("prml_vslam.sources.config.Record3DStreamingSourceConfig", FakeRecord3DSourceConfig)

    record3d_source = Record3DSourceConfig(frame_stride=2).setup_target(path_config=PathConfig(root=tmp_path))

    assert record3d_source.label == "streaming-manifest"
    assert calls[0][1]["transport"].value == "usb"


class _StreamingManifestSource(_ManifestOnlySource):
    label = "streaming-manifest"

    def open_stream(self, *, loop: bool):
        del loop
        raise EOFError
