from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import cv2
import liblzfse
import numpy as np
import pytest
from pydantic import ValidationError

import prml_vslam.sources.datasets.normalization as normalization_module
import prml_vslam.sources.datasets.normalized_store as normalized_store_module
from prml_vslam.interfaces import (
    ObservationIndexEntry,
    ObservationProvenance,
    ObservationSequenceIndex,
    ObservationSequenceRef,
)
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources import FileObservationSequenceLoader
from prml_vslam.sources.config import (
    AdvioSourceConfig,
    Record3DDatasetSourceConfig,
    TumRgbdSourceConfig,
    normalized_profile_for_source_config,
)
from prml_vslam.sources.contracts import (
    PreparedBenchmarkInputs,
    ReferenceCloudSource,
    ReferenceSource,
    SequenceManifest,
)
from prml_vslam.sources.datasets.contracts import DatasetId, FrameSelectionConfig, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalization import (
    normalize_dataset_entries,
    normalize_dataset_entry,
    source_config_for_normalization,
)
from prml_vslam.sources.datasets.normalized_query import query_normalized_dataset
from prml_vslam.sources.datasets.normalized_source import NormalizedDatasetRuntimeSource
from prml_vslam.sources.datasets.normalized_store import (
    NormalizedDatasetEntry,
    NormalizedDatasetProfile,
    NormalizedDatasetStore,
    load_depth_array,
    load_normalized_entry_metadata,
    load_normalized_entry_stats,
    normalized_entry_analysis_summary,
    normalized_store_for_path_config,
)
from prml_vslam.sources.datasets.record3d import (
    Record3DCatalog,
    Record3DDatasetService,
    Record3DDownloadRequest,
    Record3DSceneMetadata,
    Record3DSequence,
    Record3DSequenceConfig,
)
from prml_vslam.sources.datasets.record3d.record3d_download import _redact_url_for_log
from prml_vslam.sources.datasets.record3d.record3d_layout import load_record3d_catalog
from prml_vslam.sources.datasets.registry import list_sequence_slugs, resolve_reference_path
from prml_vslam.sources.replay import ReplayMode
from prml_vslam.sources.stage.config import SourceStageConfig
from prml_vslam.utils import PathConfig
from prml_vslam.utils.geometry import load_point_cloud_ply_with_colors, load_tum_trajectory


@dataclass(frozen=True, slots=True)
class _Record3DNormalizedEntryFixture:
    archive_path: Path
    path_config: PathConfig
    store: NormalizedDatasetStore
    profile: NormalizedDatasetProfile
    entry: NormalizedDatasetEntry


def _write_record3d_archive(
    dataset_root: Path,
    *,
    sequence_id: str = "synthetic",
    frame_indices: tuple[int, ...] = (0, 1, 2),
    zero_origin_depth: bool = True,
) -> Path:
    dataset_root.mkdir(parents=True, exist_ok=True)
    archive_path = dataset_root / f"{sequence_id}.r3d"
    metadata = {
        "K": [100.0, 0.0, 0.0, 0.0, 100.0, 0.0, 4.0, 4.0, 1.0],
        "w": 8,
        "h": 8,
        "dw": 4,
        "dh": 4,
        "fps": 10,
        "frameTimestamps": [0.0, 0.1, 0.2],
        "poses": [
            [0.0, 0.0, 0.0, 1.0, 10.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 11.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 12.0, 0.0, 0.0],
        ],
    }
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("metadata", json.dumps(metadata))
        for seq, index in enumerate(frame_indices):
            rgb = np.full((8, 8, 3), seq * 60, dtype=np.uint8)
            ok, jpg = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
            assert ok
            depth = np.full((4, 4), 1.0 + seq, dtype=np.float32)
            if zero_origin_depth:
                depth[0, 0] = 0.0
            confidence = np.full((4, 4), 2, dtype=np.uint8)
            confidence[0, 1] = 0
            archive.writestr(f"rgbd/{index}.jpg", jpg.tobytes())
            archive.writestr(f"rgbd/{index}.depth", liblzfse.compress(depth.tobytes()))
            archive.writestr(f"rgbd/{index}.conf", liblzfse.compress(confidence.tobytes()))
    return archive_path


def _create_record3d_normalized_entry(tmp_path: Path) -> _Record3DNormalizedEntryFixture:
    archive_path = _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_copy(update={"target_fps": None}).model_dump(mode="json"),
    )
    raw_source = service._build_normalization_materializer(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    entry = store.create_entry_from_source(profile=profile, source=raw_source)
    return _Record3DNormalizedEntryFixture(
        archive_path=archive_path,
        path_config=path_config,
        store=store,
        profile=profile,
        entry=entry,
    )


def test_record3d_catalog_registers_zenodo_scenes_without_preview_token() -> None:
    catalog = load_record3d_catalog()

    assert [scene.sequence_index for scene in catalog.scenes] == list(range(8))
    assert [scene.archive_name for scene in catalog.scenes] == [
        "2026-06-03--18-17-10.r3d",
        "2026-06-03--18-20-22.r3d",
        "2026-06-03--18-24-27.r3d",
        "2026-06-03--18-26-32.r3d",
        "2026-06-03--18-27-25.r3d",
        "2026-06-03--18-29-08.r3d",
        "2026-06-03--18-32-27.r3d",
        "2026-06-03--18-35-44.r3d",
    ]
    assert catalog.scenes[3].archive_sha256 == "d76050f5edac45644dd3aafa20e1b73336959a4282c5494ff30c748c86288fc5"
    assert all("token=" not in (scene.archive_url or "") for scene in catalog.scenes)


def test_record3d_download_request_rejects_out_of_range_sequence_ids() -> None:
    assert Record3DDownloadRequest(sequence_ids=[3, 1, 3]).sequence_ids == [1, 3]
    with pytest.raises(ValidationError, match="non-negative"):
        Record3DDownloadRequest(sequence_ids=[-1])


def test_record3d_dataset_service_downloads_selected_archives_from_file_urls(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="downloadable")
    source_hash = sha256(remote_archive.read_bytes()).hexdigest()
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=3,
                sequence_id="downloadable",
                archive_name="downloadable.r3d",
                display_name="Downloadable",
                archive_url=remote_archive.as_uri(),
                archive_sha256=source_hash,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    first_result = service.download(Record3DDownloadRequest(sequence_ids=[3]))
    second_result = service.download(Record3DDownloadRequest(sequence_ids=[3]))

    local_archive = tmp_path / ".data" / "record3d" / "downloadable.r3d"
    assert local_archive.exists()
    assert sha256(local_archive.read_bytes()).hexdigest() == source_hash
    assert first_result.sequence_ids == [3]
    assert first_result.downloaded_archive_count == 1
    assert first_result.reused_archive_count == 0
    assert first_result.written_path_count == 1
    assert second_result.downloaded_archive_count == 0
    assert second_result.reused_archive_count == 1


def test_record3d_dataset_service_summarizes_catalog_scenes_even_when_missing(tmp_path: Path) -> None:
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="missing",
                archive_name="missing.r3d",
                display_name="Missing",
                archive_url="file:///tmp/missing.r3d",
                archive_sha256="0" * 64,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    statuses = service.local_scene_statuses()
    summary = service.summarize(statuses)

    assert len(statuses) == 1
    assert statuses[0].scene.sequence_id == "missing"
    assert statuses[0].sequence_dir is None
    assert statuses[0].archive_path is None
    assert summary.total_scene_count == 1
    assert summary.local_scene_count == 0
    assert summary.offline_ready_scene_count == 0


def test_record3d_dataset_service_appends_local_ad_hoc_archives_to_catalog_statuses(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d", sequence_id="synthetic")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="catalog-missing",
                archive_name="catalog-missing.r3d",
                display_name="Catalog Missing",
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    statuses = service.local_scene_statuses()

    assert [status.scene.sequence_id for status in statuses] == ["catalog-missing", "synthetic"]
    assert statuses[0].offline_ready is False
    assert statuses[1].offline_ready is True


def test_record3d_dataset_service_rejects_sequence_indices_outside_catalog(tmp_path: Path) -> None:
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="downloadable",
                archive_name="downloadable.r3d",
                display_name="Downloadable",
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match=r"\[0, 0\]"):
        service.download(Record3DDownloadRequest(sequence_ids=[8]))


def test_record3d_download_redacts_sensitive_url_query_values() -> None:
    url = "https://zenodo.org/records/20591352/files/scene.r3d?preview=1&token=secret&access_token=also-secret"

    redacted = _redact_url_for_log(url)

    assert "preview=1" in redacted
    assert "token=%3Credacted%3E" in redacted
    assert "access_token=%3Credacted%3E" in redacted
    assert "secret" not in redacted


def test_record3d_dataset_service_rejects_unsafe_archive_names(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="unsafe")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="unsafe",
                archive_name="../unsafe.r3d",
                display_name="Unsafe",
                archive_url=remote_archive.as_uri(),
                archive_sha256=sha256(remote_archive.read_bytes()).hexdigest(),
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match="simple `.r3d` filename"):
        service.download(Record3DDownloadRequest(sequence_ids=[0]))


def test_record3d_dataset_service_rejects_download_checksum_mismatch(tmp_path: Path) -> None:
    remote_archive = _write_record3d_archive(tmp_path / "remote", sequence_id="bad-hash")
    catalog = Record3DCatalog(
        scenes=[
            Record3DSceneMetadata(
                sequence_index=0,
                sequence_id="bad-hash",
                archive_name="bad-hash.r3d",
                display_name="Bad Hash",
                archive_url=remote_archive.as_uri(),
                archive_sha256="0" * 64,
            )
        ]
    )
    service = Record3DDatasetService(PathConfig(root=tmp_path, data_dir=tmp_path / ".data"), catalog=catalog)

    with pytest.raises(ValueError, match="Checksum mismatch"):
        service.download(Record3DDownloadRequest(sequence_ids=[0]))
    assert not (tmp_path / ".data" / "record3d" / "bad-hash.r3d").exists()


def test_record3d_sequence_loads_rgbd_observations_and_reference_cloud(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, random_seed=17, min_confidence=1),
        )
    )

    sample = sequence.load_offline_sample()
    manifest = sequence.to_sequence_manifest(output_dir=tmp_path / "manifest")
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    observations = list(FileObservationSequenceLoader(benchmark_inputs.observation_sequences[0]).iter_observations())
    points_xyz, colors_rgb = load_point_cloud_ply_with_colors(benchmark_inputs.reference_clouds[0].path)
    metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert sample.sequence_id == "synthetic"
    assert len(sample.frames) == 3
    assert sample.rgb_intrinsics.width_px == 8
    assert sample.depth_intrinsics.width_px == 4
    assert sample.timestamps_ns == [0, 100_000_000, 200_000_000]
    assert manifest.dataset_id is DatasetId.RECORD3D
    assert manifest.rgb_dir is None
    assert json.loads(manifest.timestamps_path.read_text(encoding="utf-8")) == {
        "timestamps_ns": [0, 100_000_000, 200_000_000]
    }
    assert benchmark_inputs.reference_trajectories[0].source is ReferenceSource.ARKIT
    assert benchmark_inputs.reference_trajectories[0].target_frame == "record3d_world"
    assert benchmark_inputs.reference_clouds[0].source is ReferenceCloudSource.RECORD3D_LIDAR
    assert benchmark_inputs.reference_clouds[0].coordinate_status.value == "aligned"
    assert len(observations) == 3
    assert observations[0].rgb is not None
    assert observations[0].rgb.shape == (4, 4, 3)
    assert observations[0].depth_m is not None
    assert observations[0].depth_m.shape == (4, 4)
    assert observations[0].intrinsics.width_px == 4
    np.testing.assert_allclose(observations[0].T_world_camera.as_matrix(), np.eye(4), atol=1e-9)
    assert observations[1].T_world_camera.tx == pytest.approx(1.0)
    trajectory = load_tum_trajectory(benchmark_inputs.reference_trajectories[0].path)
    trajectory_metadata = json.loads(
        benchmark_inputs.reference_trajectories[0].metadata_path.read_text(encoding="utf-8")
    )
    np.testing.assert_allclose(trajectory.poses_se3[0], np.eye(4), atol=1e-9)
    assert trajectory.positions_xyz[:, 0].tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert trajectory_metadata["trajectory_origin"] == "first_pose"
    assert trajectory_metadata["pose_normalization"] == "relative_to_first_pose"
    assert points_xyz.shape[0] == 20
    assert points_xyz[:, 0].min() > -1.0
    assert points_xyz[:, 0].max() < 4.0
    assert colors_rgb is not None
    assert metadata["coordinate_origin"] == "first_pose"
    assert metadata["coordinate_normalization"] == "relative_to_first_pose"
    assert metadata["max_points"] == 20
    assert metadata["depth_stride_px"] == 1
    assert metadata["min_confidence"] == 1
    assert metadata["random_seed"] == 17
    assert metadata["point_count_after_sampling"] == 20
    assert metadata["rejected_count"] >= 2


def test_record3d_dataset_service_and_registry_discover_local_archives(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)

    source = service._build_normalization_materializer(
        sequence_id="synthetic",
        frame_selection=None,
    )
    manifest = source.prepare_sequence_manifest(tmp_path / "source")

    assert service.resolve_sequence_id("synthetic.r3d") == "synthetic"
    synthetic_status = next(
        status for status in service.local_scene_statuses() if status.scene.sequence_id == "synthetic"
    )
    assert synthetic_status.offline_ready is True
    assert source.label == "synthetic"
    assert manifest.dataset_id is DatasetId.RECORD3D
    assert list_sequence_slugs(DatasetId.RECORD3D, tmp_path / ".data" / "record3d") == ["synthetic"]
    assert resolve_reference_path(DatasetId.RECORD3D, tmp_path / ".data" / "record3d", "synthetic") is None


def test_record3d_normalized_store_persists_replayable_entry(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    entry = fixture.entry
    records = [record.model_dump(mode="json") for record in fixture.store.summary(strict=False)]

    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    observation_ref = benchmark_inputs["observation_sequences"][0]
    stored_inputs = PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    observations = list(FileObservationSequenceLoader(stored_inputs.observation_sequences[0]).iter_observations())
    observation_index = json.loads(stored_inputs.observation_sequences[0].index_path.read_text(encoding="utf-8"))
    first_depth_path = stored_inputs.observation_sequences[0].payload_root / observation_index["rows"][0]["depth_path"]
    stats = {(row["scope"], row["subject"], row["stat"]): row["value"] for row in load_normalized_entry_stats(entry)}

    assert fixture.store.store_root == (tmp_path / ".data" / "vslam-datastore" / "record3d").resolve()
    assert entry.root.parent == fixture.store.store_root / "synthetic"
    assert entry.stats_long_path == entry.root / "stats_long.csv"
    assert entry.metadata_long_path == entry.root / "metadata_long.csv"
    assert not (tmp_path / ".data" / "record3d" / ".normalized").exists()
    assert observation_ref["payload_root"] == (entry.root / "observations").as_posix()
    assert observation_ref["index_path"] == (entry.root / "observations" / "observations.json").as_posix()
    assert not (entry.root / "observations" / "rgb.mp4").exists()
    assert (entry.root / "observations" / "rgb").is_dir()
    assert (entry.root / "observations" / "depth").is_dir()
    assert json.loads((entry.root / "observations" / "rgb.metadata.json").read_text(encoding="utf-8")) == {
        "dimension_multiple": 14,
        "raster_space": "display_downscaled",
        "rgb_max_width_px": 392,
        "source_raster_space": "depth",
    }
    assert not (entry.root / "observations" / "0").exists()
    assert not (entry.root / "benchmark" / "reference").exists()
    assert not (entry.root / "benchmark" / "observations").exists()
    assert (
        benchmark_inputs["reference_trajectories"][0]["path"]
        == (entry.root / "benchmark" / "trajectories" / "arkit.tum").as_posix()
    )
    assert (
        benchmark_inputs["reference_trajectories"][0]["metadata_path"]
        == (entry.root / "benchmark" / "trajectories" / "arkit.metadata.json").as_posix()
    )
    trajectory = load_tum_trajectory(Path(benchmark_inputs["reference_trajectories"][0]["path"]))
    trajectory_metadata = json.loads(Path(benchmark_inputs["reference_trajectories"][0]["metadata_path"]).read_text())
    np.testing.assert_allclose(trajectory.poses_se3[0], np.eye(4), atol=1e-9)
    assert trajectory_metadata["trajectory_origin"] == "first_pose"
    assert trajectory_metadata["pose_normalization"] == "relative_to_first_pose"
    assert (
        benchmark_inputs["reference_clouds"][0]["path"]
        == (entry.root / "benchmark" / "reference_clouds" / "record3d_lidar.ply").as_posix()
    )
    assert (
        benchmark_inputs["reference_clouds"][0]["metadata_path"]
        == (entry.root / "benchmark" / "reference_clouds" / "record3d_lidar.metadata.json").as_posix()
    )
    assert len(observations) == 3
    assert observations[0].rgb is not None
    assert observations[0].depth_m is not None
    np.testing.assert_allclose(observations[0].T_world_camera.as_matrix(), np.eye(4), atol=1e-9)
    assert observations[1].T_world_camera.tx == pytest.approx(1.0)
    assert stored_inputs.observation_sequences[0].raster_space == "display_downscaled"
    assert observations[0].rgb.shape[:2] == observations[0].depth_m.shape
    assert observations[0].intrinsics is not None
    assert observations[0].intrinsics.width_px == observations[0].rgb.shape[1]
    assert observations[0].intrinsics.height_px == observations[0].rgb.shape[0]
    assert observation_index["rows"][0]["rgb_path"] == "rgb/000000.png"
    assert observation_index["rows"][0]["provenance"]["raster_space"] == "display_downscaled"
    assert observation_index["rows"][0]["provenance"]["original_width"] == 4
    assert observation_index["rows"][0]["provenance"]["original_height"] == 4
    assert (stored_inputs.observation_sequences[0].payload_root / observation_index["rows"][0]["rgb_path"]).is_file()
    assert first_depth_path.suffix == ".png"
    assert observation_index["rows"][0]["depth_scale_to_m"] == pytest.approx(0.001)
    assert (load_depth_array(first_depth_path) * observation_index["rows"][0]["depth_scale_to_m"])[
        1, 1
    ] == pytest.approx(
        1.0,
        abs=0.0005,
    )
    assert observations[0].depth_m[1, 1] == pytest.approx(1.0, abs=0.0005)
    assert stats[("observation_sequence", "record3d_dataset", "depth_coverage_ratio")] == "1"
    assert stats[("reference_trajectory", "arkit/aligned", "trajectory_path_length_m")] == "2"
    assert ("reference_trajectory", "arkit/aligned", "ego_motion_class") not in stats
    cloud_metadata = json.loads(Path(benchmark_inputs["reference_clouds"][0]["metadata_path"]).read_text())
    points_xyz, _ = load_point_cloud_ply_with_colors(Path(benchmark_inputs["reference_clouds"][0]["path"]))
    assert cloud_metadata["coordinate_origin"] == "first_pose"
    assert cloud_metadata["coordinate_normalization"] == "relative_to_first_pose"
    assert points_xyz[:, 0].min() > -1.0
    assert points_xyz[:, 0].max() < 4.0
    assert records[0]["schema_version"] == 10
    assert "sequence_id" not in records[0]["profile"]["source_profile"]
    assert "source_id" not in records[0]["profile"]["source_profile"]


def test_normalized_entry_accepts_legacy_analysis_csv_path_fields(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    entry_path = fixture.entry.root / "entry.json"
    payload = json.loads(entry_path.read_text(encoding="utf-8"))
    payload["stats_long_csv_path"] = payload.pop("stats_long_path")
    payload["metadata_long_csv_path"] = payload.pop("metadata_long_path")
    entry_path.write_text(json.dumps(payload), encoding="utf-8")

    entry = fixture.store.load_entry(fixture.profile)
    summary = normalized_entry_analysis_summary(entry)

    assert entry.stats_long_path == fixture.entry.root / "stats_long.csv"
    assert entry.metadata_long_path == fixture.entry.root / "metadata_long.csv"
    assert summary["stats_long_row_count"] > 0
    assert summary["metadata_long_row_count"] > 0
    assert load_normalized_entry_stats(entry)
    assert load_normalized_entry_metadata(entry)
    assert "stats_long_csv_path" not in entry.model_dump(mode="json")
    assert "metadata_long_csv_path" not in entry.model_dump(mode="json")
    assert fixture.store.summary(strict=False) == [entry]
    assert fixture.store.issues() == []


def test_record3d_normalized_store_rejects_stale_schema_entries(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    store = fixture.store
    profile = fixture.profile
    entry = fixture.entry
    entry_path = entry.root / "entry.json"
    stale_payload = json.loads(entry_path.read_text(encoding="utf-8"))
    stale_payload["schema_version"] = 9
    stale_payload["profile"]["schema_version"] = 9
    entry_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="schema_version"):
        store.load_entry(profile)
    assert store.summary() == []
    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].status == "stale_schema"
    assert issues[0].sequence_id == "synthetic"


def test_normalized_store_ignores_superseded_stale_schema_entries(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    stale_root = fixture.entry.root.parent / "legacy-profile"
    shutil.copytree(fixture.entry.root, stale_root)
    entry_path = stale_root / "entry.json"
    stale_payload = json.loads(entry_path.read_text(encoding="utf-8"))
    stale_payload["schema_version"] = 9
    stale_payload["profile_key"] = stale_root.name
    stale_payload["root"] = stale_root.as_posix()
    stale_payload["profile"]["schema_version"] = 9
    entry_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    assert fixture.store.summary(strict=False) == [fixture.entry]
    issues = fixture.store.issues()
    assert len(issues) == 1
    assert issues[0].status == "stale_schema"
    assert issues[0].profile_key == "legacy-profile"


def test_normalized_store_rejects_stored_sampling_profile_mismatch(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        target_fps=5.0,
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    stored_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    raw_source = service._build_normalization_materializer(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(target_fps=5.0),
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    stored_entry = store.create_entry_from_source(profile=stored_profile, source=raw_source)
    requested_profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id=stored_profile.sequence_id,
        source_id=stored_profile.source_id,
        source_profile={
            key: value
            for key, value in stored_profile.source_profile.items()
            if key not in {"frame_stride", "target_fps"}
        },
    )

    with pytest.raises(FileNotFoundError):
        store.load_entry(requested_profile)
    with pytest.raises(FileNotFoundError):
        store.load_entry_for_runtime(requested_profile, frame_selection=FrameSelectionConfig(target_fps=5.0))
    assert (
        store.load_entry_by_key_for_runtime(
            sequence_id="synthetic",
            profile_key=stored_entry.profile_key,
            frame_selection=FrameSelectionConfig(target_fps=5.0),
        ).root
        == stored_entry.root
    )


def test_normalized_store_rejects_requested_sampling_profile_mismatch(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    source_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        target_fps=5.0,
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    requested_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=source_config.source_id,
        payload=source_config.model_dump(mode="json"),
    )
    stored_profile = NormalizedDatasetProfile(
        dataset_id=requested_profile.dataset_id,
        sequence_id=requested_profile.sequence_id,
        source_id=requested_profile.source_id,
        source_profile={
            key: value
            for key, value in requested_profile.source_profile.items()
            if key not in {"frame_stride", "target_fps"}
        },
    )
    raw_source = service._build_normalization_materializer(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(),
        materialization=source_config.materialization,
        reference_cloud=source_config.reference_cloud,
    )
    stored_entry = store.create_entry_from_source(profile=stored_profile, source=raw_source)

    with pytest.raises(FileNotFoundError):
        store.load_entry(requested_profile)
    with pytest.raises(FileNotFoundError):
        store.load_entry_for_runtime(requested_profile, frame_selection=FrameSelectionConfig())
    assert (
        store.load_entry_by_key_for_runtime(
            sequence_id="synthetic",
            profile_key=stored_entry.profile_key,
            frame_selection=FrameSelectionConfig(),
        ).root
        == stored_entry.root
    )


def test_normalized_store_rejects_byte_affecting_profile_mismatch(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    requested_profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id=fixture.profile.sequence_id,
        source_id=fixture.profile.source_id,
        source_profile={"reference_cloud": {"max_points": 999}},
    )

    with pytest.raises(FileNotFoundError):
        fixture.store.load_entry_for_runtime(requested_profile)


def test_normalized_store_target_fps_requires_exact_normalized_profile(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    first_config = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        target_fps=5.0,
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    second_config = first_config.model_copy(update={"target_fps": 2.5})
    stored_entries = {}
    for source_config in (first_config, second_config):
        profile = normalized_profile_for_source_config(
            dataset_id=DatasetId.RECORD3D,
            sequence_id="synthetic",
            source_id=source_config.source_id,
            payload=source_config.model_dump(mode="json"),
        )
        source = service._build_normalization_materializer(
            sequence_id="synthetic",
            frame_selection=FrameSelectionConfig(target_fps=source_config.target_fps),
            materialization=source_config.materialization,
            reference_cloud=source_config.reference_cloud,
        )
        stored_entries[source_config.target_fps] = store.create_entry_from_source(
            profile=profile,
            source=source,
        )
    requested_profile = normalized_profile_for_source_config(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id=first_config.source_id,
        payload=first_config.model_copy(update={"target_fps": None}).model_dump(mode="json"),
    )

    with pytest.raises(FileNotFoundError):
        store.load_entry_for_runtime(requested_profile)
    assert (
        store.load_entry_by_key_for_runtime(
            sequence_id="synthetic",
            profile_key=stored_entries[5.0].profile_key,
        ).profile_key
        == stored_entries[5.0].profile_key
    )


def test_record3d_normalized_store_reports_invalid_entries_without_aborting_summary(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    store = fixture.store
    profile = fixture.profile
    entry = fixture.entry
    entry.benchmark_inputs_path.unlink()

    with pytest.raises(FileNotFoundError):
        store.load_entry(profile)
    assert store.summary(strict=False) == []
    issues = store.issues()
    assert len(issues) == 1
    assert issues[0].status == "invalid"
    assert issues[0].sequence_id == "synthetic"
    assert "FileNotFoundError" in issues[0].message


def test_normalized_store_preserves_manifest_timestamps_for_video_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class VideoSource:
        @property
        def label(self) -> str:
            return "video"

        def prepare_sequence_manifest(self, output_dir: Path) -> SequenceManifest:
            output_dir.mkdir(parents=True)
            video_path = output_dir / "frames.mov"
            video_path.write_bytes(b"placeholder")
            timestamps_path = output_dir / "frames.csv"
            timestamps_path.write_text("0.000000000,1\n0.123456789,2\n", encoding="utf-8")
            return SequenceManifest(
                sequence_id="video-seq",
                dataset_id=DatasetId.ADVIO,
                video_path=video_path,
                timestamps_path=timestamps_path,
            )

        def prepare_benchmark_inputs(self, output_dir: Path) -> PreparedBenchmarkInputs:
            output_dir.mkdir(parents=True)
            return PreparedBenchmarkInputs()

    def fake_extract_video_frames(*, video_path: Path, output_dir: Path) -> SimpleNamespace:
        del video_path
        output_dir.mkdir(parents=True)
        return SimpleNamespace(rgb_dir=output_dir, timestamps_ns=[0, 100_000_000])

    monkeypatch.setattr(
        normalized_store_module,
        "extract_video_frames",
        fake_extract_video_frames,
    )
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    store = normalized_store_for_path_config(DatasetId.ADVIO, path_config)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.ADVIO,
        sequence_id="video-seq",
        source_id="video-seq",
        source_profile={},
    )

    entry = store.create_entry_from_source(profile=profile, source=VideoSource())
    manifest = SequenceManifest.model_validate_json(entry.sequence_manifest_path.read_text(encoding="utf-8"))
    timestamps = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))

    assert timestamps == {
        "timestamps_ns": [0, 123_456_789],
        "requested_frame_stride": 1,
        "requested_target_fps": None,
        "resolved_frame_stride": 1,
        "resolved_target_fps": pytest.approx(8.10000007371),
        "frame_stride": 1,
        "target_fps": pytest.approx(8.10000007371),
    }


def test_source_config_for_normalization_preserves_dataset_reference_cloud_defaults() -> None:
    advio_config = source_config_for_normalization(dataset_id=DatasetId.ADVIO, sequence_id="advio-21")
    tum_config = source_config_for_normalization(dataset_id=DatasetId.TUM_RGBD, sequence_id="freiburg1_desk")
    record3d_config = source_config_for_normalization(dataset_id=DatasetId.RECORD3D, sequence_id="synthetic")

    assert isinstance(advio_config, AdvioSourceConfig)
    assert advio_config.target_fps == 15.0
    assert advio_config.rgb_max_width_px == 392
    assert advio_config.rgb_dimension_multiple == 14
    assert isinstance(tum_config, TumRgbdSourceConfig)
    assert tum_config.target_fps == 30.0
    assert tum_config.reference_cloud == ReferenceCloudConfig()
    assert tum_config.rgb_max_width_px == 392
    assert tum_config.rgb_dimension_multiple == 14
    assert isinstance(record3d_config, Record3DDatasetSourceConfig)
    assert record3d_config.target_fps == 30.0
    assert record3d_config.reference_cloud == ReferenceCloudConfig(min_confidence=1)
    assert record3d_config.rgb_max_width_px == 392
    assert record3d_config.rgb_dimension_multiple == 14


def test_fresh_normalized_entries_are_current_query_records(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d", zero_origin_depth=False)
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source_config = source_config_for_normalization(dataset_id=DatasetId.RECORD3D, sequence_id="synthetic")

    entry = normalize_dataset_entry(
        dataset_id=DatasetId.RECORD3D,
        path_config=path_config,
        service=service,
        source_config=source_config,
    )
    query = query_normalized_dataset(DatasetId.RECORD3D, path_config)

    assert [(record.sequence_id, record.profile_key) for record in query.records] == [
        (entry.sequence_id, entry.profile_key)
    ]


def test_normalize_dataset_entries_parallelizes_multi_sequence_builds(monkeypatch, tmp_path: Path) -> None:
    seen_workers: list[int] = []

    class FakeExecutor:
        def __init__(self, *, max_workers: int) -> None:
            seen_workers.append(max_workers)

        def __enter__(self) -> FakeExecutor:
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def map(self, func, tasks):
            return [func(task) for task in tasks]

    monkeypatch.setattr(normalization_module, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(
        normalization_module,
        "_normalize_dataset_entry_worker",
        lambda task: SimpleNamespace(sequence_id=task[2]),
    )

    entries = normalize_dataset_entries(
        dataset_id=DatasetId.RECORD3D,
        path_config=PathConfig(root=tmp_path),
        sequence_ids=["a", "b", "c"],
        workers=99,
    )

    assert seen_workers == [3]
    assert [entry.sequence_id for entry in entries] == ["a", "b", "c"]


def test_normalized_store_preserves_external_benchmark_observation_sources(tmp_path: Path) -> None:
    payload_root = tmp_path / "external" / "benchmark" / "observations"
    rgb_dir = payload_root / "rgb"
    rgb_dir.mkdir(parents=True)
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cv2.imwrite(str(rgb_dir / "000000.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    sequence_index = ObservationSequenceIndex(
        source_id="external",
        sequence_id="synthetic",
        observation_count=1,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb/000000.png"),
                provenance=ObservationProvenance(source_id="external", sequence_id="synthetic"),
            )
        ],
    )
    index_path = payload_root / "observations.json"
    index_path.write_text(json.dumps(sequence_index.model_dump(mode="json")), encoding="utf-8")
    timestamps_path = tmp_path / "source" / "timestamps.json"
    timestamps_path.parent.mkdir(parents=True)
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0]}), encoding="utf-8")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="synthetic",
        source_profile={},
    )

    entry = store.create_entry(
        profile=profile,
        sequence_manifest=SequenceManifest(
            sequence_id="synthetic", dataset_id=DatasetId.RECORD3D, timestamps_path=timestamps_path
        ),
        benchmark_inputs=PreparedBenchmarkInputs(
            observation_sequences=[
                ObservationSequenceRef(
                    source_id="external",
                    sequence_id="synthetic",
                    index_path=index_path,
                    payload_root=payload_root,
                    observation_count=1,
                )
            ]
        ),
    )

    assert payload_root.exists()
    assert (entry.root / "observations" / "observations.json").exists()


def test_normalized_store_does_not_rewrite_opaque_json_strings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="synthetic",
        source_profile={},
    )
    temp_root = (store.store_root / ".tmp-normalized-test" / profile.sequence_id / profile.profile_key).resolve()
    opaque_value = (temp_root / "literal-not-a-path-contract").as_posix()
    monkeypatch.setattr(normalized_store_module, "_temporary_entry_root", lambda _final_root: temp_root)
    payload_root = tmp_path / "external" / "observations"
    rgb_dir = payload_root / "rgb"
    rgb_dir.mkdir(parents=True)
    rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    assert cv2.imwrite(str(rgb_dir / "000000.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    sequence_index = ObservationSequenceIndex(
        source_id="external",
        sequence_id="synthetic",
        observation_count=1,
        rows=[
            ObservationIndexEntry(
                seq=0,
                timestamp_ns=0,
                rgb_path=Path("rgb/000000.png"),
                provenance=ObservationProvenance(source_id=opaque_value, sequence_id="synthetic"),
            )
        ],
    )
    index_path = payload_root / "observations.json"
    index_path.write_text(json.dumps(sequence_index.model_dump(mode="json")), encoding="utf-8")

    entry = store.create_entry(
        profile=profile,
        sequence_manifest=SequenceManifest(sequence_id="synthetic", dataset_id=DatasetId.RECORD3D),
        benchmark_inputs=PreparedBenchmarkInputs(
            observation_sequences=[
                ObservationSequenceRef(
                    source_id="external",
                    sequence_id="synthetic",
                    index_path=index_path,
                    payload_root=payload_root,
                    observation_count=1,
                )
            ]
        ),
    )
    stored_inputs = PreparedBenchmarkInputs.model_validate_json(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    stored_index = json.loads(stored_inputs.observation_sequences[0].index_path.read_text(encoding="utf-8"))

    assert stored_inputs.observation_sequences[0].index_path.is_relative_to(entry.root)
    assert stored_index["rows"][0]["provenance"]["source_id"] == opaque_value
    assert not stored_index["rows"][0]["provenance"]["source_id"].startswith(entry.root.as_posix())


def test_normalized_store_failed_rebuild_preserves_existing_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    timestamps_path = tmp_path / "replacement" / "timestamps.json"
    timestamps_path.parent.mkdir()
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0]}), encoding="utf-8")
    intrinsics_path = tmp_path / "replacement" / "intrinsics.yaml"
    intrinsics_path.write_text("camera:\n  model: pinhole\n", encoding="utf-8")

    def fail_copy_path(source: Path, target: Path) -> Path:
        raise RuntimeError(f"boom while copying {source} to {target}")

    monkeypatch.setattr(normalized_store_module, "_copy_path", fail_copy_path)

    with pytest.raises(RuntimeError, match="boom while copying"):
        fixture.store.create_entry(
            profile=fixture.profile,
            sequence_manifest=SequenceManifest(
                sequence_id="synthetic",
                dataset_id=DatasetId.RECORD3D,
                timestamps_path=timestamps_path,
                intrinsics_path=intrinsics_path,
            ),
            benchmark_inputs=PreparedBenchmarkInputs(),
        )

    assert fixture.store.load_entry(fixture.profile).root == fixture.entry.root
    assert not list(fixture.entry.root.parent.glob(f".{fixture.entry.root.name}.tmp-*"))


def test_normalized_store_rejects_multiple_observation_sequences(tmp_path: Path) -> None:
    source_roots: list[Path] = []
    refs: list[ObservationSequenceRef] = []
    for index in range(2):
        payload_root = tmp_path / "source" / f"sequence-{index}"
        rgb_dir = payload_root / "rgb"
        rgb_dir.mkdir(parents=True)
        rgb = np.full((2, 2, 3), index, dtype=np.uint8)
        assert cv2.imwrite(str(rgb_dir / "000000.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        sequence_index = ObservationSequenceIndex(
            source_id=f"source-{index}",
            sequence_id="synthetic",
            observation_count=1,
            rows=[
                ObservationIndexEntry(
                    seq=0,
                    timestamp_ns=index,
                    rgb_path=Path("rgb/000000.png"),
                    provenance=ObservationProvenance(source_id=f"source-{index}", sequence_id="synthetic"),
                )
            ],
        )
        index_path = payload_root / "observations.json"
        index_path.write_text(json.dumps(sequence_index.model_dump(mode="json")), encoding="utf-8")
        source_roots.append(payload_root)
        refs.append(
            ObservationSequenceRef(
                source_id=f"source-{index}",
                sequence_id="synthetic",
                index_path=index_path,
                payload_root=payload_root,
                observation_count=1,
            )
        )
    timestamps_path = tmp_path / "source" / "timestamps.json"
    timestamps_path.write_text(json.dumps({"timestamps_ns": [0]}), encoding="utf-8")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    store = normalized_store_for_path_config(DatasetId.RECORD3D, path_config)
    profile = NormalizedDatasetProfile(
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="synthetic",
        source_profile={},
    )

    with pytest.raises(RuntimeError, match="exactly one observation sequence"):
        store.create_entry(
            profile=profile,
            sequence_manifest=SequenceManifest(
                sequence_id="synthetic", dataset_id=DatasetId.RECORD3D, timestamps_path=timestamps_path
            ),
            benchmark_inputs=PreparedBenchmarkInputs(observation_sequences=refs),
        )


def test_record3d_normalized_store_reuses_full_frame_payload_for_sampled_runs(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    fixture.archive_path.rename(fixture.archive_path.with_suffix(".r3d.bak"))
    normalized_source = NormalizedDatasetRuntimeSource(
        label="record3d_dataset:synthetic",
        store=fixture.store,
        profile=fixture.profile,
        frame_selection=FrameSelectionConfig(frame_stride=2),
        replay_mode=ReplayMode.REALTIME,
    )

    manifest = normalized_source.prepare_sequence_manifest(tmp_path / "run" / "input")
    benchmark_inputs = normalized_source.prepare_benchmark_inputs(tmp_path / "run" / "benchmark")
    frame_indices = json.loads(manifest.source_frame_indices_path.read_text(encoding="utf-8"))
    timestamps = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    observation_ref = benchmark_inputs.observation_sequences[0]
    observation_index = json.loads(observation_ref.index_path.read_text(encoding="utf-8"))

    assert fixture.entry.root.joinpath("input", "rgb").exists() is False
    assert manifest.video_path is None
    assert manifest.rgb_dir == observation_ref.payload_root / "rgb"
    assert manifest.rgb_dir.is_relative_to(fixture.entry.root)
    assert not (tmp_path / "run" / "input" / "rgb").exists()
    assert frame_indices == {"source_frame_indices": [0, 2]}
    assert timestamps["timestamps_ns"] == [0, 200_000_000]
    assert timestamps["requested_frame_stride"] == 2
    assert timestamps["requested_target_fps"] is None
    assert timestamps["resolved_frame_stride"] == 2
    assert timestamps["resolved_target_fps"] == pytest.approx(5.0)
    assert timestamps["target_fps"] == pytest.approx(5.0)
    assert observation_ref.payload_root.is_relative_to(fixture.entry.root)
    assert [row["provenance"]["source_frame_index"] for row in observation_index["rows"]] == [0, 2]


def test_record3d_normalized_store_applies_runtime_target_fps_without_copying_payloads(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    normalized_source = NormalizedDatasetRuntimeSource(
        label="record3d_dataset:synthetic",
        store=fixture.store,
        profile=fixture.profile,
        frame_selection=FrameSelectionConfig(target_fps=5.0),
        replay_mode=ReplayMode.REALTIME,
    )
    fixture.archive_path.rename(fixture.archive_path.with_suffix(".r3d.bak"))

    manifest = normalized_source.prepare_sequence_manifest(tmp_path / "run" / "input")
    timestamps = json.loads(manifest.timestamps_path.read_text(encoding="utf-8"))
    frame_indices = json.loads(manifest.source_frame_indices_path.read_text(encoding="utf-8"))

    assert manifest.rgb_dir.is_relative_to(fixture.entry.root)
    assert not (tmp_path / "run" / "input" / "rgb").exists()
    assert frame_indices == {"source_frame_indices": [0, 2]}
    assert timestamps["timestamps_ns"] == [0, 200_000_000]
    assert timestamps["requested_frame_stride"] == 1
    assert timestamps["requested_target_fps"] == pytest.approx(5.0)
    assert timestamps["resolved_frame_stride"] == 2
    assert timestamps["resolved_target_fps"] == pytest.approx(5.0)


def test_record3d_normalized_store_warns_and_uses_stored_frames_for_runtime_upsampling(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    normalized_source = NormalizedDatasetRuntimeSource(
        label="record3d_dataset:synthetic",
        store=fixture.store,
        profile=fixture.profile,
        frame_selection=FrameSelectionConfig(target_fps=30.0),
        replay_mode=ReplayMode.REALTIME,
    )

    with pytest.warns(RuntimeWarning, match="would require upsampling"):
        manifest = normalized_source.prepare_sequence_manifest(tmp_path / "run" / "input")

    timestamps = json.loads(Path(manifest.timestamps_path).read_text(encoding="utf-8"))
    assert timestamps["resolved_frame_stride"] == 1
    assert timestamps["resolved_target_fps"] < 30.0


def test_record3d_normalized_store_rejects_tampered_entry_metadata(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    store = fixture.store
    profile = fixture.profile
    entry = fixture.entry
    payload = entry.model_dump(mode="json")
    payload["sequence_id"] = "other"
    (entry.root / "entry.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="metadata does not match requested profile"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="metadata does not match requested profile"):
        store.summary()


def test_normalized_store_rejects_unsafe_entry_identity_paths(tmp_path: Path) -> None:
    store = normalized_store_for_path_config(
        DatasetId.RECORD3D,
        PathConfig(root=tmp_path, data_dir=tmp_path / ".data"),
    )
    valid_key = "0123456789abcdef01234567"

    for sequence_id in ("", ".", "..", "../escape", "nested/sequence", "nested\\sequence"):
        with pytest.raises(ValueError, match="sequence_id"):
            store.load_entry_by_key_for_runtime(sequence_id=sequence_id, profile_key=valid_key)

    for profile_key in ("", "not-a-profile-key", "../0123456789abcdef0123", "0123456789abcdef0123456g"):
        with pytest.raises(ValueError, match="profile_key"):
            store.load_entry_by_key_for_runtime(sequence_id="synthetic", profile_key=profile_key)

    escape_root = tmp_path / "escaped-store"
    escape_root.mkdir()
    sequence_link = store.store_root / "synthetic"
    sequence_link.parent.mkdir(parents=True)
    sequence_link.symlink_to(escape_root, target_is_directory=True)
    with pytest.raises(RuntimeError, match="outside entry root"):
        store.load_entry_by_key_for_runtime(sequence_id="synthetic", profile_key=valid_key)


def test_record3d_normalized_store_rejects_tampered_manifest_paths(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    store = fixture.store
    profile = fixture.profile
    entry = fixture.entry
    manifest = json.loads(entry.sequence_manifest_path.read_text(encoding="utf-8"))
    manifest["rgb_dir"] = (tmp_path / "outside-rgb").as_posix()
    entry.sequence_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside entry root"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="outside entry root"):
        store.summary()


def test_record3d_normalized_store_rejects_tampered_observation_paths(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    store = fixture.store
    profile = fixture.profile
    entry = fixture.entry
    benchmark_inputs = json.loads(entry.benchmark_inputs_path.read_text(encoding="utf-8"))
    index_path = Path(benchmark_inputs["observation_sequences"][0]["index_path"])
    observation_index = json.loads(index_path.read_text(encoding="utf-8"))
    observation_index["rows"][0]["depth_path"] = (tmp_path / "outside-depth.npy").as_posix()
    index_path.write_text(json.dumps(observation_index), encoding="utf-8")

    with pytest.raises(RuntimeError, match="outside entry root"):
        store.load_entry(profile)
    with pytest.raises(RuntimeError, match="outside entry root"):
        store.summary()


def test_normalized_store_rejects_invalid_analysis_table_header(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    fixture.entry.stats_long_path.write_text("bad,header\n1,2\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="invalid CSV header"):
        fixture.store.load_entry(fixture.profile)
    assert fixture.store.summary(strict=False) == []


def test_record3d_dataset_source_requires_normalized_store_entry(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    source = Record3DDatasetSourceConfig(sequence_id="synthetic").setup_target(path_config=path_config)

    with pytest.raises(FileNotFoundError, match="prml-vslam dataset normalize --dataset record3d"):
        source.prepare_sequence_manifest(tmp_path / "run" / "input")


def test_record3d_normalization_materializer_does_not_stream_raw_dataset(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path / ".data" / "record3d")
    path_config = PathConfig(root=tmp_path, data_dir=tmp_path / ".data")
    service = Record3DDatasetService(path_config)
    source = service._build_normalization_materializer(
        sequence_id="synthetic",
        frame_selection=FrameSelectionConfig(target_fps=5.0),
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )

    assert not hasattr(source, "open_stream")
    source.prepare_sequence_manifest(tmp_path / "source")
    benchmark_inputs = source.prepare_benchmark_inputs(tmp_path / "benchmark")
    index = ObservationSequenceIndex.model_validate_json(
        benchmark_inputs.observation_sequences[0].index_path.read_text(encoding="utf-8")
    )
    assert [row.provenance.source_frame_index for row in index.rows] == [0, 2]


def test_record3d_preview_stream_does_not_require_reference_cloud_points(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(min_confidence=3),
        )
    )

    stream = sequence.open_stream(loop=False, replay_mode=ReplayMode.FAST_AS_POSSIBLE)
    stream.connect()
    packet = stream.wait_for_observation()

    assert packet.rgb is not None
    assert packet.depth_m is not None
    with pytest.raises(RuntimeError, match="no valid points"):
        sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")


def test_record3d_benchmark_inputs_honor_source_frame_selection(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(
            dataset_root=tmp_path,
            sequence_id="synthetic",
            reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=100, random_seed=17, min_confidence=1),
        )
    )

    benchmark_inputs = sequence.to_benchmark_inputs(
        output_dir=tmp_path / "benchmark",
        frame_selection=FrameSelectionConfig(frame_stride=2),
    )

    observation_index = json.loads(benchmark_inputs.observation_sequences[0].index_path.read_text(encoding="utf-8"))
    metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert [row["provenance"]["source_frame_index"] for row in observation_index["rows"]] == [0, 2]
    assert metadata["selected_frame_count"] == 2
    assert metadata["source_frame_indices"] == [0, 2]
    assert metadata["source_timestamps_ns"] == [0, 200_000_000]
    for stale_key in (
        "method_sample_count",
        "frame_count",
        "sampled_frame_count",
        "contributing_source_frame_indices",
        "reference_cloud_sampled_frame_indices",
        "reference_cloud_sampled_timestamps_ns",
    ):
        assert stale_key not in metadata


def test_record3d_reference_cloud_config_controls_sampling_and_metadata(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path)
    base_config = Record3DSequenceConfig(
        dataset_root=tmp_path,
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=1, min_confidence=1),
    )
    repeat_config = base_config.model_copy(
        update={
            "reference_cloud": ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=1, min_confidence=1)
        }
    )
    different_seed_config = base_config.model_copy(
        update={
            "reference_cloud": ReferenceCloudConfig(depth_stride_px=1, max_points=6, random_seed=2, min_confidence=1)
        }
    )

    first_inputs = Record3DSequence(config=base_config).to_benchmark_inputs(output_dir=tmp_path / "first")
    repeat_inputs = Record3DSequence(config=repeat_config).to_benchmark_inputs(output_dir=tmp_path / "repeat")
    different_seed_inputs = Record3DSequence(config=different_seed_config).to_benchmark_inputs(
        output_dir=tmp_path / "different-seed"
    )
    points_first, _colors_first = load_point_cloud_ply_with_colors(first_inputs.reference_clouds[0].path)
    points_repeat, _colors_repeat = load_point_cloud_ply_with_colors(repeat_inputs.reference_clouds[0].path)
    points_different_seed, _colors_different_seed = load_point_cloud_ply_with_colors(
        different_seed_inputs.reference_clouds[0].path
    )
    metadata = json.loads(first_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert metadata["depth_stride_px"] == 1
    assert metadata["max_points"] == 6
    assert metadata["min_confidence"] == 1
    assert metadata["random_seed"] == 1
    assert metadata["point_count_before_sampling"] > 6
    assert metadata["point_sampling_policy"] == "random_without_replacement"
    for stale_key in ("depth_pixel_stride_px", "max_reference_points", "seed", "point_sampling_seed", "point_count"):
        assert stale_key not in metadata
    np.testing.assert_allclose(points_repeat, points_first)
    assert not np.allclose(points_different_seed, points_first)


def test_record3d_source_config_accepts_reference_cloud_block_and_rejects_old_materialization_cloud_keys() -> None:
    source = SourceStageConfig.from_toml(
        """
        [backend]
        source_id = "record3d_dataset"
        sequence_id = "synthetic"

        [backend.reference_cloud]
        depth_stride_px = 4
        max_points = 64
        random_seed = 5
        min_confidence = 2

        rgb_max_width_px = 392
        rgb_dimension_multiple = 14
        """
    )
    reloaded = SourceStageConfig.from_toml(source.to_toml())

    assert isinstance(source.backend, Record3DDatasetSourceConfig)
    assert source.backend.reference_cloud.depth_stride_px == 4
    assert source.backend.reference_cloud.max_points == 64
    assert source.backend.reference_cloud.random_seed == 5
    assert source.backend.reference_cloud.min_confidence == 2
    assert source.backend.rgb_max_width_px == 392
    assert source.backend.rgb_dimension_multiple == 14
    assert isinstance(reloaded.backend, Record3DDatasetSourceConfig)
    assert reloaded.backend.reference_cloud == source.backend.reference_cloud
    assert reloaded.backend.rgb_max_width_px == 392
    assert reloaded.backend.rgb_dimension_multiple == 14

    removed_shapes = [
        {"materialization": {"reference_cloud_max_points": 64}},
        {"reference_cloud_max_points": 64},
        {"reference_cloud_frame_stride": 2},
        {"reference_cloud_pixel_stride": 4},
        {"reference_cloud_min_confidence": 1},
    ]
    for removed_shape in removed_shapes:
        with pytest.raises(ValidationError):
            SourceStageConfig.model_validate(
                {
                    "backend": {
                        "source_id": "record3d_dataset",
                        "sequence_id": "synthetic",
                        **removed_shape,
                    }
                }
            )


def test_record3d_archive_frames_must_match_metadata_indices(tmp_path: Path) -> None:
    _write_record3d_archive(tmp_path, frame_indices=(1, 2, 3))
    sequence = Record3DSequence(config=Record3DSequenceConfig(dataset_root=tmp_path, sequence_id="synthetic"))

    with pytest.raises(ValueError, match="consecutively numbered"):
        sequence.load_offline_sample()


def test_record3d_source_config_plans_arkit_and_cloud_alignment_path(tmp_path: Path) -> None:
    fixture = _create_record3d_normalized_entry(tmp_path)
    path_config = fixture.path_config.model_copy(update={"artifacts_dir": tmp_path / ".artifacts"})
    source_backend = Record3DDatasetSourceConfig(
        sequence_id="synthetic",
        reference_cloud=ReferenceCloudConfig(depth_stride_px=1, max_points=20, min_confidence=1),
    )
    run_config = build_run_config(
        experiment_name="record3d-plan",
        output_dir=path_config.artifacts_dir,
        source_backend=source_backend,
        method=MethodId.VISTA,
        trajectory_alignment_enabled=True,
        trajectory_baseline=ReferenceSource.ARKIT,
        cloud_alignment_enabled=True,
        reference_enabled=False,
    )

    plan = run_config.compile_plan(path_config, fail_on_unavailable=True)

    assert run_config.stages.align_trajectory.baseline_source is ReferenceSource.ARKIT
    assert run_config.stages.align_cloud.enabled is True
    assert plan.source.source_id == "record3d_dataset"
    assert plan.source.sequence_id == "synthetic"
    assert plan.source.replay_mode == "realtime"
    assert plan.source.expected_fps == pytest.approx(10.0)
    assert plan.source.metadata["dataset_id"] == DatasetId.RECORD3D.value
    assert plan.source.metadata["pose_source"] == ReferenceSource.ARKIT.value
    assert plan.source.metadata["reference_cloud_source"] == ReferenceCloudSource.RECORD3D_LIDAR.value
    assert plan.source.metadata["reference_cloud_depth_stride_px"] == 1
    assert plan.source.metadata["reference_cloud_max_points"] == 20
    assert plan.source.metadata["reference_cloud_random_seed"] == 17
    assert plan.source.metadata["reference_cloud_min_confidence"] == 1
    assert next(stage for stage in plan.stages if stage.key is StageKey.CLOUD_ALIGNMENT).available is True


def test_record3d_real_sample_decodes_rgbd_and_materializes_reference_cloud(tmp_path: Path) -> None:
    dataset_root = PathConfig().resolve_dataset_dir("record3d")
    archive_path = next(
        (
            dataset_root / archive_name
            for archive_name in (
                "2024-03-31--16-17-17.r3d",
                "2026-06-03--18-26-32.r3d",
            )
            if (dataset_root / archive_name).exists()
        ),
        dataset_root / "2024-03-31--16-17-17.r3d",
    )
    if not archive_path.exists():
        pytest.skip(f"Record3D sample is not present: {archive_path}")
    sequence = Record3DSequence(
        config=Record3DSequenceConfig(dataset_root=archive_path.parent, sequence_id=archive_path.stem)
    )

    sample = sequence.load_offline_sample()
    benchmark_inputs = sequence.to_benchmark_inputs(output_dir=tmp_path / "benchmark")
    observations = list(FileObservationSequenceLoader(benchmark_inputs.observation_sequences[0]).iter_observations())
    cloud_metadata = json.loads(benchmark_inputs.reference_clouds[0].metadata_path.read_text(encoding="utf-8"))

    assert len(sample.frames) > 0
    assert sample.metadata.dw > 0
    assert sample.metadata.dh > 0
    assert observations[0].rgb.shape[:2] == observations[0].depth_m.shape
    assert observations[0].rgb.shape[1] <= sequence.config.rgb_max_width_px
    assert observations[0].intrinsics.width_px == observations[0].rgb.shape[1]
    assert observations[0].intrinsics.height_px == observations[0].rgb.shape[0]
    assert benchmark_inputs.reference_clouds[0].path.exists()
    assert cloud_metadata["point_count_after_sampling"] > 0
    assert cloud_metadata["point_count_after_sampling"] <= cloud_metadata["max_points"]
    assert cloud_metadata["depth_stride_px"] == 8
    assert cloud_metadata["min_confidence"] == 1
