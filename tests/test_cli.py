"""CLI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
import typer
from click.utils import strip_ansi
from typer.testing import CliRunner

import prml_vslam.main as main_module
from prml_vslam.main import Record3DStreamConfig, _apply_dotted_overrides_to_run_config, app
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.sources.config import Record3DDatasetSourceConfig, VideoSourceConfig
from prml_vslam.sources.datasets.advio import AdvioDownloadRequest
from prml_vslam.sources.datasets.contracts import DatasetId, ReferenceCloudConfig
from prml_vslam.sources.datasets.normalization import NormalizedDatasetBuildConfig
from prml_vslam.sources.datasets.normalized_query import NormalizedDatasetQuery, NormalizedSequenceRecord
from prml_vslam.sources.datasets.normalized_store import STORE_SCHEMA_VERSION, NormalizedDatasetEntry
from prml_vslam.sources.datasets.record3d import Record3DDownloadRequest
from prml_vslam.sources.datasets.tum_rgbd import TumRgbdDownloadRequest
from prml_vslam.utils import PathConfig

runner = CliRunner()


def test_record3d_devices_command_runs(monkeypatch) -> None:
    class FakeDevice:
        def __init__(self, product_id: int, udid: str) -> None:
            self.product_id = product_id
            self.udid = udid

        def model_dump(self, *, mode: str) -> dict[str, object]:
            return {"product_id": self.product_id, "udid": self.udid, "mode": mode}

    class FakeSession:
        def list_devices(self) -> list[FakeDevice]:
            return [FakeDevice(product_id=42, udid="device-42")]

    monkeypatch.setattr(Record3DStreamConfig, "setup_target", lambda self: FakeSession())

    result = runner.invoke(app, ["record3d-devices"])

    assert result.exit_code == 0
    assert "device-42" in result.stdout


def test_record3d_download_command_builds_zero_based_sequence_request(monkeypatch) -> None:
    seen_requests: list[Record3DDownloadRequest] = []

    class FakeService:
        dataset_root = Path(".data/record3d")

        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def download(self, request: Record3DDownloadRequest) -> SimpleNamespace:
            seen_requests.append(request)
            return SimpleNamespace(
                model_dump=lambda *, mode: {
                    "sequence_ids": request.sequence_ids,
                    "downloaded_archive_count": 1,
                    "reused_archive_count": 0,
                    "written_path_count": 1,
                    "mode": mode,
                }
            )

        def summarize(self) -> SimpleNamespace:
            return SimpleNamespace(model_dump=lambda *, mode: {"total_scene_count": 8, "mode": mode})

    monkeypatch.setattr(main_module, "Record3DDatasetService", FakeService)

    result = runner.invoke(app, ["record3d", "download", "--sequence", "3"])

    assert result.exit_code == 0
    assert seen_requests == [Record3DDownloadRequest(sequence_ids=[3])]
    assert "downloaded_archive_count" in result.stdout


def test_record3d_download_rejects_invalid_sequence_index() -> None:
    result = runner.invoke(app, ["record3d", "download", "--sequence", "8"])

    assert result.exit_code == 1
    assert "[0, 7]" in result.stdout


def test_dataset_summary_accepts_record3d_alias(monkeypatch, tmp_path: Path) -> None:
    normalized = NormalizedDatasetQuery(
        dataset_id=DatasetId.RECORD3D,
        records=[
            NormalizedSequenceRecord(
                dataset_id=DatasetId.RECORD3D,
                sequence_id="synthetic",
                sequence_label="Synthetic",
                source_id="record3d_dataset",
                profile_key="profile",
                root=tmp_path / ".data" / "vslam-datastore" / "record3d" / "synthetic" / "profile",
                is_default_profile=True,
                stats_row_count=9,
                metadata_row_count=4,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                {
                    "dataset_id": "record3d",
                    "sequence_id": "synthetic",
                    "profile_key": "profile",
                    "source_id": "record3d_dataset",
                    "scope": "observation_sequence",
                    "subject": "record3d_dataset",
                    "stat": "observation_frame_count",
                    "value": "30",
                    "unit": "count",
                }
            ]
        ),
        metadata_df=pd.DataFrame(),
    )
    monkeypatch.setattr(main_module, "query_normalized_dataset", lambda dataset_id, path_config: normalized)

    result = runner.invoke(app, ["dataset", "summary", "--dataset", "record3d"])

    assert result.exit_code == 0
    assert "record3d" in result.stdout
    assert "vslam-datastore" in result.stdout
    assert "'record_count': 1" in result.stdout
    assert "'observation_frame_count': '30'" in result.stdout
    assert "'entries'" not in result.stdout


def test_dataset_inspect_reports_single_entry_metadata(monkeypatch, tmp_path: Path) -> None:
    entry_root = tmp_path / ".data" / "vslam-datastore" / "record3d" / "synthetic" / "profile"
    entry_root.mkdir(parents=True)
    manifest_path = entry_root / "sequence_manifest.json"
    benchmark_path = entry_root / "benchmark_inputs.json"
    manifest_path.write_text(
        '{"sequence_id":"synthetic","dataset_id":"record3d","rgb_dir":"observations/rgb"}',
        encoding="utf-8",
    )
    benchmark_path.write_text(
        '{"reference_trajectories":[],"candidate_trajectories":[],"reference_clouds":[],"observation_sequences":[]}',
        encoding="utf-8",
    )
    entry = NormalizedDatasetEntry(
        schema_version=STORE_SCHEMA_VERSION,
        dataset_id=DatasetId.RECORD3D,
        sequence_id="synthetic",
        source_id="record3d_dataset",
        profile_key="profile",
        profile={},
        root=entry_root,
        sequence_manifest_path=manifest_path,
        benchmark_inputs_path=benchmark_path,
    )
    (entry_root / "entry.json").write_text(entry.model_dump_json(), encoding="utf-8")
    normalized = NormalizedDatasetQuery(
        dataset_id=DatasetId.RECORD3D,
        records=[
            NormalizedSequenceRecord(
                dataset_id=DatasetId.RECORD3D,
                sequence_id="synthetic",
                sequence_label="Synthetic",
                source_id="record3d_dataset",
                profile_key="profile",
                root=entry_root,
                is_default_profile=True,
                stats_row_count=1,
                metadata_row_count=1,
            )
        ],
        issues=[],
        stats_df=pd.DataFrame.from_records(
            [
                {
                    "dataset_id": "record3d",
                    "sequence_id": "synthetic",
                    "profile_key": "profile",
                    "source_id": "record3d_dataset",
                    "scope": "reference_trajectory",
                    "subject": "ground_truth/source_native",
                    "stat": "trajectory_path_length_m",
                    "value": "1.5",
                    "unit": "m",
                }
            ]
        ),
        metadata_df=pd.DataFrame.from_records(
            [
                {
                    "dataset_id": "record3d",
                    "sequence_id": "synthetic",
                    "profile_key": "profile",
                    "source_id": "record3d_dataset",
                    "scope": "sequence",
                    "key": "rgb_dir",
                    "value": "observations/rgb",
                }
            ]
        ),
    )
    monkeypatch.setattr(main_module, "query_normalized_dataset", lambda dataset_id, path_config: normalized)

    result = runner.invoke(app, ["dataset", "inspect", "--dataset", "record3d", "--sequence", "synthetic"])

    assert result.exit_code == 0
    assert "'sequence_manifest'" in result.stdout
    assert "'trajectory_path_length_m'" in result.stdout
    assert "'rgb_dir'" in result.stdout


def test_advio_summary_reports_normalized_entries_and_native_cache(monkeypatch) -> None:
    class FakeService:
        dataset_root = Path(".data/advio")
        catalog = SimpleNamespace(
            upstream=SimpleNamespace(model_dump=lambda *, mode: {"repo_url": "https://example.test", "mode": mode}),
            scenes=[SimpleNamespace(archive_size_bytes=123)],
        )

        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def local_scene_statuses(self) -> list[SimpleNamespace]:
            return [
                SimpleNamespace(
                    scene=SimpleNamespace(sequence_id=15),
                    sequence_dir=Path(".data/advio/advio-15"),
                    archive_path=Path(".data/advio/advio-15.zip"),
                )
            ]

    normalized = SimpleNamespace(model_dump=lambda *, mode: {"records": [{"sequence_id": "advio-15"}], "mode": mode})
    monkeypatch.setattr(main_module, "AdvioDatasetService", FakeService)
    monkeypatch.setattr(main_module, "query_normalized_dataset", lambda dataset_id, path_config: normalized)

    result = runner.invoke(app, ["advio", "summary"])

    assert result.exit_code == 0
    assert "'normalized': {'records': [{'sequence_id': 'advio-15'}], 'mode': 'json'}" in result.stdout
    assert "'native_cache':" in result.stdout
    assert "'sequence_ids': [15]" in result.stdout
    assert "'archive_sequence_ids': [15]" in result.stdout
    assert "'total_remote_archive_bytes': 123" in result.stdout
    assert "'summary':" not in result.stdout
    assert "replay_ready_scene_count" not in result.stdout
    assert "offline_ready_scene_count" not in result.stdout
    assert "'local_sequence_ids'" not in result.stdout


def test_dataset_normalize_defaults_to_all_local_sequences_and_cpu_workers(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeService:
        dataset_root = Path(".data/record3d")

        def list_local_sequence_ids(self) -> list[str]:
            return ["scene-a", "scene-b"]

    class FakeEntry:
        def __init__(self, sequence_id: str) -> None:
            self.sequence_id = sequence_id

        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": self.sequence_id, "mode": mode}

    def fake_normalize_dataset_entries(**kwargs):
        captured.update(kwargs)
        return [FakeEntry(sequence_id) for sequence_id in kwargs["sequence_ids"]]

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())
    monkeypatch.setattr(main_module.os, "cpu_count", lambda: 7)
    monkeypatch.setattr(main_module, "normalize_dataset_entries", fake_normalize_dataset_entries)

    result = runner.invoke(app, ["dataset", "normalize", "--dataset", "record3d"])

    assert result.exit_code == 0
    assert captured["sequence_ids"] == ["scene-a", "scene-b"]
    assert captured["workers"] == 7
    assert captured["frame_selection"].frame_stride == 1
    assert captured["frame_selection"].target_fps == 15.0
    assert "'sequence_count': 2" in result.stdout
    assert "'frame_stride': 1" in result.stdout
    assert "'target_fps': 15.0" in result.stdout
    assert "'workers': 2" in result.stdout
    assert "'entries'" in result.stdout


def test_dataset_normalize_advio_defaults_to_10_fps(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeService:
        dataset_root = Path(".data/advio")

        def list_local_sequence_ids(self) -> list[str]:
            return ["advio-21"]

    class FakeEntry:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": "advio-21", "mode": mode}

    def fake_normalize_dataset_entries(**kwargs):
        captured.update(kwargs)
        return [FakeEntry()]

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())
    monkeypatch.setattr(main_module, "normalize_dataset_entries", fake_normalize_dataset_entries)

    result = runner.invoke(app, ["dataset", "normalize", "--dataset", "advio", "--sequence", "advio-21"])

    assert result.exit_code == 0
    assert captured["frame_selection"].frame_stride == 1
    assert captured["frame_selection"].target_fps == 10.0
    assert "'target_fps': 10.0" in result.stdout


def test_dataset_normalize_frame_stride_clears_default_target_fps(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    class FakeService:
        dataset_root = Path(".data/record3d")

        def list_local_sequence_ids(self) -> list[str]:
            return ["scene-a"]

    class FakeEntry:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": "scene-a", "mode": mode}

    def fake_normalize_dataset_entries(**kwargs):
        captured.update(kwargs)
        return [FakeEntry()]

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())
    monkeypatch.setattr(main_module, "normalize_dataset_entries", fake_normalize_dataset_entries)

    result = runner.invoke(app, ["dataset", "normalize", "--dataset", "record3d", "--frame-stride", "2"])

    assert result.exit_code == 0
    assert captured["frame_selection"].frame_stride == 2
    assert captured["frame_selection"].target_fps is None
    assert "'frame_stride': 2" in result.stdout
    assert "'target_fps': None" in result.stdout


def test_dataset_normalize_preserves_single_sequence_entry_payload(monkeypatch) -> None:
    class FakeService:
        dataset_root = Path(".data/record3d")

        def list_local_sequence_ids(self) -> list[str]:
            raise AssertionError("explicit sequence should not list local ids")

    class FakeEntry:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": "scene-a", "mode": mode}

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())
    monkeypatch.setattr(main_module, "normalize_dataset_entries", lambda **kwargs: [FakeEntry()])

    result = runner.invoke(app, ["dataset", "normalize", "--dataset", "record3d", "--sequence", "scene-a"])

    assert result.exit_code == 0
    assert "'entry'" in result.stdout
    assert "'entries'" not in result.stdout


def test_dataset_normalize_accepts_typed_source_config_toml(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    source_config = Record3DDatasetSourceConfig(
        sequence_id="scene-a",
        target_fps=12.0,
        rgb_max_width_px=280,
        rgb_dimension_multiple=14,
        reference_cloud=ReferenceCloudConfig(depth_stride_px=4, max_points=64, min_confidence=2),
    )
    config_path = tmp_path / "record3d-source.toml"
    source_config.save_toml(config_path)

    class FakeService:
        dataset_root = Path(".data/record3d")

    class FakeEntry:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": "scene-a", "mode": mode}

    def fake_normalize_dataset_entry(**kwargs):
        captured.update(kwargs)
        return FakeEntry()

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())
    monkeypatch.setattr(main_module, "normalize_dataset_entry", fake_normalize_dataset_entry)

    result = runner.invoke(app, ["dataset", "normalize", "--source-config", str(config_path)])

    assert result.exit_code == 0
    assert captured["dataset_id"] is DatasetId.RECORD3D
    assert captured["source_config"] == source_config
    assert "'rgb_max_width_px': 280" in result.stdout
    assert "'target_fps': 12.0" in result.stdout
    assert "'entry'" in result.stdout


def test_dataset_normalize_accepts_benchmark_build_config_toml(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}
    build_config = NormalizedDatasetBuildConfig(
        workers=4,
        sources=[
            Record3DDatasetSourceConfig(sequence_id="scene-a", target_fps=30.0),
            Record3DDatasetSourceConfig(sequence_id="scene-b", frame_stride=2),
        ],
    )
    config_path = tmp_path / "benchmark-vslam-datastore.toml"
    build_config.save_toml(config_path)

    class FakeEntry:
        def __init__(self, sequence_id: str) -> None:
            self.sequence_id = sequence_id

        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": self.sequence_id, "mode": mode}

    def fake_normalize_dataset_source_configs(**kwargs):
        captured.update(kwargs)
        return [FakeEntry(source.sequence_id) for source in kwargs["source_configs"]]

    monkeypatch.setattr(main_module, "normalize_dataset_source_configs", fake_normalize_dataset_source_configs)

    result = runner.invoke(app, ["dataset", "normalize", "--config", str(config_path)])

    assert result.exit_code == 0
    assert [source.sequence_id for source in captured["source_configs"]] == ["scene-a", "scene-b"]
    assert captured["workers"] == 4
    assert "'source_count': 2" in result.stdout
    assert "'workers': 2" in result.stdout
    assert "'entries'" in result.stdout


def test_dataset_normalize_rejects_runtime_and_normalize_time_sampling_mix(monkeypatch) -> None:
    class FakeService:
        dataset_root = Path(".data/record3d")

        def list_local_sequence_ids(self) -> list[str]:
            return ["scene-a"]

    monkeypatch.setattr(main_module, "dataset_service", lambda dataset_id, path_config: FakeService())

    result = runner.invoke(
        app,
        ["dataset", "normalize", "--dataset", "record3d", "--frame-stride", "2", "--target-fps", "5.0"],
    )

    assert result.exit_code != 0
    assert "Configure either `frame_stride` or `target_fps`, not both." in result.stderr


@pytest.mark.parametrize("command", (("advio", "download"), ("tum-rgbd", "download")))
def test_dataset_download_commands_expose_only_full_scene_options(command: tuple[str, str]) -> None:
    result = runner.invoke(app, [*command, "--help"])
    help_text = strip_ansi(result.stdout)

    assert result.exit_code == 0
    assert "--sequence" in help_text
    assert "--overwrite" in help_text
    assert "--reuse" in help_text
    assert "--" + "preset" not in help_text
    assert "--" + "modality" not in help_text


def test_advio_download_command_builds_full_scene_request(monkeypatch) -> None:
    seen_requests: list[AdvioDownloadRequest] = []

    class FakeService:
        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def download(self, request: AdvioDownloadRequest) -> SimpleNamespace:
            seen_requests.append(request)
            return SimpleNamespace(
                model_dump=lambda *, mode: {
                    "sequence_ids": request.sequence_ids,
                    "overwrite": request.overwrite,
                    "downloaded_archive_count": 1,
                    "reused_archive_count": 0,
                    "written_path_count": 3,
                    "mode": mode,
                }
            )

        def summarize(self) -> SimpleNamespace:
            return SimpleNamespace(model_dump=lambda *, mode: {"total_scene_count": 1, "mode": mode})

    monkeypatch.setattr(main_module, "AdvioDatasetService", FakeService)

    result = runner.invoke(app, ["advio", "download", "--sequence", "15", "--overwrite"])

    assert result.exit_code == 0
    assert seen_requests == [AdvioDownloadRequest(sequence_ids=[15], overwrite=True)]


def test_tum_rgbd_download_command_builds_full_scene_request(monkeypatch) -> None:
    seen_requests: list[TumRgbdDownloadRequest] = []

    class FakeService:
        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def download(self, request: TumRgbdDownloadRequest) -> SimpleNamespace:
            seen_requests.append(request)
            return SimpleNamespace(
                model_dump=lambda *, mode: {
                    "sequence_ids": request.sequence_ids,
                    "overwrite": request.overwrite,
                    "downloaded_archive_count": 1,
                    "reused_archive_count": 0,
                    "written_path_count": 3,
                    "mode": mode,
                }
            )

        def summarize(self) -> SimpleNamespace:
            return SimpleNamespace(model_dump=lambda *, mode: {"total_scene_count": 1, "mode": mode})

    monkeypatch.setattr(main_module, "TumRgbdDatasetService", FakeService)

    result = runner.invoke(app, ["tum-rgbd", "download", "--sequence", "freiburg1_desk", "--overwrite"])

    assert result.exit_code == 0
    assert seen_requests == [TumRgbdDownloadRequest(sequence_ids=["freiburg1_desk"], overwrite=True)]


def test_dotted_run_config_overrides_parse_json_and_deep_merge(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="cli-overrides",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        connect_live_viewer=True,
    )

    updated = _apply_dotted_overrides_to_run_config(
        config,
        [
            "--mode",
            '"offline"',
            "--stages.slam.backend.max_frames",
            "100",
            "--stages.slam.outputs",
            '{"emit_dense_points": false}',
            "--reuse_artifact_root",
            str(tmp_path / "old-run"),
            "--visualization.connect_live_viewer",
            "false",
        ],
    )

    assert updated.mode.value == "offline"
    assert updated.stages.slam.backend.max_frames == 100
    assert updated.stages.slam.outputs.emit_dense_points is False
    assert updated.stages.slam.outputs.emit_sparse_points is True
    assert updated.reuse_artifact_root == tmp_path / "old-run"
    assert updated.visualization.connect_live_viewer is False


def test_plan_run_mast3r_defaults_sparse_output_off(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "plan-run",
            "mast3r-cli",
            "captures/demo.mp4",
            "--method",
            "mast3r",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "dense_points.ply" in result.stdout.replace("\n", "")
    assert "'key': 'slam'" in result.stdout
    assert "'available': True" in result.stdout
    assert "does not expose a separate sparse point-cloud artifact" not in result.stdout


def test_plan_run_mast3r_explicit_sparse_output_stays_unavailable(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "plan-run",
            "mast3r-cli",
            "captures/demo.mp4",
            "--method",
            "mast3r",
            "--sparse",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "'key': 'slam'" in result.stdout
    assert "'available': False" in result.stdout
    assert "does not expose a separate sparse point-cloud artifact" in result.stdout


@pytest.mark.parametrize("command", ["run-config", "plan-run-config"])
def test_run_config_help_documents_schema_pure_dotted_overrides(command: str) -> None:
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert "--dataset-frame-stride" not in result.stdout
    assert "--dataset-target-fps" not in result.stdout
    assert "RunConfig Overrides - Run" in result.stdout
    assert "RunConfig Overrides - Source Stage" in result.stdout
    assert "RunConfig Overrides - SLAM Stage" in result.stdout
    assert "RunConfig Overrides - Downstream Stages" in result.stdout
    assert "RunConfig Overrides - Visualization" in result.stdout
    assert "RunConfig Overrides - Runtime" in result.stdout
    assert "RunConfig Override Syntax" in result.stdout
    assert "--mode" in result.stdout
    assert "--reuse_artifact_root" in result.stdout
    assert "--stages.source.backend.frame_stride" in result.stdout
    assert "--stages.source.backend.target_fps" in result.stdout
    assert "--stages.slam.backend.max_frames" in result.stdout
    assert "--stages.align_trajectory.baseline_source" in result.stdout
    assert "--stages.reconstruction.enabled" in result.stdout
    assert "--visualization.connect_live_viewer" in result.stdout
    assert "--ray_local_head_lifecycle" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["--dataset-frame-stride", "5"],
        ["--dataset.frame.stride", "5"],
    ],
)
def test_run_config_overrides_reject_non_schema_paths(tmp_path: Path, args: list[str]) -> None:
    config = build_run_config(
        experiment_name="cli-overrides",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )

    with pytest.raises(typer.BadParameter, match="Invalid RunConfig override"):
        _apply_dotted_overrides_to_run_config(config, args)


def test_run_config_overrides_require_values(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="cli-overrides",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
    )

    with pytest.raises(typer.BadParameter, match="requires a value"):
        _apply_dotted_overrides_to_run_config(config, ["--stages.slam.backend.max_frames"])


def test_eval_trajectory_command_uses_advio_provider_baseline_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = tmp_path / "demo-run"
    estimate_path = artifact_root / "slam" / "trajectory.tum"
    reference_path = artifact_root / "benchmark" / "arcore.tum"
    estimate_path.parent.mkdir(parents=True)
    reference_path.parent.mkdir(parents=True)
    estimate_path.write_text("", encoding="utf-8")
    reference_path.write_text("", encoding="utf-8")
    captured = {}

    class FakeTrajectoryEvaluationService:
        def __init__(self, path_config: PathConfig) -> None:
            self.path_config = path_config

        def compute_evaluation(self, *, selection):
            captured["reference_path"] = selection.reference_path
            return SimpleNamespace(artifact_root=artifact_root, error_series_paths=[])

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))
    monkeypatch.setattr("prml_vslam.eval.services.TrajectoryEvaluationService", FakeTrajectoryEvaluationService)

    result = runner.invoke(app, ["eval-trajectory", str(artifact_root), "--baseline", "arcore", "--sequence-id", "seq"])

    assert result.exit_code == 0
    assert captured["reference_path"] == reference_path


# ---------------------------------------------------------------------------
# Sweep CLI tests
# ---------------------------------------------------------------------------

_VISTA_SLAM_TOML = """\
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id   = "vista"
    max_frames  = 50
    random_seed = 43
"""

_MAST3R_SLAM_TOML = """\
[stages.slam]
enabled  = true
num_gpus = 1.0

    [stages.slam.outputs]
    emit_dense_points  = true
    emit_sparse_points = false

    [stages.slam.backend]
    method_id   = "mast3r"
    max_frames  = 50
    random_seed = 43
"""


def _write_sweep_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (sweep_toml, vista_template, mast3r_template) paths."""
    vista = tmp_path / "vista-slam.toml"
    vista.write_text(_VISTA_SLAM_TOML, encoding="utf-8")
    mast3r = tmp_path / "mast3r-slam.toml"
    mast3r.write_text(_MAST3R_SLAM_TOML, encoding="utf-8")
    sweep = tmp_path / "sweep.toml"
    sweep.write_text(
        f"""\
[sweep]
name       = "cli-sweep"
output_dir = "{(tmp_path / "out").as_posix()}"

[[datasets]]
dataset_id = "tum_rgbd"
sequence_id = "freiburg1_xyz"
frame_stride = 1
baseline_source = "ground_truth"

[[datasets]]
dataset_id = "advio"
sequence_id = "advio-15"
frame_stride = 2

[[datasets]]
dataset_id = "record3d_dataset"
sequence_id = "2026-06-03--18-29-08"
frame_stride = 1
baseline_source = "arkit"

[methods.vista]
config_path = "{vista.as_posix()}"

[methods.mast3r]
config_path = "{mast3r.as_posix()}"
""",
        encoding="utf-8",
    )
    return sweep, vista, mast3r


def test_plan_sweep_config_outputs_valid_json(tmp_path: Path) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)
    result = runner.invoke(app, ["plan-sweep-config", str(sweep)])

    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    run_ids = [item["run_id"] for item in parsed]
    assert "cli-sweep-tum_rgbd-freiburg1_xyz-vista" in run_ids
    assert "cli-sweep-tum_rgbd-freiburg1_xyz-mast3r" in run_ids
    assert "cli-sweep-advio-advio-15-vista" in run_ids
    assert "cli-sweep-advio-advio-15-mast3r" in run_ids
    assert "cli-sweep-record3d_dataset-2026-06-03--18-29-08-vista" in run_ids
    assert "cli-sweep-record3d_dataset-2026-06-03--18-29-08-mast3r" in run_ids


def test_plan_sweep_config_stable_ordering(tmp_path: Path) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)
    result = runner.invoke(app, ["plan-sweep-config", str(sweep)])

    assert result.exit_code == 0, result.output
    positions = [
        result.stdout.find(rid)
        for rid in [
            "cli-sweep-tum_rgbd-freiburg1_xyz-vista",
            "cli-sweep-tum_rgbd-freiburg1_xyz-mast3r",
            "cli-sweep-advio-advio-15-vista",
            "cli-sweep-advio-advio-15-mast3r",
            "cli-sweep-record3d_dataset-2026-06-03--18-29-08-vista",
            "cli-sweep-record3d_dataset-2026-06-03--18-29-08-mast3r",
        ]
    ]
    assert positions == sorted(positions), "Run IDs must appear in dataset×method order"


def test_plan_sweep_config_fails_on_missing_template(tmp_path: Path) -> None:
    sweep = tmp_path / "sweep.toml"
    sweep.write_text(
        """\
[sweep]
name       = "bad-sweep"
output_dir = ".artifacts/sweeps"

[[datasets]]
dataset_id  = "tum_rgbd"
sequence_id = "freiburg1_xyz"

[methods.vista]
config_path = "/nonexistent/path/vista.toml"
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["plan-sweep-config", str(sweep)])
    assert result.exit_code == 1


def test_run_sweep_config_fail_fast_stops_on_first_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)
    executed: list[str] = []

    def fake_run_config_loaded(*, run_cfg, path_config):
        executed.append(run_cfg.experiment_name)
        raise typer.Exit(code=1)

    monkeypatch.setattr("prml_vslam.main._run_config_loaded", fake_run_config_loaded)
    monkeypatch.setattr("prml_vslam.main._preflight_sweep_normalized_entries", lambda items, *, path_config: None)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    result = runner.invoke(app, ["run-sweep-config", str(sweep), "--fail-fast"])

    assert result.exit_code == 1
    assert len(executed) == 1, "fail-fast must stop after the first failure"


def test_run_sweep_config_continue_on_failure_attempts_all_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)
    executed: list[str] = []

    def fake_run_config_loaded(*, run_cfg, path_config):
        executed.append(run_cfg.experiment_name)
        raise typer.Exit(code=1)

    monkeypatch.setattr("prml_vslam.main._run_config_loaded", fake_run_config_loaded)
    monkeypatch.setattr("prml_vslam.main._preflight_sweep_normalized_entries", lambda items, *, path_config: None)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    result = runner.invoke(app, ["run-sweep-config", str(sweep), "--continue-on-failure"])

    assert result.exit_code == 1
    assert len(executed) == 6, "continue-on-failure must attempt all six runs"


def test_run_sweep_config_exits_zero_when_all_succeed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)

    def fake_run_config_loaded(*, run_cfg, path_config):
        pass  # success

    monkeypatch.setattr("prml_vslam.main._run_config_loaded", fake_run_config_loaded)
    monkeypatch.setattr("prml_vslam.main._preflight_sweep_normalized_entries", lambda items, *, path_config: None)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    result = runner.invoke(app, ["run-sweep-config", str(sweep)])

    assert result.exit_code == 0


def test_run_sweep_config_preflights_normalized_datastore_before_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sweep, _, _ = _write_sweep_fixtures(tmp_path)
    executed: list[str] = []

    def fake_run_config_loaded(*, run_cfg, path_config):
        executed.append(run_cfg.experiment_name)

    monkeypatch.setattr("prml_vslam.main._run_config_loaded", fake_run_config_loaded)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))

    result = runner.invoke(app, ["run-sweep-config", str(sweep)])

    assert result.exit_code == 1
    assert "Sweep normalized datastore preflight failed" in result.output
    assert executed == []
