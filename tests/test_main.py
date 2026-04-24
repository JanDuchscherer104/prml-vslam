"""Minimal CLI-facing smoke tests for the refactored pipeline module."""

from __future__ import annotations

import io
import logging
import re
import signal
import subprocess
import uuid
from contextlib import contextmanager, redirect_stdout
from pathlib import Path

import click
import pytest
import typer

from prml_vslam.datasets.advio import AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from prml_vslam.main import (
    _build_rerun_viewer_command,
    _find_rerun_viewer_processes,
    _forward_rerun_viewer_stdout,
    _launch_rerun_viewer,
    _print_pipeline_demo_snapshot,
    _ProcessInfo,
    _rerun_viewer_process_group_ids,
    _RerunViewerProcess,
    _shutdown_rerun_viewer,
    _wait_for_rerun_viewer_close,
    kill_rerun,
    pipeline_demo_console,
    plan_run,
    run_config,
)
from prml_vslam.methods.stage.config import MethodId, VistaSlamBackendConfig
from prml_vslam.pipeline import PipelineMode
from prml_vslam.pipeline.config import RunConfig, build_run_config
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.demo import (
    build_advio_demo_run_config,
    build_runtime_source_from_run_config,
    load_run_config_toml,
)
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.sources.config import AdvioSourceConfig
from prml_vslam.utils import PathConfig
from tests.pipeline_testing_support import FakeStreamingSource


@contextmanager
def _capture_logger(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, logger_name: str):
    monkeypatch.setattr("prml_vslam.utils.console.Console._logging_configured", True)
    logger = logging.getLogger(logger_name)
    old_handlers = list(logger.handlers)
    old_level = logger.level
    old_propagate = logger.propagate
    logger.handlers = [caplog.handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    caplog.clear()
    try:
        yield logger
    finally:
        logger.handlers = old_handlers
        logger.setLevel(old_level)
        logger.propagate = old_propagate


def _advio_source_payload(sequence_id: str = "advio-01") -> dict[str, object]:
    return {
        "source_id": "advio",
        "sequence_id": sequence_id,
        "dataset_serving": {
            "pose_source": "ground_truth",
            "pose_frame_mode": "provider_world",
        },
    }


def _advio_run_config(
    *,
    output_dir: Path,
    mode: PipelineMode = PipelineMode.STREAMING,
    connect_live_viewer: bool = False,
    local_head_lifecycle: str = "ephemeral",
    viewer_blueprint_path: str | None = None,
    max_frames: int | None = None,
) -> RunConfig:
    return RunConfig.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": mode.value,
            "output_dir": str(output_dir),
            "ray_local_head_lifecycle": local_head_lifecycle,
            "stages": {
                "source": {"backend": _advio_source_payload()},
                "slam": {"backend": {"method_id": "vista", "max_frames": max_frames}},
                "summary": {"enabled": True},
            },
            "visualization": {
                "connect_live_viewer": connect_live_viewer,
                **({} if viewer_blueprint_path is None else {"viewer_blueprint_path": viewer_blueprint_path}),
            },
        }
    )


def _run_config_command(config_path: Path) -> None:
    ctx = typer.Context(
        click.Command("run-config"),
        allow_extra_args=True,
        ignore_unknown_options=True,
    )
    run_config(ctx, config_path)


def test_load_run_config_toml_accepts_target_config(tmp_path: Path) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    config_path = tmp_path / "target-compatible.toml"
    config_path.write_text(
        """
experiment_name = "target-compatible"
mode = "offline"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.source.backend]
source_id = "video"
video_path = "captures/demo.mp4"

[stages.slam]
enabled = true

[stages.slam.backend]
method_id = "vista"

[stages.summary]
enabled = true
""".strip()
    )

    run_config = load_run_config_toml(path_config=path_config, config_path=config_path)

    assert run_config.experiment_name == "target-compatible"
    assert run_config.stages.slam.backend.method_id is MethodId.VISTA


def test_run_config_planning_rejects_missing_target_backends(tmp_path: Path) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    config_path = tmp_path / "target-only.toml"
    config_path.write_text(
        """
experiment_name = "target-only"
mode = "offline"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.slam]
enabled = true

[stages.summary]
enabled = true
""".strip()
    )

    run_config = load_run_config_toml(path_config=path_config, config_path=config_path)

    with pytest.raises(ValueError, match=r"RunConfig planning requires `\[stages\.source\.backend\]`"):
        run_config.compile_plan(path_config)


def test_print_pipeline_demo_snapshot_accepts_projected_snapshot(tmp_path: Path) -> None:
    snapshot = RunSnapshot(
        run_id="demo",
        state=RunState.COMPLETED,
        artifacts={},
        error_message="",
    )

    _print_pipeline_demo_snapshot(snapshot)

    assert snapshot.state is RunState.COMPLETED


def test_wait_for_pipeline_terminal_snapshot_uses_pipeline_demo_namespace(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    from prml_vslam.main import _wait_for_pipeline_terminal_snapshot

    snapshot = RunSnapshot(run_id="demo", state=RunState.COMPLETED)

    class FakeRunService:
        def snapshot(self) -> RunSnapshot:
            return snapshot

    with _capture_logger(caplog, monkeypatch, pipeline_demo_console.logger.name):
        result = _wait_for_pipeline_terminal_snapshot(FakeRunService(), poll_interval_seconds=0.01)

    assert result is snapshot
    assert caplog.records[0].name == "prml_vslam.pipeline.demo"
    assert "Pipeline demo state: completed" in caplog.records[0].message


def test_build_advio_demo_run_config_enables_live_viewer_by_default(tmp_path: Path) -> None:
    request = build_advio_demo_run_config(
        path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
        sequence_id="advio-01",
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
    )

    assert request.visualization.connect_live_viewer is True
    assert request.stages.source.backend.dataset_serving == AdvioServingConfig(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
    )
    assert request.stages.source.backend.respect_video_rotation is False


def test_build_advio_demo_run_config_keeps_streaming_replay_controls(tmp_path: Path) -> None:
    request = build_advio_demo_run_config(
        path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
        sequence_id="advio-01",
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
        pose_source=AdvioPoseSource.ARCORE,
        respect_video_rotation=True,
    )

    assert request.stages.source.backend.dataset_serving == AdvioServingConfig(
        pose_source=AdvioPoseSource.ARCORE,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
    )
    assert request.stages.source.backend.respect_video_rotation is True


def test_plan_run_defaults_to_live_viewer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_compile_plan(self: RunConfig, path_config: PathConfig | None = None, *, fail_on_unavailable: bool = False):
        del path_config, fail_on_unavailable
        captured["connect_live_viewer"] = self.visualization.connect_live_viewer
        return type("Plan", (), {"model_dump": lambda self, mode="json": {"ok": True}})()

    monkeypatch.setattr(RunConfig, "compile_plan", fake_compile_plan)
    monkeypatch.setattr("prml_vslam.main.console.plog", lambda payload: captured.setdefault("payload", payload))

    plan_run(
        experiment_name="demo",
        video_path=tmp_path / "demo.mp4",
    )

    assert captured["connect_live_viewer"] is True


def test_run_config_supports_streaming_requests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir)
    runtime_source = object()
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            captured["run_config"] = run_config
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: runtime_source)
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert isinstance(captured["run_config"], RunConfig)
    assert captured["run_config"].model_dump(mode="json") == run_cfg.model_dump(mode="json")
    assert captured["runtime_source"] is runtime_source
    assert captured["preserve_local_head"] is False


def test_run_config_persists_timestamped_command_log(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir)

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            del run_config, runtime_source
            print("start payload processed=73 fps=13.29")

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            print(f"shutdown preserve={preserve_local_head}")

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.COMPLETED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: print("snapshot payload"))

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    log_files = list(path_config.resolve_run_logs_dir("demo-streaming").glob("*.log"))
    assert len(log_files) == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}_demo-streaming\.log", log_files[0].name)
    lines = log_files[0].read_text(encoding="utf-8").splitlines()
    assert lines
    assert all(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z ", line) for line in lines)
    assert any("Persisting run-config log" in line for line in lines)
    assert any("start payload processed=73 fps=13.29" in line for line in lines)
    assert any("snapshot payload" in line for line in lines)


def test_run_config_persists_log_after_loaded_config_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir)

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr(
        "prml_vslam.main.build_runtime_source_from_run_config",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("runtime source boom")),
    )

    with pytest.raises(typer.Exit) as exc_info:
        _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert exc_info.value.exit_code == 1
    log_files = list(path_config.resolve_run_logs_dir("demo-streaming").glob("*.log"))
    assert len(log_files) == 1
    content = log_files[0].read_text(encoding="utf-8")
    assert "Persisting run-config log" in content
    assert "runtime source boom" in content


def test_run_config_vista_full_toml_smoke_with_capped_vista_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path_config = PathConfig(root=repo_root, artifacts_dir=tmp_path / ".artifacts", logs_dir=tmp_path / ".logs")
    captured: dict[str, object] = {}

    class FakeBackend:
        def submit_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> str:
            captured["run_config"] = run_config
            captured["runtime_source"] = runtime_source
            return run_config.experiment_name

        def stop_run(self, run_id: str) -> None:
            captured["stopped_run_id"] = run_id

        def get_snapshot(self, run_id: str) -> RunSnapshot:
            return RunSnapshot(run_id=run_id, state=RunState.COMPLETED)

        def get_events(
            self,
            run_id: str,
            *,
            after_event_id: str | None = None,
            limit: int = 200,
        ) -> list[RunEvent]:
            del run_id, after_event_id, limit
            return []

        def read_payload(self, run_id: str, ref: TransientPayloadRef | None):
            del run_id, ref
            return None

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    class CapturingRunService(RunService):
        def __init__(self, *, path_config: PathConfig) -> None:
            super().__init__(path_config=path_config, backend=FakeBackend())
            captured["path_config"] = path_config

    config_path = tmp_path / "target-run-config.toml"
    config_path.write_text(
        """
experiment_name = "target-smoke"
mode = "streaming"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.source.backend]
source_id = "advio"
sequence_id = "advio-01"

[stages.source.backend.dataset_serving]
pose_source = "ground_truth"
pose_frame_mode = "provider_world"

[stages.slam]
enabled = true

[stages.slam.backend]
method_id = "vista"

[stages.summary]
enabled = true
""".strip(),
        encoding="utf-8",
    )

    def load_and_patch_run_config(*, path_config: PathConfig, config_path: Path) -> RunConfig:
        run_config = load_run_config_toml(path_config=path_config, config_path=config_path)
        patched_stages = run_config.stages.model_copy(
            update={"slam": run_config.stages.slam.model_copy(update={"backend": VistaSlamBackendConfig(max_frames=3)})}
        )
        return run_config.model_copy(
            update={
                "output_dir": path_config.artifacts_dir,
                "stages": patched_stages,
                "visualization": run_config.visualization.model_copy(
                    update={"connect_live_viewer": False, "export_viewer_rrd": False}
                ),
            }
        )

    monkeypatch.setenv("PRML_VSLAM_RAY_NAMESPACE", f"pytest-{uuid.uuid4().hex}")
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", load_and_patch_run_config)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: FakeStreamingSource())
    monkeypatch.setattr("prml_vslam.main.RunService", CapturingRunService)
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    _run_config_command(config_path)

    assert captured["path_config"] == path_config
    assert isinstance(captured["runtime_source"], FakeStreamingSource)
    run_cfg = captured["run_config"]
    assert isinstance(run_cfg, RunConfig)
    assert run_cfg.stages.slam.backend is not None
    assert run_cfg.stages.slam.backend.method_id is MethodId.VISTA
    assert run_cfg.visualization.connect_live_viewer is False
    assert run_cfg.visualization.export_viewer_rrd is False
    assert captured["shutdown"] is False


def test_run_config_preserves_local_head_for_reusable_completed_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, local_head_lifecycle="reusable")
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            captured["run_config"] = run_config
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.COMPLETED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert captured["preserve_local_head"] is True


def test_run_config_does_not_preserve_local_head_for_reusable_failed_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, local_head_lifecycle="reusable")
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            captured["run_config"] = run_config
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.FAILED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    with pytest.raises(typer.Exit):
        _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert captured["preserve_local_head"] is False


def test_build_rerun_viewer_command_uses_blueprint_when_configured(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(
        output_dir=tmp_path / ".artifacts",
        connect_live_viewer=True,
        viewer_blueprint_path=".configs/visualization/demo_blueprint.rbl",
    )

    command = _build_rerun_viewer_command(run_config=run_cfg, path_config=path_config)

    assert command == [
        "uv",
        "run",
        "--extra",
        "vista",
        "rerun",
        (tmp_path / ".configs/visualization/demo_blueprint.rbl").resolve().as_posix(),
        "--serve-web",
    ]


def test_build_rerun_viewer_command_omits_blueprint_when_unset(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(output_dir=tmp_path / ".artifacts", connect_live_viewer=True)

    command = _build_rerun_viewer_command(run_config=run_cfg, path_config=path_config)

    assert command == ["uv", "run", "--extra", "vista", "rerun", "--serve-web"]


def test_build_rerun_viewer_command_resolves_vista_full_blueprint_path(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path_config = PathConfig(root=repo_root)
    config_path = tmp_path / "target-blueprint-test.toml"
    config_path.write_text(
        """
experiment_name = "target-blueprint"
mode = "offline"
output_dir = ".artifacts"

[stages.source]
enabled = true

[stages.source.backend]
source_id = "video"
video_path = "captures/demo.mp4"

[stages.slam]
enabled = true

[stages.slam.backend]
method_id = "vista"

[stages.summary]
enabled = true

[visualization]
viewer_blueprint_path = ".configs/visualization/vista_blueprint.rbl"
""".strip(),
        encoding="utf-8",
    )
    run_cfg = load_run_config_toml(path_config=path_config, config_path=config_path)

    command = _build_rerun_viewer_command(run_config=run_cfg, path_config=path_config)

    assert command[-2] == (repo_root / ".configs/visualization/vista_blueprint.rbl").resolve().as_posix()


def test_forward_rerun_viewer_stdout_prefixes_child_output() -> None:
    source = io.StringIO("viewer ready\nsecond line\n")
    target = io.StringIO()

    _forward_rerun_viewer_stdout(stream=source, target=target)

    assert target.getvalue() == "[rerun] viewer ready\n[rerun] second line\n"


def test_forward_rerun_viewer_stdout_uses_current_stdout_by_default() -> None:
    source = io.StringIO("viewer ready\n")
    target = io.StringIO()

    with redirect_stdout(target):
        _forward_rerun_viewer_stdout(stream=source)

    assert target.getvalue() == "[rerun] viewer ready\n"


def test_launch_rerun_viewer_is_noop_when_live_viewer_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(output_dir=tmp_path / ".artifacts", connect_live_viewer=False)

    monkeypatch.setattr(
        "prml_vslam.main.subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("viewer subprocess must not be launched")),
    )

    assert _launch_rerun_viewer(run_config=run_cfg, path_config=path_config) is None


def test_launch_rerun_viewer_uses_pipe_and_merged_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(output_dir=tmp_path / ".artifacts", connect_live_viewer=True)
    captured: dict[str, object] = {}

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("viewer ready\n")
            self.returncode = None

        def poll(self) -> int | None:
            return self.returncode

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr("prml_vslam.main.subprocess.Popen", fake_popen)
    monkeypatch.setattr("prml_vslam.main.time.sleep", lambda _: None)

    viewer = _launch_rerun_viewer(run_config=run_cfg, path_config=path_config)

    assert viewer is not None
    assert captured["command"] == ["uv", "run", "--extra", "vista", "rerun", "--serve-web"]
    assert captured["kwargs"]["stdout"] is subprocess.PIPE
    assert captured["kwargs"]["stderr"] is subprocess.STDOUT
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["bufsize"] == 1
    assert captured["kwargs"]["cwd"] == path_config.root


def test_launch_rerun_viewer_warns_and_returns_none_on_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(output_dir=tmp_path / ".artifacts", connect_live_viewer=True)
    warnings: list[str] = []

    monkeypatch.setattr(
        "prml_vslam.main.subprocess.Popen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom"))
    )
    monkeypatch.setattr("prml_vslam.main.console.warning", lambda message, *args: warnings.append(message % args))

    viewer = _launch_rerun_viewer(run_config=run_cfg, path_config=path_config)

    assert viewer is None
    assert warnings == ["Failed to launch the Rerun viewer subprocess: boom"]


def test_launch_rerun_viewer_warns_and_returns_none_on_early_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=tmp_path)
    run_cfg = _advio_run_config(output_dir=tmp_path / ".artifacts", connect_live_viewer=True)
    warnings: list[str] = []

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = io.StringIO("boom\n")
            self.returncode = 2

        def poll(self) -> int | None:
            return self.returncode

    monkeypatch.setattr("prml_vslam.main.subprocess.Popen", lambda *args, **kwargs: FakeProcess())
    monkeypatch.setattr("prml_vslam.main.time.sleep", lambda _: None)
    monkeypatch.setattr("prml_vslam.main.console.warning", lambda message, *args: warnings.append(message % args))

    viewer = _launch_rerun_viewer(run_config=run_cfg, path_config=path_config)

    assert viewer is None
    assert warnings == ["Rerun viewer exited early with code 2; continuing without auto-launched live viewer."]


def test_shutdown_rerun_viewer_terminates_process_and_joins_forwarder() -> None:
    observed: dict[str, object] = {}

    class FakeStdout:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = FakeStdout()

        def poll(self) -> int | None:
            return None

        def terminate(self) -> None:
            observed["terminated"] = True

        def wait(self, timeout: float) -> None:
            observed["wait_timeout"] = timeout

        def kill(self) -> None:
            observed["killed"] = True

    class FakeThread:
        def join(self, timeout: float) -> None:
            observed["join_timeout"] = timeout

    viewer = _RerunViewerProcess(
        process=FakeProcess(),  # type: ignore[arg-type]
        forwarder=FakeThread(),  # type: ignore[arg-type]
    )

    _shutdown_rerun_viewer(viewer)

    assert observed["terminated"] is True
    assert observed["wait_timeout"] == 5.0
    assert observed["join_timeout"] == 1.0
    assert viewer.process.stdout.closed is True


def test_wait_for_rerun_viewer_close_handles_keyboard_interrupt() -> None:
    observed: dict[str, object] = {}

    class FakeProcess:
        def poll(self) -> int | None:
            return None

        def wait(self) -> None:
            observed["waited"] = True
            raise KeyboardInterrupt

    class FakeThread:
        def join(self, timeout: float) -> None:
            del timeout

    viewer = _RerunViewerProcess(
        process=FakeProcess(),  # type: ignore[arg-type]
        forwarder=FakeThread(),  # type: ignore[arg-type]
    )

    _wait_for_rerun_viewer_close(viewer)

    assert observed["waited"] is True


def test_find_rerun_viewer_processes_matches_current_viewer_tree() -> None:
    processes = [
        _ProcessInfo(
            pid=77384,
            ppid=74705,
            pgid=77384,
            stat="Ssl",
            command=(
                "uv run --extra vista rerun "
                "/home/jandu/repos/prml-vslam/.configs/visualization/vista_blueprint.rbl --serve-web"
            ),
        ),
        _ProcessInfo(
            pid=77389,
            ppid=77384,
            pgid=77384,
            stat="S",
            command=(
                "/home/jandu/repos/prml-vslam/.venv/bin/python3 "
                "/home/jandu/repos/prml-vslam/.venv/bin/rerun "
                "/home/jandu/repos/prml-vslam/.configs/visualization/vista_blueprint.rbl --serve-web"
            ),
        ),
        _ProcessInfo(
            pid=77390,
            ppid=77389,
            pgid=77384,
            stat="Sl",
            command=(
                "/home/jandu/repos/prml-vslam/.venv/lib/python3.11/site-packages/rerun_sdk/rerun_cli/rerun "
                "/home/jandu/repos/prml-vslam/.configs/visualization/vista_blueprint.rbl --serve-web"
            ),
        ),
        _ProcessInfo(
            pid=77400,
            ppid=1,
            pgid=77400,
            stat="S",
            command="uv run prml-vslam kill-rerun",
        ),
        _ProcessInfo(pid=77401, ppid=1, pgid=77401, stat="S", command="rerun rrd print recording.rrd"),
    ]

    matches = _find_rerun_viewer_processes(processes)

    assert [process.pid for process in matches] == [77384, 77389, 77390]
    assert _rerun_viewer_process_group_ids(matches) == [77384]


def test_kill_rerun_dry_run_lists_processes_without_signaling(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    processes = [
        _ProcessInfo(
            pid=11,
            ppid=1,
            pgid=10,
            stat="Sl",
            command="uv run --extra vista rerun .configs/visualization/vista_blueprint.rbl --serve-web",
        )
    ]
    monkeypatch.setattr("prml_vslam.main._find_rerun_viewer_processes", lambda: processes)
    monkeypatch.setattr(
        "prml_vslam.main._signal_process_group",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("dry run must not signal")),
    )

    kill_rerun(dry_run=True)

    output = capsys.readouterr().out
    assert "Matched Rerun web viewer processes" in output
    assert "vista_blueprint.rbl" in output


def test_kill_rerun_terminates_matched_process_group(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = [
        _ProcessInfo(pid=11, ppid=1, pgid=10, stat="Ssl", command="uv run --extra vista rerun --serve-web"),
        _ProcessInfo(pid=12, ppid=11, pgid=10, stat="Sl", command="/tmp/.venv/bin/rerun --serve-web"),
    ]
    signals: list[tuple[int, signal.Signals]] = []
    monkeypatch.setattr("prml_vslam.main._find_rerun_viewer_processes", lambda: processes)
    monkeypatch.setattr("prml_vslam.main._signal_process_group", lambda pgid, sig: signals.append((pgid, sig)) or True)
    monkeypatch.setattr("prml_vslam.main._wait_for_rerun_process_groups_to_exit", lambda **kwargs: [])

    kill_rerun()

    assert signals == [(10, signal.SIGTERM)]


def test_kill_rerun_escalates_when_process_group_remains(monkeypatch: pytest.MonkeyPatch) -> None:
    processes = [_ProcessInfo(pid=11, ppid=1, pgid=10, stat="Ssl", command="uv run --extra vista rerun --serve-web")]
    signals: list[tuple[int, signal.Signals]] = []
    wait_results = [[10], []]
    monkeypatch.setattr("prml_vslam.main._find_rerun_viewer_processes", lambda: processes)
    monkeypatch.setattr("prml_vslam.main._signal_process_group", lambda pgid, sig: signals.append((pgid, sig)) or True)
    monkeypatch.setattr("prml_vslam.main._wait_for_rerun_process_groups_to_exit", lambda **kwargs: wait_results.pop(0))

    kill_rerun(timeout_seconds=0.1)

    assert signals == [(10, signal.SIGTERM), (10, signal.SIGKILL)]


def test_run_config_continues_when_viewer_launcher_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, connect_live_viewer=True)
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            captured["run_config"] = run_config
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: captured.setdefault("viewer", viewer))
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert isinstance(captured["run_config"], RunConfig)
    assert captured["run_config"].model_dump(mode="json") == run_cfg.model_dump(mode="json")
    assert captured["viewer"] is None


def test_run_config_prints_output_then_waits_for_viewer_after_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    events: list[str] = []
    viewer = _RerunViewerProcess(
        process=object(),  # type: ignore[arg-type]
        forwarder=object(),  # type: ignore[arg-type]
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, connect_live_viewer=True)

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            del run_config, runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            events.append(f"run-shutdown:{preserve_local_head}")

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer",
        lambda current: events.append(f"viewer-shutdown:{current is viewer}"),
    )
    monkeypatch.setattr("prml_vslam.main._wait_for_rerun_viewer_close", lambda current: events.append("viewer-wait"))
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.COMPLETED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: events.append("print"))

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert events == ["run-shutdown:False", "print", "viewer-wait", "viewer-shutdown:True"]


def test_run_config_keeps_failed_run_viewer_open_until_wait_finishes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    events: list[str] = []
    viewer = _RerunViewerProcess(
        process=object(),  # type: ignore[arg-type]
        forwarder=object(),  # type: ignore[arg-type]
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, connect_live_viewer=True)

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            del run_config, runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            events.append(f"run-shutdown:{preserve_local_head}")

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer",
        lambda current: events.append(f"viewer-shutdown:{current is viewer}"),
    )
    monkeypatch.setattr("prml_vslam.main._wait_for_rerun_viewer_close", lambda current: events.append("viewer-wait"))
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.FAILED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: events.append("print"))

    with pytest.raises(typer.Exit) as exc_info:
        _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert exc_info.value.exit_code == 1
    assert events == ["run-shutdown:False", "print", "viewer-wait", "viewer-shutdown:True"]


def test_run_config_ctrl_c_during_post_run_viewer_wait_does_not_stop_finished_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    events: list[str] = []

    class FakeProcess:
        def poll(self) -> int | None:
            return None

        def wait(self) -> None:
            events.append("viewer-wait")
            raise KeyboardInterrupt

    class FakeThread:
        def join(self, timeout: float) -> None:
            del timeout

    viewer = _RerunViewerProcess(
        process=FakeProcess(),  # type: ignore[arg-type]
        forwarder=FakeThread(),  # type: ignore[arg-type]
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, connect_live_viewer=True)

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            del run_config, runtime_source

        def stop_run(self) -> None:
            events.append("stop-run")

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            events.append(f"run-shutdown:{preserve_local_head}")

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer",
        lambda current: events.append(f"viewer-shutdown:{current is viewer}"),
    )
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.COMPLETED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: events.append("print"))

    _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert events == ["run-shutdown:False", "print", "viewer-wait", "viewer-shutdown:True"]


def test_run_config_shuts_down_viewer_after_active_pipeline_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(
        root=Path(__file__).resolve().parents[1],
        artifacts_dir=tmp_path / ".artifacts",
        logs_dir=tmp_path / ".logs",
    )
    captured: dict[str, object] = {}
    viewer = _RerunViewerProcess(
        process=object(),  # type: ignore[arg-type]
        forwarder=object(),  # type: ignore[arg-type]
    )
    run_cfg = _advio_run_config(output_dir=path_config.artifacts_dir, connect_live_viewer=True)

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, run_config: RunConfig, runtime_source: object | None = None) -> None:
            del run_config, runtime_source

        def stop_run(self) -> None:
            captured["stopped"] = True

        def snapshot(self) -> RunSnapshot:
            return RunSnapshot()

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_config_toml", lambda **kwargs: run_cfg)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer", lambda current: captured.setdefault("viewer", current)
    )
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_run_config", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    with pytest.raises(typer.Exit) as exc_info:
        _run_config_command(Path(".configs/pipelines/vista-full.toml"))

    assert exc_info.value.exit_code == 130
    assert captured["stopped"] is True
    assert captured["viewer"] is viewer


def test_build_runtime_source_from_run_config_caps_streaming_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    run_config = build_run_config(
        experiment_name="demo-streaming",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source_backend=AdvioSourceConfig(
            sequence_id="advio-01",
            dataset_serving={
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
            respect_video_rotation=True,
        ),
        method=MethodId.VISTA,
        max_frames=2,
    )

    class FakePacketStream:
        def __init__(self) -> None:
            self.connected = False
            self.index = 0

        def connect(self) -> None:
            self.connected = True

        def disconnect(self) -> None:
            self.connected = False

        def wait_for_packet(self, timeout_seconds: float | None = None) -> object:
            del timeout_seconds
            packet = f"frame-{self.index}"
            self.index += 1
            return packet

    class FakeStreamingSource:
        label = "fake-advio"

        def __init__(self) -> None:
            self.stream = FakePacketStream()

        def prepare_sequence_manifest(self, output_dir: Path) -> object:
            del output_dir
            return object()

        def prepare_benchmark_inputs(self, output_dir: Path) -> object:
            del output_dir
            return object()

        def open_stream(self, *, loop: bool):
            del loop
            return self.stream

    fake_source = FakeStreamingSource()
    captured: dict[str, object] = {}

    def fake_setup_target(self, *, path_config: PathConfig) -> FakeStreamingSource:
        del self
        captured["path_config"] = path_config
        return fake_source

    monkeypatch.setattr("prml_vslam.sources.config.AdvioSourceConfig.setup_target", fake_setup_target)

    capped_source = build_runtime_source_from_run_config(run_config=run_config, path_config=path_config)
    assert capped_source is not None
    assert captured["path_config"] == path_config

    stream = capped_source.open_stream(loop=False)
    stream.connect()
    assert stream.wait_for_packet() == "frame-0"
    assert stream.wait_for_packet() == "frame-1"
    with pytest.raises(EOFError):
        stream.wait_for_packet()
