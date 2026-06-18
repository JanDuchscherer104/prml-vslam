"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
    class FakeEntry:
        def model_dump(self, *, mode: str) -> dict[str, str]:
            return {"sequence_id": "synthetic", "mode": mode}

    class FakeStore:
        store_root = tmp_path / ".data" / "vslam-datastore" / "record3d"

        def summary(self) -> list[FakeEntry]:
            return [FakeEntry()]

    monkeypatch.setattr(main_module, "normalized_store_for_service", lambda dataset_id, path_config: FakeStore())
    monkeypatch.setattr(
        main_module,
        "normalized_entry_analysis_summary",
        lambda entry: {"stats_long_row_count": 9, "metadata_long_row_count": 4},
    )

    result = runner.invoke(app, ["dataset", "summary", "--dataset", "record3d"])

    assert result.exit_code == 0
    assert "record3d" in result.stdout
    assert "vslam-datastore" in result.stdout
    assert "'analysis'" in result.stdout
    assert "'stats_long_row_count': 9" in result.stdout


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
