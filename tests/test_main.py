"""Focused CLI tests for ADVIO dataset commands."""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

from prml_vslam import main
from prml_vslam.datasets.advio import (
    AdvioCatalog,
    AdvioDatasetService,
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioDownloadResult,
    AdvioEnvironment,
    AdvioPeopleLevel,
    AdvioSceneMetadata,
    AdvioUpstreamMetadata,
)
from prml_vslam.utils import PathConfig


def _fake_advio_service(tmp_path: Path) -> AdvioDatasetService:
    catalog = AdvioCatalog(
        dataset_id="advio",
        dataset_label="ADVIO",
        upstream=AdvioUpstreamMetadata(
            repo_url="https://github.com/AaltoVision/ADVIO",
            zenodo_record_url="https://zenodo.org/records/1476931",
            doi="10.5281/zenodo.1320824",
            license="CC BY-NC 4.0",
            calibration_base_url="https://raw.githubusercontent.com/AaltoVision/ADVIO/master/calibration/",
        ),
        scenes=[
            AdvioSceneMetadata(
                sequence_id=15,
                sequence_slug="advio-15",
                venue="Office",
                dataset_code="03",
                environment=AdvioEnvironment.INDOOR,
                has_stairs=False,
                has_escalator=False,
                has_elevator=False,
                people_level=AdvioPeopleLevel.NONE,
                has_vehicles=False,
                calibration_name="iphone-03.yaml",
                archive_url="https://zenodo.org/api/records/1476931/files/advio-15.zip/content",
                archive_size_bytes=54_845_329,
                archive_md5="f5febcd087acd90531aea98efff71c7c",
            )
        ],
    )
    return AdvioDatasetService(PathConfig(root=tmp_path), catalog=catalog)


def test_advio_download_command_builds_explicit_request(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    captured: dict[str, object] = {}

    class FakeService:
        catalog = _fake_advio_service(tmp_path).catalog

        def __init__(self, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def download(self, request: AdvioDownloadRequest) -> AdvioDownloadResult:
            captured["request"] = request
            return AdvioDownloadResult(
                sequence_ids=request.sequence_ids, modalities=list(request.resolved_modalities())
            )

        def summarize(self) -> object:
            return _fake_advio_service(tmp_path).summarize()

    monkeypatch.setattr(main, "AdvioDatasetService", FakeService)
    monkeypatch.setattr(main, "get_path_config", lambda: PathConfig(root=tmp_path))

    result = runner.invoke(
        main.app,
        [
            "advio",
            "download",
            "--sequence",
            "15",
            "--preset",
            AdvioDownloadPreset.STREAMING.value,
        ],
    )

    assert result.exit_code == 0
    request = captured["request"]
    assert isinstance(request, AdvioDownloadRequest)
    assert request.sequence_ids == [15]
    assert request.preset is AdvioDownloadPreset.STREAMING


def test_plan_run_config_command_loads_toml_request(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    captured: dict[str, object] = {}
    config_path = tmp_path / "configs" / "advio-vista.toml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
experiment_name = "Advio Office Offline Vista"
mode = "offline"
output_dir = ".artifacts"

[source]
video_path = "captures/office-03.mp4"
frame_stride = 2

[slam]
method = "vista"
emit_dense_points = true
emit_sparse_points = true

[reference]
enabled = false

[evaluation]
compare_to_arcore = true
evaluate_cloud = false
evaluate_efficiency = true
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "get_path_config", lambda: PathConfig(root=tmp_path))
    monkeypatch.setattr(main.console, "plog", lambda payload: captured.setdefault("payload", payload))

    result = runner.invoke(main.app, ["plan-run-config", "configs/advio-vista.toml"])

    assert result.exit_code == 0
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["run_id"] == "advio-office-offline-vista"
    assert payload["method"] == "vista"
    assert payload["source"]["video_path"] == "captures/office-03.mp4"


def test_root_cli_defaults_to_offline_pipeline_demo(monkeypatch) -> None:
    runner = CliRunner()
    captured: dict[str, object] = {}

    def fake_pipeline_demo() -> None:
        captured["called"] = True

    monkeypatch.setattr(main, "pipeline_demo", fake_pipeline_demo)

    result = runner.invoke(main.app, [])

    assert result.exit_code == 0
    assert captured == {"called": True}


def test_pipeline_demo_command_reuses_shared_demo_request(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    captured: dict[str, object] = {}

    class FakeService:
        def __init__(self, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def local_scene_statuses(self) -> list[object]:
            return [SimpleNamespace(scene=SimpleNamespace(sequence_id=15), replay_ready=True)]

        def scene(self, sequence_id: int) -> object:
            captured["sequence_id"] = sequence_id
            return SimpleNamespace(sequence_slug="advio-15", display_name="ADVIO 15")

        def build_streaming_source(
            self,
            *,
            sequence_id: int,
            pose_source,
            respect_video_rotation: bool,
        ) -> object:
            captured["source_args"] = {
                "sequence_id": sequence_id,
                "pose_source": pose_source,
                "respect_video_rotation": respect_video_rotation,
            }
            return "streaming-source"

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["run_service_path_config"] = path_config

        def start_run(self, *, request, source) -> None:
            captured["request"] = request
            captured["source"] = source

        def snapshot(self):
            return main.PipelineSessionSnapshot(state=main.PipelineSessionState.COMPLETED)

        def stop_run(self) -> None:
            captured["stopped"] = True

    monkeypatch.setattr(main, "AdvioDatasetService", FakeService)
    monkeypatch.setattr(main, "RunService", FakeRunService)
    monkeypatch.setattr(main, "get_path_config", lambda: PathConfig(root=tmp_path))

    result = runner.invoke(main.app, ["pipeline-demo"])

    assert result.exit_code == 0
    request = captured["request"]
    assert request.experiment_name == "advio-offline-advio-15-vista"
    assert request.mode is main.PipelineMode.OFFLINE
    assert request.slam.method is main.MethodId.VISTA
    assert request.source.sequence_id == "advio-15"
    assert captured["source"] == "streaming-source"
    assert captured["source_args"]["sequence_id"] == 15


def test_runtime_dependencies_include_pyyaml() -> None:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]

    assert any(dependency.lower().startswith("pyyaml") for dependency in dependencies)
