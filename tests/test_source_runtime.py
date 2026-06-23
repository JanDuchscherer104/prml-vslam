"""Tests for the target source stage runtime."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from prml_vslam.interfaces import (
    CAMERA_RDF_FRAME,
    CameraIntrinsics,
    FrameTransform,
    Observation,
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.interfaces.artifacts import artifact_ref
from prml_vslam.pipeline.contracts.mode import PipelineMode
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DSourceConfig,
    TumRgbdSourceConfig,
    VideoSourceConfig,
    normalized_profile_for_source_config,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudCoordinateStatus,
    ReferenceCloudRef,
    ReferenceCloudSource,
    ReferenceSource,
    ReferenceTrajectoryRef,
    SequenceManifest,
)
from prml_vslam.sources.datasets.advio import AdvioPoseSource, AdvioServingConfig
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig
from prml_vslam.sources.datasets.normalized_source import NormalizedDatasetRuntimeSource
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
    load_timestamps_ns,
)
from prml_vslam.sources.materialization import materialize_manifest
from prml_vslam.sources.observation_reader import iter_sequence_manifest_observations
from prml_vslam.sources.protocols import OfflineSequenceSource
from prml_vslam.sources.replay import ImageSequenceObservationSource, ReplayMode, write_rgb_video
from prml_vslam.sources.stage.artifacts import reference_trajectory_artifact_key
from prml_vslam.sources.stage.contracts import SourceStageInput, SourceStageOutput
from prml_vslam.sources.stage.runtime import SourceRuntime
from prml_vslam.sources.stage.visualization import (
    ROLE_SOURCE_CAMERA_POSE,
    ROLE_SOURCE_CAMERA_RGB,
    ROLE_SOURCE_DEPTH,
    ROLE_SOURCE_PINHOLE,
    ROLE_SOURCE_POINTMAP,
    ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ROLE_SOURCE_REFERENCE_TRAJECTORY,
    ROLE_SOURCE_RGB,
    SourceVisualizationAdapter,
)
from prml_vslam.utils import PathConfig, RunArtifactPaths


def test_offline_sequence_source_label_contract_is_read_only_property() -> None:
    assert isinstance(OfflineSequenceSource.__dict__["label"], property)


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
                    target_frame="world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
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
                ReferenceTrajectoryRef(
                    source=ReferenceSource.GROUND_TRUTH,
                    path=self._reference_path,
                    target_frame="world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
                )
            ],
            reference_clouds=[
                ReferenceCloudRef(
                    source=ReferenceCloudSource.TUM_RGBD,
                    path=self._cloud_path,
                    metadata_path=self._metadata_path,
                    target_frame="tum_rgbd_world",
                    native_frame="tum_rgbd_mocap_world",
                    coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
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


def _write_rgb_manifest(
    tmp_path: Path,
    *,
    frame_count: int = 2,
    timestamps_ns: list[int] | None = None,
    source_frame_indices: list[int] | None = None,
) -> SequenceManifest:
    rgb_dir = tmp_path / "frames"
    rgb_dir.mkdir()
    for index in range(frame_count):
        frame_rgb = np.full((2, 3, 3), index + 1, dtype=np.uint8)
        cv2.imwrite(str(rgb_dir / f"{index:06d}.png"), cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
    timestamps_path = tmp_path / "timestamps.json"
    timestamps_path.write_text(
        json.dumps({"timestamps_ns": timestamps_ns or [index * 100_000_000 for index in range(frame_count)]}),
        encoding="utf-8",
    )
    source_frame_indices_path = None
    if source_frame_indices is not None:
        source_frame_indices_path = tmp_path / "source_frame_indices.json"
        source_frame_indices_path.write_text(
            json.dumps({"source_frame_indices": source_frame_indices}),
            encoding="utf-8",
        )
    return SequenceManifest(
        sequence_id="seq-rgb",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
        source_frame_indices_path=source_frame_indices_path,
    )


def _write_video_manifest(
    tmp_path: Path,
    *,
    frame_count: int = 3,
    timestamps_ns: list[int] | None = None,
    source_frame_indices: list[int] | None = None,
) -> SequenceManifest:
    frames = [np.full((4, 6, 3), index + 1, dtype=np.uint8) for index in range(frame_count)]
    video_path = write_rgb_video(tmp_path / "rgb.mp4", frames)
    timestamps_path = tmp_path / "timestamps.json"
    timestamps_path.write_text(
        json.dumps({"timestamps_ns": timestamps_ns or [index * 100_000_000 for index in range(frame_count)]}),
        encoding="utf-8",
    )
    source_frame_indices_path = None
    if source_frame_indices is not None:
        source_frame_indices_path = tmp_path / "source_frame_indices.json"
        source_frame_indices_path.write_text(
            json.dumps({"source_frame_indices": source_frame_indices}),
            encoding="utf-8",
        )
    return SequenceManifest(
        sequence_id="seq-video",
        video_path=video_path,
        rgb_dir=None,
        timestamps_path=timestamps_path,
        source_frame_indices_path=source_frame_indices_path,
    )


def test_sequence_manifest_observation_reader_yields_rgb_observations(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path, frame_count=2, timestamps_ns=[10, 20])

    observations = list(iter_sequence_manifest_observations(manifest))

    assert [observation.seq for observation in observations] == [0, 1]
    assert [observation.timestamp_ns for observation in observations] == [10, 20]
    assert observations[0].rgb is not None
    assert observations[0].rgb_path == manifest.rgb_dir / "000000.png"
    assert observations[0].rgb.shape == (2, 3, 3)
    assert observations[0].provenance.source_id == "source_manifest"
    assert observations[0].provenance.sequence_id == "seq-rgb"


def test_image_sequence_replay_loads_depth_before_pose_contract_validation(tmp_path: Path) -> None:
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cv2.imwrite(str(tmp_path / "rgb.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    depth_path = tmp_path / "depth.npy"
    np.save(depth_path, np.ones((2, 2), dtype=np.float32))
    loaded_depth_paths: list[Path] = []
    source = ImageSequenceObservationSource(
        sequence_dir=tmp_path,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb.png"),
                depth_path=Path("depth.npy"),
                intrinsics=CameraIntrinsics(fx=1.0, fy=1.0, cx=0.5, cy=0.5, width_px=2, height_px=2),
                T_world_camera=None,
                provenance=ObservationProvenance(source_id="synthetic"),
            )
        ],
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
        depth_loader=lambda path: loaded_depth_paths.append(path) or np.asarray(np.load(path), dtype=np.float32),
    )

    source.connect()
    with pytest.raises(ValueError, match="Metric observation geometry requires T_world_camera"):
        source.wait_for_observation()

    assert loaded_depth_paths == [depth_path]


def test_sequence_manifest_observation_reader_applies_max_frames(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path, frame_count=3)

    observations = list(iter_sequence_manifest_observations(manifest, max_frames=2))

    assert [observation.seq for observation in observations] == [0, 1]


def test_sequence_manifest_observation_reader_preserves_original_source_frame_indices(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(
        tmp_path,
        frame_count=4,
        timestamps_ns=[10, 20, 30, 40],
        source_frame_indices=[1, 3],
    )

    observations = list(iter_sequence_manifest_observations(manifest))

    assert [observation.seq for observation in observations] == [0, 1]
    assert [observation.timestamp_ns for observation in observations] == [20, 40]
    assert [observation.source_frame_index for observation in observations] == [1, 3]
    assert [observation.provenance.source_frame_index for observation in observations] == [1, 3]


def test_sequence_manifest_observation_reader_accepts_preselected_timestamps(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(
        tmp_path,
        frame_count=4,
        timestamps_ns=[10, 30],
        source_frame_indices=[0, 2],
    )

    observations = list(iter_sequence_manifest_observations(manifest))

    assert [int(observation.rgb[0, 0, 0]) for observation in observations if observation.rgb is not None] == [1, 3]
    assert [observation.timestamp_ns for observation in observations] == [10, 30]
    assert [observation.source_frame_index for observation in observations] == [0, 2]


def test_sequence_manifest_observation_reader_uses_observation_index_rows(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "observations" / "rgb"
    rgb_dir.mkdir(parents=True)
    for index in range(2):
        frame_rgb = np.full((2, 3, 3), index + 1, dtype=np.uint8)
        cv2.imwrite(str(rgb_dir / f"{index:06d}.png"), cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
    timestamps_path = tmp_path / "timestamps.json"
    timestamps_path.write_text(json.dumps({"timestamps_ns": [100, 200]}), encoding="utf-8")
    observation_index_path = tmp_path / "observations.json"
    observation_index_path.write_text(
        ObservationSequenceIndex(
            source_id="tum_rgbd",
            sequence_id="seq-rgb",
            observation_count=2,
            rows=[
                ObservationIndexEntry(
                    seq=0,
                    timestamp_ns=100,
                    rgb_path=Path("rgb/000000.png"),
                    provenance=ObservationProvenance(source_id="tum_rgbd", source_frame_index=16),
                ),
                ObservationIndexEntry(
                    seq=1,
                    timestamp_ns=200,
                    rgb_path=Path("rgb/000001.png"),
                    provenance=ObservationProvenance(source_id="tum_rgbd", source_frame_index=612),
                ),
            ],
        ).model_dump_json(),
        encoding="utf-8",
    )
    manifest = SequenceManifest(
        sequence_id="seq-rgb",
        rgb_dir=rgb_dir,
        timestamps_path=timestamps_path,
        observation_index_path=observation_index_path,
    )

    observations = list(iter_sequence_manifest_observations(manifest))

    assert [int(observation.rgb[0, 0, 0]) for observation in observations if observation.rgb is not None] == [1, 2]
    assert [observation.timestamp_ns for observation in observations] == [100, 200]
    assert [observation.source_frame_index for observation in observations] == [16, 612]
    assert [observation.provenance.source_frame_index for observation in observations] == [16, 612]


def test_normalized_store_source_frame_indices_sidecar_uses_original_observation_provenance(tmp_path: Path) -> None:
    payload_root = tmp_path / "entry" / "observations"
    rgb_dir = payload_root / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "entry" / "input" / "timestamps.json"
    timestamps_path.parent.mkdir(parents=True)
    timestamps_path.write_text(json.dumps({"timestamps_ns": [10, 20, 30, 40]}), encoding="utf-8")
    index_path = payload_root / "observations.json"
    rows = [
        ObservationIndexEntry(
            seq=seq,
            timestamp_ns=timestamp_ns,
            rgb_path=Path(f"rgb/{seq:06d}.png"),
            provenance=ObservationProvenance(source_id="advio", source_frame_index=source_frame_index),
        )
        for seq, (timestamp_ns, source_frame_index) in enumerate(zip([10, 20, 30, 40], [5, 9, 13, 17], strict=True))
    ]
    for row in rows:
        cv2.imwrite(str(payload_root / row.rgb_path), np.zeros((2, 3, 3), dtype=np.uint8))
    index_path.write_text(
        ObservationSequenceIndex(
            source_id="advio",
            sequence_id="advio-synthetic",
            observation_count=len(rows),
            rows=rows,
        ).model_dump_json(),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "entry" / "sequence_manifest.json"
    manifest_path.write_text(
        SequenceManifest(
            sequence_id="advio-synthetic", rgb_dir=rgb_dir, timestamps_path=timestamps_path
        ).model_dump_json(),
        encoding="utf-8",
    )
    benchmark_inputs_path = tmp_path / "entry" / "benchmark_inputs.json"
    benchmark_inputs_path.write_text(
        PreparedBenchmarkInputs(
            observation_sequences=[
                ObservationSequenceRef(
                    source_id="advio",
                    sequence_id="advio-synthetic",
                    index_path=index_path,
                    payload_root=payload_root,
                    observation_count=len(rows),
                )
            ]
        ).model_dump_json(),
        encoding="utf-8",
    )
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-synthetic",
        source_id="advio",
        source_profile={},
    )
    entry = NormalizedDatasetEntry(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-synthetic",
        source_id="advio",
        profile_key=profile.profile_key,
        profile=profile.model_dump(mode="json"),
        root=tmp_path / "entry",
        sequence_manifest_path=manifest_path,
        benchmark_inputs_path=benchmark_inputs_path,
    )

    selected = NormalizedDatasetStore(store_root=tmp_path / "store", dataset_id=DatasetId.ADVIO).read_sequence_manifest(
        entry,
        frame_selection=FrameSelectionConfig(frame_stride=2),
        output_dir=tmp_path / "run" / "input",
    )

    source_frame_indices = json.loads(selected.source_frame_indices_path.read_text(encoding="utf-8"))
    selected_observations = ObservationSequenceIndex.model_validate_json(
        selected.observation_index_path.read_text(encoding="utf-8")
    )
    assert source_frame_indices == {"source_frame_indices": [5, 13]}
    assert [row.seq for row in selected_observations.rows] == [0, 1]
    assert [row.provenance.source_frame_index for row in selected_observations.rows] == [5, 13]


def test_sequence_manifest_observation_reader_decodes_video_path_without_rgb_dir(tmp_path: Path) -> None:
    manifest = _write_video_manifest(
        tmp_path,
        frame_count=4,
        timestamps_ns=[10, 20, 30, 40],
        source_frame_indices=[1, 3],
    )

    observations = list(iter_sequence_manifest_observations(manifest))

    assert manifest.rgb_dir is None
    assert [observation.seq for observation in observations] == [0, 1]
    assert [observation.timestamp_ns for observation in observations] == [20, 40]
    assert [observation.source_frame_index for observation in observations] == [1, 3]
    assert observations[0].rgb is not None
    assert observations[0].rgb.shape == (4, 6, 3)


def test_image_sequence_replay_preserves_row_provenance_source_frame_index(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir()
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cv2.imwrite(str(rgb_dir / "000003.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    source = ImageSequenceObservationSource(
        sequence_dir=tmp_path,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb/000003.png"),
                provenance=ObservationProvenance(source_id="synthetic", source_frame_index=3),
            )
        ],
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    )

    source.connect()
    observation = source.wait_for_observation()
    source.disconnect()

    assert observation.seq == 0
    assert observation.source_frame_index == 3
    assert observation.provenance.source_frame_index == 3


def test_sequence_manifest_observation_reader_can_skip_rgb_payloads(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path, frame_count=2, timestamps_ns=[10, 20])

    observations = list(iter_sequence_manifest_observations(manifest, load_rgb=False))

    assert [observation.seq for observation in observations] == [0, 1]
    assert [observation.timestamp_ns for observation in observations] == [10, 20]
    assert [observation.rgb for observation in observations] == [None, None]
    assert [observation.rgb_path for observation in observations] == [
        manifest.rgb_dir / "000000.png",
        manifest.rgb_dir / "000001.png",
    ]
    assert observations[0].provenance.source_id == "source_manifest"
    assert observations[0].provenance.sequence_id == "seq-rgb"


def test_sequence_manifest_observation_reader_preserves_provenance_without_rgb(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path, frame_count=1).model_copy(
        update={
            "dataset_id": DatasetId.ADVIO,
            "dataset_serving": AdvioServingConfig(pose_source=AdvioPoseSource.ARCORE),
        }
    )

    loaded = list(iter_sequence_manifest_observations(manifest, load_rgb=True))
    shells = list(iter_sequence_manifest_observations(manifest, load_rgb=False))

    assert loaded[0].rgb is not None
    assert shells[0].rgb is None
    assert loaded[0].rgb_path == shells[0].rgb_path
    assert loaded[0].provenance == shells[0].provenance
    assert shells[0].provenance.source_id == DatasetId.ADVIO.value
    assert shells[0].provenance.dataset_id == DatasetId.ADVIO.value
    assert shells[0].provenance.pose_source == AdvioPoseSource.ARCORE.value


def test_sequence_manifest_observation_reader_requires_rgb_dir(tmp_path: Path) -> None:
    timestamps_path = tmp_path / "timestamps.json"
    timestamps_path.write_text(json.dumps({"timestamps_ns": [10]}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="SequenceManifest\\.rgb_dir"):
        list(iter_sequence_manifest_observations(SequenceManifest(sequence_id="seq", timestamps_path=timestamps_path)))


def test_sequence_manifest_observation_reader_requires_timestamps_path(tmp_path: Path) -> None:
    rgb_dir = tmp_path / "frames"
    rgb_dir.mkdir()

    with pytest.raises(RuntimeError, match="SequenceManifest\\.timestamps_path"):
        list(iter_sequence_manifest_observations(SequenceManifest(sequence_id="seq", rgb_dir=rgb_dir)))


def test_sequence_manifest_observation_reader_rejects_malformed_timestamps(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path)
    assert manifest.timestamps_path is not None
    manifest.timestamps_path.write_text(json.dumps({"values": [10]}), encoding="utf-8")

    with pytest.raises(RuntimeError, match="timestamps_ns"):
        list(iter_sequence_manifest_observations(manifest))


def test_sequence_manifest_observation_reader_rejects_count_mismatch(tmp_path: Path) -> None:
    manifest = _write_rgb_manifest(tmp_path, frame_count=2, timestamps_ns=[10])

    with pytest.raises(RuntimeError, match="inconsistent"):
        list(iter_sequence_manifest_observations(manifest))


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
    assert "reference_cloud:tum_rgbd:aligned" in result.outcome.artifacts
    assert "reference_cloud_metadata:tum_rgbd:aligned" in result.outcome.artifacts
    assert result.payload.benchmark_inputs is not None
    assert result.payload.benchmark_inputs.reference_clouds[0].native_frame == "tum_rgbd_mocap_world"
    items = SourceVisualizationAdapter().build_reference_items(
        output=result.payload,
        artifact_refs=result.outcome.artifacts,
    )
    assert [item.role for item in items] == [
        ROLE_SOURCE_REFERENCE_TRAJECTORY,
        ROLE_SOURCE_REFERENCE_POINT_CLOUD,
    ]
    assert items[0].space == "world"
    assert items[1].space == "tum_rgbd_world"
    assert items[1].metadata["native_frame"] == "tum_rgbd_mocap_world"


def test_source_visualization_adapter_emits_native_and_aligned_reference_trajectories(tmp_path: Path) -> None:
    native_path = tmp_path / "arkit.tum"
    aligned_path = tmp_path / "arkit_aligned_to_gt.tum"
    native_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    aligned_path.write_text("0 0 0 0 0 0 0 1\n", encoding="utf-8")
    native_reference = ReferenceTrajectoryRef(
        source=ReferenceSource.ARKIT,
        path=native_path,
        target_frame="advio_arkit_world",
        native_frame="advio_arkit_world",
        coordinate_status=ReferenceCloudCoordinateStatus.SOURCE_NATIVE,
    )
    aligned_reference = ReferenceTrajectoryRef(
        source=ReferenceSource.ARKIT,
        path=aligned_path,
        target_frame="advio_gt_world",
        native_frame="advio_arkit_world",
        coordinate_status=ReferenceCloudCoordinateStatus.ALIGNED,
    )
    output = SourceStageOutput(
        sequence_manifest=SequenceManifest(sequence_id="advio-20", dataset_id="advio"),
        benchmark_inputs=PreparedBenchmarkInputs(reference_trajectories=[native_reference, aligned_reference]),
    )
    artifact_refs = {
        reference_trajectory_artifact_key(native_reference): artifact_ref(native_path, kind="tum"),
        reference_trajectory_artifact_key(aligned_reference): artifact_ref(aligned_path, kind="tum"),
    }

    items = SourceVisualizationAdapter().build_reference_items(output=output, artifact_refs=artifact_refs)

    assert output.benchmark_inputs.trajectory_for_source(ReferenceSource.ARKIT) is native_reference
    assert [(item.role, item.metadata["coordinate_status"], item.metadata["target_frame"]) for item in items] == [
        (ROLE_SOURCE_REFERENCE_TRAJECTORY, "source_native", "advio_arkit_world"),
        (ROLE_SOURCE_REFERENCE_TRAJECTORY, "aligned", "advio_gt_world"),
    ]


def test_source_visualization_adapter_emits_posed_observation_geometry_items() -> None:
    observation = Observation(
        seq=7,
        timestamp_ns=1,
        T_world_camera=FrameTransform(
            target_frame="tum_rgbd_world",
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

    items = SourceVisualizationAdapter().build_observation_items(
        observation=observation,
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
    assert items[1].pose == observation.T_world_camera
    assert items[2].intrinsics == observation.intrinsics
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
        mode=PipelineMode.OFFLINE,
        frame_stride=1,
        streaming_max_frames=None,
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
        mode=PipelineMode.OFFLINE,
        frame_stride=1,
        streaming_max_frames=None,
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
        mode=PipelineMode.OFFLINE,
        frame_stride=1,
        streaming_max_frames=None,
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
        mode=PipelineMode.OFFLINE,
        frame_stride=3,
        streaming_max_frames=None,
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


def test_source_runtime_materialization_preserves_selected_normalized_video(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    video_path = tmp_path / "store" / "observations" / "rgb.mp4"
    video_path.parent.mkdir(parents=True)
    video_path.write_bytes(b"video")
    timestamps_path = run_paths.input_timestamps_path
    timestamps_path.parent.mkdir(parents=True)
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0, 300_000_000], "frame_stride": 3}), encoding="utf-8")
    indices_path = run_paths.artifact_root / "input" / "source_frame_indices.json"
    indices_path.write_text(json.dumps({"source_frame_indices": [0, 3]}), encoding="utf-8")

    def fail_extract_video_frames(**_kwargs):
        raise AssertionError("normalized video-backed manifests must not extract artifact PNG frames")

    monkeypatch.setattr("prml_vslam.sources.materialization.extract_video_frames", fail_extract_video_frames)

    manifest = materialize_manifest(
        mode=PipelineMode.OFFLINE,
        frame_stride=3,
        streaming_max_frames=None,
        prepared_manifest=SequenceManifest(
            sequence_id="advio-15",
            video_path=video_path,
            timestamps_path=timestamps_path,
            source_frame_indices_path=indices_path,
        ),
        run_paths=run_paths,
    )

    assert manifest.video_path == video_path
    assert manifest.rgb_dir is None
    assert manifest.timestamps_path == timestamps_path
    assert not run_paths.input_frames_dir.exists()
    assert json.loads(timestamps_path.read_text(encoding="utf-8")) == {
        "timestamps_ns": [0, 300_000_000],
        "frame_stride": 3,
    }


def test_source_runtime_materialization_does_not_double_sample_dataset_timestamps(tmp_path: Path) -> None:
    run_paths = RunArtifactPaths.build(tmp_path / "artifacts")
    rgb_dir = tmp_path / "rgb"
    rgb_dir.mkdir(parents=True)
    timestamps_path = tmp_path / "sampled-rgb.txt"
    timestamps_path.write_text("0.000000000 rgb/000000.png\n0.200000000 rgb/000001.png\n", encoding="utf-8")
    manifest = materialize_manifest(
        mode=PipelineMode.OFFLINE,
        frame_stride=2,
        streaming_max_frames=None,
        prepared_manifest=SequenceManifest(
            sequence_id="freiburg1_room",
            rgb_dir=rgb_dir,
            timestamps_path=timestamps_path,
        ),
        run_paths=run_paths,
    )

    payload = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    assert payload == {"frame_stride": 1, "timestamps_ns": [0, 200_000_000]}


def test_normalized_store_timestamp_loader_accepts_tum_rgbd_list_rows(tmp_path: Path) -> None:
    timestamps_path = tmp_path / "rgb.txt"
    timestamps_path.write_text(
        "# timestamp rgb\n0.000000000 rgb/000000.png\n0.200000000 rgb/000001.png\n",
        encoding="utf-8",
    )

    assert load_timestamps_ns(timestamps_path) == [0, 200_000_000]


def test_video_source_config_constructs_video_adapter(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path, captures_dir=tmp_path / "captures")
    path_config.captures_dir.mkdir()
    video_path = path_config.captures_dir / "demo.mp4"
    video_path.write_bytes(b"video")

    video_source = VideoSourceConfig(video_path=Path("demo.mp4"), frame_stride=2).setup_target(path_config=path_config)

    assert video_source.label == "Video 'demo.mp4'"


def test_dataset_source_configs_construct_dataset_adapters(tmp_path: Path, monkeypatch) -> None:
    class FakeDatasetService:
        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config
            self.dataset_root = path_config.data_dir / "fake-dataset"

        def resolve_sequence_id(self, sequence_id: str) -> str:
            if sequence_id == "advio-20":
                return 20
            return f"resolved-{sequence_id}"

        def scene(self, sequence_id: object) -> SimpleNamespace:
            return SimpleNamespace(display_name=f"Scene {sequence_id}")

    monkeypatch.setattr("prml_vslam.sources.config.AdvioDatasetService", FakeDatasetService)
    monkeypatch.setattr("prml_vslam.sources.config.TumRgbdDatasetService", FakeDatasetService)

    path_config = PathConfig(root=tmp_path)
    tum_source = TumRgbdSourceConfig(
        sequence_id="freiburg1_room",
        target_fps=15.0,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    ).setup_target(path_config=path_config)
    advio_source = AdvioSourceConfig(
        sequence_id="advio-20",
        frame_stride=3,
        replay_mode=ReplayMode.FAST_AS_POSSIBLE,
    ).setup_target(path_config=path_config)

    assert isinstance(tum_source, NormalizedDatasetRuntimeSource)
    assert isinstance(advio_source, NormalizedDatasetRuntimeSource)
    assert tum_source.label == "resolved-freiburg1_room"
    assert advio_source.label == "advio-20"
    assert tum_source._frame_selection.target_fps == 15.0
    assert tum_source._replay_mode is ReplayMode.FAST_AS_POSSIBLE
    assert tum_source._store.dataset_id is DatasetId.TUM_RGBD
    assert tum_source._store.store_root == (tmp_path / ".data" / "vslam-datastore" / "tum_rgbd").resolve()
    assert tum_source._profile.dataset_id is DatasetId.TUM_RGBD
    assert tum_source._profile.sequence_id == "resolved-freiburg1_room"
    assert advio_source._frame_selection.frame_stride == 3
    assert advio_source._replay_mode is ReplayMode.FAST_AS_POSSIBLE
    assert advio_source._store.dataset_id is DatasetId.ADVIO
    assert advio_source._store.store_root == (tmp_path / ".data" / "vslam-datastore" / "advio").resolve()
    assert advio_source._profile.dataset_id is DatasetId.ADVIO
    assert advio_source._profile.sequence_id == "advio-20"


def test_advio_normalized_profile_ignores_run_local_sampling() -> None:
    source = AdvioSourceConfig(sequence_id="advio-20")
    sampled_source = source.model_copy(update={"frame_stride": 3, "replay_mode": ReplayMode.FAST_AS_POSSIBLE})
    target_fps_source = source.model_copy(update={"target_fps": 15.0})

    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-20",
        source_id=source.source_id,
        payload=source.model_dump(mode="json"),
    )
    sampled_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-20",
        source_id=sampled_source.source_id,
        payload=sampled_source.model_dump(mode="json"),
    )
    target_fps_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.ADVIO,
        sequence_id="advio-20",
        source_id=target_fps_source.source_id,
        payload=target_fps_source.model_dump(mode="json"),
    )

    assert profile.profile_key == sampled_profile.profile_key
    assert profile.profile_key == target_fps_profile.profile_key
    assert profile.source_profile["trajectory_convention"] == "fixedpoint_common_start_local_rdf_v1"
    assert "frame_stride" not in target_fps_profile.source_profile
    assert "target_fps" not in target_fps_profile.source_profile
    assert "sequence_id" not in target_fps_profile.source_profile
    assert "source_id" not in target_fps_profile.source_profile


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
