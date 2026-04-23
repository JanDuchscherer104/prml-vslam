"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prml_vslam.main import Record3DStreamConfig, _apply_dotted_overrides_to_run_config, app
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.finalization import write_json
from prml_vslam.pipeline.stages.slam.config import MethodId
from prml_vslam.pipeline.stages.source.config import VideoSourceConfig

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


def test_dotted_run_config_overrides_parse_json_and_deep_merge(tmp_path: Path) -> None:
    config = build_run_config(
        experiment_name="cli-overrides",
        output_dir=tmp_path,
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.MOCK,
    )

    updated = _apply_dotted_overrides_to_run_config(
        config,
        [
            "--stages.slam.backend.max_frames",
            "100",
            "--stages.slam.outputs",
            '{"emit_dense_points": false}',
        ],
    )

    assert updated.stages.slam.backend.max_frames == 100
    assert updated.stages.slam.outputs.emit_dense_points is False
    assert updated.stages.slam.outputs.emit_sparse_points is True


def test_export_import_run_commands_round_trip_bundle(tmp_path: Path) -> None:
    artifact_root = _write_cli_run(tmp_path / "source-artifacts" / "demo-run" / "mock")
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"
    output_dir = tmp_path / "imported-artifacts"

    export_result = runner.invoke(app, ["export-run", str(artifact_root), "--output", str(bundle_path)])
    import_result = runner.invoke(app, ["import-run", str(bundle_path), "--output-dir", str(output_dir)])

    assert export_result.exit_code == 0
    assert bundle_path.is_file()
    assert "demo-run" in export_result.stdout
    assert import_result.exit_code == 0
    assert (output_dir / "demo-run" / "mock" / "summary" / "run_summary.json").is_file()


def test_import_run_command_collision_policies(tmp_path: Path) -> None:
    artifact_root = _write_cli_run(tmp_path / "source-artifacts" / "demo-run" / "mock")
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"
    output_dir = tmp_path / "imported-artifacts"
    runner.invoke(app, ["export-run", str(artifact_root), "--output", str(bundle_path)])
    runner.invoke(app, ["import-run", str(bundle_path), "--output-dir", str(output_dir)])

    fail_result = runner.invoke(app, ["import-run", str(bundle_path), "--output-dir", str(output_dir)])
    rename_result = runner.invoke(
        app,
        ["import-run", str(bundle_path), "--output-dir", str(output_dir), "--on-collision", "rename"],
    )
    overwrite_result = runner.invoke(
        app,
        ["import-run", str(bundle_path), "--output-dir", str(output_dir), "--on-collision", "overwrite"],
    )

    assert fail_result.exit_code == 1
    assert "already exists" in fail_result.stdout
    assert rename_result.exit_code == 0
    assert (output_dir / "demo-run" / "mock-imported-1").is_dir()
    assert overwrite_result.exit_code == 0
    assert (output_dir / "demo-run" / "mock").is_dir()


def _write_cli_run(artifact_root: Path) -> Path:
    write_json(
        artifact_root / "summary" / "run_summary.json",
        RunSummary(
            run_id="demo-run",
            artifact_root=artifact_root,
            stage_status={StageKey.SOURCE: StageStatus.COMPLETED},
        ),
    )
    return artifact_root.resolve()
