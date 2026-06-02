"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from prml_vslam.eval.contracts import MetricStats
from prml_vslam.main import Record3DStreamConfig, _apply_dotted_overrides_to_run_config, app
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import build_run_config
from prml_vslam.pipeline.contracts.provenance import RunSummary, StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources.config import VideoSourceConfig
from prml_vslam.utils import PathConfig
from prml_vslam.utils.serialization import write_json

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


def test_export_import_run_commands_round_trip_bundle(tmp_path: Path) -> None:
    artifact_root = _write_cli_run(tmp_path / "source-artifacts" / "demo-run" / "vista")
    bundle_path = tmp_path / "demo-run.prmlrun.tar.gz"
    output_dir = tmp_path / "imported-artifacts"

    export_result = runner.invoke(app, ["export-run", str(artifact_root), "--output", str(bundle_path)])
    import_result = runner.invoke(app, ["import-run", str(bundle_path), "--output-dir", str(output_dir)])

    assert export_result.exit_code == 0
    assert bundle_path.is_file()
    assert "demo-run" in export_result.stdout
    assert import_result.exit_code == 0
    assert (output_dir / "demo-run" / "vista" / "summary" / "run_summary.json").is_file()


def test_import_run_command_collision_policies(tmp_path: Path) -> None:
    artifact_root = _write_cli_run(tmp_path / "source-artifacts" / "demo-run" / "vista")
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
    assert (output_dir / "demo-run" / "vista-imported-1").is_dir()
    assert overwrite_result.exit_code == 0
    assert (output_dir / "demo-run" / "vista").is_dir()


def test_eval_trajectory_command_uses_aligned_advio_baseline_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = tmp_path / "demo-run"
    estimate_path = artifact_root / "slam" / "trajectory.tum"
    reference_path = artifact_root / "benchmark" / "arcore_aligned_to_gt.tum"
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
            return SimpleNamespace(
                path=artifact_root / "evaluation" / "trajectory_metrics.json",
                stats=MetricStats(rmse=0.0, mean=0.0, median=0.0, std=0.0, min=0.0, max=0.0, sse=0.0),
            )

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path, artifacts_dir=tmp_path))
    monkeypatch.setattr("prml_vslam.eval.services.TrajectoryEvaluationService", FakeTrajectoryEvaluationService)

    result = runner.invoke(app, ["eval-trajectory", str(artifact_root), "--baseline", "arcore", "--sequence-id", "seq"])

    assert result.exit_code == 0
    assert captured["reference_path"] == reference_path


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
