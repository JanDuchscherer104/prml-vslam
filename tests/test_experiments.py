"""Experiment scaffold tests."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest
from typer.testing import CliRunner

from prml_vslam.experiments.config import ExperimentConfig, ExperimentItem, load_experiment_config
from prml_vslam.experiments.contracts import ExperimentReport
from prml_vslam.experiments.execution import expand_experiment_items, run_experiment
from prml_vslam.experiments.reporting import collect_run_dataframes, write_experiment_report
from prml_vslam.experiments.validation import validate_run_artifacts
from prml_vslam.experiments.wandb_logging import log_run_to_wandb
from prml_vslam.methods.stage.backend_config import MethodId
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.sources.config import VideoSourceConfig
from prml_vslam.utils import PathConfig, RunArtifactPaths

runner = CliRunner()


def test_experiment_config_loads_relative_run_config_paths(tmp_path: Path) -> None:
    run_config_path = tmp_path / "run.toml"
    _run_config(tmp_path).save_toml(run_config_path)
    experiment_path = tmp_path / "experiment.toml"
    experiment_path.write_text(
        """
name = "offline-smoke"
output_dir = "experiment-artifacts"

[[items]]
id = "vista-demo"
run_config_path = "run.toml"
dataset_id = "video"
sequence_id = "demo"
method_id = "vista"
""",
        encoding="utf-8",
    )

    config = load_experiment_config(experiment_path, path_config=PathConfig(root=tmp_path))

    assert config.items[0].run_config_path == run_config_path.resolve()


def test_experiment_config_rejects_empty_and_duplicate_items(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one item"):
        ExperimentConfig(name="empty")

    item = ExperimentItem(id="same", run_config=_run_config(tmp_path))
    with pytest.raises(ValueError, match="Duplicate"):
        ExperimentConfig(name="dupes", items=[item, item])


def test_expand_experiment_items_applies_overrides_and_enforces_offline(tmp_path: Path) -> None:
    config = ExperimentConfig(
        name="expansion",
        items=[
            ExperimentItem(
                id="vista",
                run_config=_run_config(tmp_path),
                overrides={"stages": {"slam": {"backend": {"max_frames": 3}}}},
            )
        ],
    )

    specs = expand_experiment_items(config, path_config=PathConfig(root=tmp_path))

    assert specs[0].method_id == "vista"
    assert specs[0].run_config["stages"]["slam"]["backend"]["max_frames"] == 3

    streaming_payload = _run_config(tmp_path).model_dump_jsonable()
    streaming_payload["mode"] = "streaming"
    streaming = RunConfig.model_validate(streaming_payload)
    with pytest.raises(ValueError, match="offline mode"):
        expand_experiment_items(
            ExperimentConfig(name="streaming", items=[ExperimentItem(id="bad", run_config=streaming)]),
            path_config=PathConfig(root=tmp_path),
        )


def test_validate_run_artifacts_passes_on_expected_fake_tree(tmp_path: Path) -> None:
    run_config = _run_config(tmp_path, trajectory_eval=True, trajectory_alignment=True, cloud_alignment=True)
    spec = expand_experiment_items(
        ExperimentConfig(name="validation", items=[ExperimentItem(id="vista", run_config=run_config)]),
        path_config=PathConfig(root=tmp_path),
    )[0]
    _write_artifacts(spec.artifact_root, run_config=run_config)

    results = validate_run_artifacts(
        spec=spec,
        run_config=run_config,
        snapshot=RunSnapshot(run_id=spec.run_id, state=RunState.COMPLETED),
        allow_failure=False,
    )

    assert results
    assert all(result.passed for result in results)


def test_validate_run_artifacts_fails_on_missing_trajectory(tmp_path: Path) -> None:
    run_config = _run_config(tmp_path)
    spec = expand_experiment_items(
        ExperimentConfig(name="validation", items=[ExperimentItem(id="vista", run_config=run_config)]),
        path_config=PathConfig(root=tmp_path),
    )[0]
    spec.artifact_root.mkdir(parents=True)

    results = validate_run_artifacts(
        spec=spec,
        run_config=run_config,
        snapshot=RunSnapshot(run_id=spec.run_id, state=RunState.COMPLETED),
        allow_failure=False,
    )

    assert any(result.check_name == "slam_trajectory_exists" and not result.passed for result in results)


def test_validate_run_artifacts_fails_on_missing_requested_metrics(tmp_path: Path) -> None:
    run_config = _run_config(tmp_path, trajectory_eval=True)
    spec = expand_experiment_items(
        ExperimentConfig(name="validation", items=[ExperimentItem(id="vista", run_config=run_config)]),
        path_config=PathConfig(root=tmp_path),
    )[0]
    _write_artifacts(spec.artifact_root, run_config=_run_config(tmp_path))

    results = validate_run_artifacts(
        spec=spec,
        run_config=run_config,
        snapshot=RunSnapshot(run_id=spec.run_id, state=RunState.COMPLETED),
        allow_failure=False,
    )

    assert any(result.check_name == "trajectory_metrics_parseable" and not result.passed for result in results)


def test_run_experiment_writes_report_and_tidy_tables(tmp_path: Path) -> None:
    config = ExperimentConfig(
        name="experiment",
        output_dir=Path("experiment-output"),
        items=[
            ExperimentItem(
                id="vista",
                run_config=_run_config(tmp_path, trajectory_eval=True, trajectory_alignment=True, cloud_alignment=True),
            )
        ],
    )

    report = run_experiment(
        config,
        path_config=PathConfig(root=tmp_path),
        run_service_factory=lambda path_config: _FakeRunService(path_config),
    )
    frames = collect_run_dataframes(report)

    assert report.success
    assert report.report_json_path is not None and report.report_json_path.is_file()
    assert report.metrics_parquet_path is not None and report.metrics_parquet_path.is_file()
    assert {"metrics", "validation", "artifacts"} == set(frames)
    assert "ape_translation_rmse" in set(frames["metrics"]["metric_name"])
    assert "slam_trajectory_exists" in set(frames["validation"]["check_name"])


def test_plan_experiment_config_command_prints_specs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from prml_vslam.main import app

    experiment_path = _write_experiment_config(tmp_path)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path))

    result = runner.invoke(app, ["plan-experiment-config", str(experiment_path)])

    assert result.exit_code == 0
    assert "vista-demo" in result.stdout
    assert "artifact_root" in result.stdout


def test_run_experiment_config_command_prints_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from prml_vslam.main import app

    experiment_path = _write_experiment_config(tmp_path)
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: PathConfig(root=tmp_path))
    monkeypatch.setattr(
        "prml_vslam.main.run_experiment",
        lambda experiment_config, path_config: ExperimentReport(
            experiment_id=experiment_config.name,
            started_at=datetime.now().astimezone(),
            completed_at=datetime.now().astimezone(),
        ),
    )

    result = runner.invoke(app, ["run-experiment-config", str(experiment_path)])

    assert result.exit_code == 0
    assert "offline-smoke" in result.stdout


def test_report_serialization_handles_empty_tables(tmp_path: Path) -> None:
    config = ExperimentConfig(name="empty-report", items=[ExperimentItem(id="vista", run_config=_run_config(tmp_path))])
    report = run_experiment(
        config,
        path_config=PathConfig(root=tmp_path),
        run_service_factory=lambda path_config: _FakeRunService(path_config),
    )

    updated = write_experiment_report(report, output_dir=tmp_path / "manual-report")

    assert updated.report_json_path is not None and updated.report_json_path.is_file()
    assert updated.metrics_csv_path is not None and updated.metrics_csv_path.is_file()


def test_wandb_disabled_mode_is_noop(tmp_path: Path) -> None:
    config = ExperimentConfig(name="wandb-off", items=[ExperimentItem(id="vista", run_config=_run_config(tmp_path))])
    report = run_experiment(
        config,
        path_config=PathConfig(root=tmp_path),
        run_service_factory=lambda path_config: _FakeRunService(path_config),
    )

    log_run_to_wandb(config=config, result=report.results[0])


def test_wandb_mocked_mode_logs_metrics(tmp_path: Path) -> None:
    config = ExperimentConfig(
        name="wandb-on",
        wandb={"enabled": True, "project": "prml-vslam-test", "mode": "offline"},
        items=[ExperimentItem(id="vista", run_config=_run_config(tmp_path, trajectory_eval=True))],
    )
    disabled_config = config.model_copy(update={"wandb": config.wandb.model_copy(update={"enabled": False})})
    report = run_experiment(
        disabled_config,
        path_config=PathConfig(root=tmp_path),
        run_service_factory=lambda path_config: _FakeRunService(path_config),
    )
    wandb = _FakeWandbModule("wandb")

    log_run_to_wandb(config=config, result=report.results[0], wandb_module=wandb)

    assert wandb.runs[0].logged
    assert wandb.runs[0].summary["terminal_state"] == "completed"


class _FakeRunService:
    def __init__(self, path_config: PathConfig) -> None:
        self.path_config = path_config
        self._snapshot = RunSnapshot()

    def start_run(self, *, run_config: RunConfig, runtime_source=None) -> None:
        plan = run_config.compile_plan(self.path_config)
        _write_artifacts(plan.artifact_root, run_config=run_config)
        self._snapshot = RunSnapshot(run_id=plan.run_id, state=RunState.COMPLETED, plan=plan)

    def snapshot(self) -> RunSnapshot:
        return self._snapshot

    def stop_run(self) -> None:
        self._snapshot = self._snapshot.model_copy(update={"state": RunState.STOPPED})

    def shutdown(self, *, preserve_local_head: bool = False) -> None:
        return None


class _FakeWandbRun:
    def __init__(self) -> None:
        self.summary = {}
        self.logged: list[dict[str, float | int | bool]] = []

    def log(self, payload: dict[str, float | int | bool]) -> None:
        self.logged.append(payload)

    def finish(self) -> None:
        return None


class _FakeWandbModule(ModuleType):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.runs: list[_FakeWandbRun] = []

    def init(self, **kwargs) -> _FakeWandbRun:
        run = _FakeWandbRun()
        run.summary["init_kwargs"] = kwargs
        self.runs.append(run)
        return run


def _run_config(
    tmp_path: Path,
    *,
    trajectory_eval: bool = False,
    trajectory_alignment: bool = False,
    cloud_alignment: bool = False,
) -> RunConfig:
    return build_run_config(
        experiment_name="vista experiment",
        output_dir=Path("artifacts"),
        source_backend=VideoSourceConfig(video_path=Path("captures/demo.mp4")),
        method=MethodId.VISTA,
        trajectory_eval_enabled=trajectory_eval,
        trajectory_alignment_enabled=trajectory_alignment,
        cloud_alignment_enabled=cloud_alignment,
        export_viewer_rrd=True,
        ray_log_to_driver=False,
    )


def _write_experiment_config(tmp_path: Path) -> Path:
    run_config_path = tmp_path / "run.toml"
    _run_config(tmp_path).save_toml(run_config_path)
    experiment_path = tmp_path / "experiment.toml"
    experiment_path.write_text(
        """
name = "offline-smoke"
output_dir = "experiment-artifacts"

[[items]]
id = "vista-demo"
run_config_path = "run.toml"
dataset_id = "video"
sequence_id = "demo"
method_id = "vista"
""",
        encoding="utf-8",
    )
    return experiment_path


def _write_artifacts(artifact_root: Path, *, run_config: RunConfig) -> None:
    paths = RunArtifactPaths.build(artifact_root)
    _write_text(paths.trajectory_path, "0 0 0 0 0 0 0 1\n")
    _write_text(paths.point_cloud_path, "ply\nformat ascii 1.0\nend_header\n")
    _write_text(paths.viewer_rrd_path, "rrd")
    if run_config.stages.align_trajectory.enabled:
        _write_json(
            paths.artifact_root / "evaluation" / "trajectory_alignment.json",
            {"rms_error_m": 0.1, "scale": 1.0, "matched_pairs": 10},
        )
        _write_text(paths.artifact_root / "evaluation" / "trajectory_sim3_aligned.tum", "0 0 0 0 0 0 0 1\n")
    if run_config.stages.evaluate_trajectory.enabled:
        _write_json(
            paths.trajectory_metrics_path,
            {
                "matched_pairs": 10,
                "stats": {"rmse": 0.1, "mean": 0.1, "median": 0.1, "std": 0.0, "min": 0.1, "max": 0.1, "sse": 0.1},
            },
        )
    if run_config.stages.align_cloud.enabled:
        _write_json(
            paths.artifact_root / "evaluation" / "cloud_alignment.json",
            {"fitness": 0.9, "inlier_rmse_m": 0.02, "max_correspondence_distance_m": 0.1},
        )
    _write_json(
        paths.stage_manifests_path,
        [
            {
                "stage_id": StageKey.SLAM.value,
                "config_hash": "slam-hash",
                "input_fingerprint": "slam-input",
                "output_paths": {
                    "trajectory_tum": paths.trajectory_path.as_posix(),
                    "dense_points_ply": paths.point_cloud_path.as_posix(),
                },
                "status": "completed",
            }
        ],
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
