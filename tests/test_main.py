"""Focused CLI tests for ADVIO dataset commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prml_vslam import main
from prml_vslam.datasets import AdvioCatalog, AdvioDatasetService, AdvioSceneMetadata
from prml_vslam.datasets.advio import (
    AdvioDownloadPreset,
    AdvioDownloadRequest,
    AdvioDownloadResult,
    AdvioEnvironment,
    AdvioPeopleLevel,
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


def test_advio_summary_command_prints_catalog_and_local_stats(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(main, "get_path_config", lambda: PathConfig(root=tmp_path))

    result = runner.invoke(main.app, ["advio", "summary"])

    assert result.exit_code == 0
    assert "total_scene_count" in result.stdout
    assert "ADVIO" in result.stdout


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
