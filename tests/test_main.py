"""Minimal CLI-facing smoke tests for the refactored pipeline module."""

from __future__ import annotations

import io
import logging
import subprocess
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
import typer

from prml_vslam.datasets.advio import AdvioPoseFrameMode, AdvioPoseSource, AdvioServingConfig
from prml_vslam.main import (
    _build_rerun_viewer_command,
    _forward_rerun_viewer_stdout,
    _launch_rerun_viewer,
    _print_pipeline_demo_snapshot,
    _RerunViewerProcess,
    _shutdown_rerun_viewer,
    pipeline_demo_console,
    plan_run,
    run_config,
)
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.contracts.events import RunEvent
from prml_vslam.pipeline.contracts.handles import ArrayHandle, PreviewHandle
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig, build_backend_spec
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.pipeline.demo import build_advio_demo_request, build_runtime_source_from_request, load_run_request_toml
from prml_vslam.pipeline.run_service import RunService
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


def test_build_advio_demo_request_enables_live_viewer_by_default(tmp_path: Path) -> None:
    request = build_advio_demo_request(
        path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
        sequence_id="advio-01",
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
    )

    assert request.visualization.connect_live_viewer is True
    assert request.source.dataset_serving == AdvioServingConfig(
        pose_source=AdvioPoseSource.GROUND_TRUTH,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
    )
    assert request.source.respect_video_rotation is False


def test_build_advio_demo_request_keeps_streaming_replay_controls(tmp_path: Path) -> None:
    request = build_advio_demo_request(
        path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
        sequence_id="advio-01",
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
        pose_source=AdvioPoseSource.ARCORE,
        respect_video_rotation=True,
    )

    assert request.source.dataset_serving == AdvioServingConfig(
        pose_source=AdvioPoseSource.ARCORE,
        pose_frame_mode=AdvioPoseFrameMode.PROVIDER_WORLD,
    )
    assert request.source.respect_video_rotation is True


def test_plan_run_defaults_to_live_viewer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_build(self: RunRequest, path_config: PathConfig | None = None):
        del path_config
        captured["connect_live_viewer"] = self.visualization.connect_live_viewer
        return type("Plan", (), {"model_dump": lambda self, mode="json": {"ok": True}})()

    monkeypatch.setattr(RunRequest, "build", fake_build)
    monkeypatch.setattr("prml_vslam.main.console.plog", lambda payload: captured.setdefault("payload", payload))

    plan_run(
        experiment_name="demo",
        video_path=tmp_path / "demo.mp4",
    )

    assert captured["connect_live_viewer"] is True


def test_run_config_supports_streaming_requests(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="demo-streaming",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={"dataset_id": "advio", "pose_source": "ground_truth", "pose_frame_mode": "provider_world"},
        ),
        slam=SlamStageConfig(backend={"kind": "mock"}),
    )
    runtime_source = object()
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            captured["request"] = request
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: runtime_source)
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["request"] is request
    assert captured["runtime_source"] is runtime_source
    assert captured["preserve_local_head"] is False


def test_run_config_vista_full_toml_smoke_with_mock_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path_config = PathConfig(root=repo_root, artifacts_dir=tmp_path / ".artifacts")
    captured: dict[str, object] = {}

    class FakeBackend:
        def submit_run(self, *, request: RunRequest, runtime_source: object | None = None) -> str:
            captured["request"] = request
            captured["runtime_source"] = runtime_source
            return request.experiment_name

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

        def read_array(self, run_id: str, handle: ArrayHandle | PreviewHandle | None):
            del run_id, handle
            return None

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    class CapturingRunService(RunService):
        def __init__(self, *, path_config: PathConfig) -> None:
            super().__init__(path_config=path_config, backend=FakeBackend())
            captured["path_config"] = path_config

    def load_and_patch_request(*, path_config: PathConfig, config_path: Path) -> RunRequest:
        request = load_run_request_toml(path_config=path_config, config_path=config_path)
        return request.model_copy(
            update={
                "output_dir": path_config.artifacts_dir,
                "slam": request.slam.model_copy(
                    update={
                        "backend": build_backend_spec(method=MethodId.MOCK, max_frames=3),
                    }
                ),
                "visualization": request.visualization.model_copy(
                    update={"connect_live_viewer": False, "export_viewer_rrd": False}
                ),
            }
        )

    monkeypatch.setenv("PRML_VSLAM_RAY_NAMESPACE", f"pytest-{uuid.uuid4().hex}")
    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", load_and_patch_request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: FakeStreamingSource())
    monkeypatch.setattr("prml_vslam.main.RunService", CapturingRunService)
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["path_config"] == path_config
    assert isinstance(captured["runtime_source"], FakeStreamingSource)
    request = captured["request"]
    assert isinstance(request, RunRequest)
    assert request.slam.backend.kind == "mock"
    assert request.visualization.connect_live_viewer is False
    assert request.visualization.export_viewer_rrd is False
    assert captured["shutdown"] is False


def test_run_config_preserves_local_head_for_reusable_completed_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(path_config.artifacts_dir),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "runtime": {"ray": {"local_head_lifecycle": "reusable"}},
        }
    )
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            captured["request"] = request
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.COMPLETED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["preserve_local_head"] is True


def test_run_config_does_not_preserve_local_head_for_reusable_failed_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(path_config.artifacts_dir),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "runtime": {"ray": {"local_head_lifecycle": "reusable"}},
        }
    )
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            captured["request"] = request
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["preserve_local_head"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: None)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: RunSnapshot(state=RunState.FAILED),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    with pytest.raises(typer.Exit):
        run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["preserve_local_head"] is False


def test_build_rerun_viewer_command_uses_blueprint_when_configured(tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {
                "connect_live_viewer": True,
                "viewer_blueprint_path": ".configs/visualization/demo_blueprint.rbl",
            },
        }
    )

    command = _build_rerun_viewer_command(request=request, path_config=path_config)

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
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )

    command = _build_rerun_viewer_command(request=request, path_config=path_config)

    assert command == ["uv", "run", "--extra", "vista", "rerun", "--serve-web"]


def test_build_rerun_viewer_command_resolves_vista_full_blueprint_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    path_config = PathConfig(root=repo_root)
    request = load_run_request_toml(path_config=path_config, config_path=Path(".configs/pipelines/vista-full.toml"))

    command = _build_rerun_viewer_command(request=request, path_config=path_config)

    assert command[-2] == (repo_root / ".configs/visualization/vista_blueprint.rbl").resolve().as_posix()


def test_forward_rerun_viewer_stdout_prefixes_child_output() -> None:
    source = io.StringIO("viewer ready\nsecond line\n")
    target = io.StringIO()

    _forward_rerun_viewer_stdout(stream=source, target=target)

    assert target.getvalue() == "[rerun] viewer ready\n[rerun] second line\n"


def test_launch_rerun_viewer_is_noop_when_live_viewer_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=tmp_path)
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": False},
        }
    )

    monkeypatch.setattr(
        "prml_vslam.main.subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("viewer subprocess must not be launched")),
    )

    assert _launch_rerun_viewer(request=request, path_config=path_config) is None


def test_launch_rerun_viewer_uses_pipe_and_merged_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path_config = PathConfig(root=tmp_path)
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
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

    viewer = _launch_rerun_viewer(request=request, path_config=path_config)

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
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
    warnings: list[str] = []

    monkeypatch.setattr(
        "prml_vslam.main.subprocess.Popen", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom"))
    )
    monkeypatch.setattr("prml_vslam.main.console.warning", lambda message, *args: warnings.append(message % args))

    viewer = _launch_rerun_viewer(request=request, path_config=path_config)

    assert viewer is None
    assert warnings == ["Failed to launch the Rerun viewer subprocess: boom"]


def test_launch_rerun_viewer_warns_and_returns_none_on_early_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=tmp_path)
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(tmp_path / ".artifacts"),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
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

    viewer = _launch_rerun_viewer(request=request, path_config=path_config)

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


def test_run_config_continues_when_viewer_launcher_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(path_config.artifacts_dir),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
    captured: dict[str, object] = {}

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            captured["path_config"] = path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            captured["request"] = request
            captured["runtime_source"] = runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: None)
    monkeypatch.setattr("prml_vslam.main._shutdown_rerun_viewer", lambda viewer: captured.setdefault("viewer", viewer))
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["request"] is request
    assert captured["viewer"] is None


def test_run_config_shuts_down_viewer_after_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(path_config.artifacts_dir),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
    captured: dict[str, object] = {}
    viewer = _RerunViewerProcess(
        process=object(),  # type: ignore[arg-type]
        forwarder=object(),  # type: ignore[arg-type]
    )

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            del request, runtime_source

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer", lambda current: captured.setdefault("viewer", current)
    )
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["viewer"] is viewer
    assert captured["shutdown"] is False


def test_run_config_shuts_down_viewer_after_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest.model_validate(
        {
            "experiment_name": "demo-streaming",
            "mode": "streaming",
            "output_dir": str(path_config.artifacts_dir),
            "source": {"dataset_id": "advio", "sequence_id": "advio-01"},
            "slam": {"backend": {"kind": "mock"}},
            "visualization": {"connect_live_viewer": True},
        }
    )
    captured: dict[str, object] = {}
    viewer = _RerunViewerProcess(
        process=object(),  # type: ignore[arg-type]
        forwarder=object(),  # type: ignore[arg-type]
    )

    class FakeRunService:
        def __init__(self, *, path_config: PathConfig) -> None:
            del path_config

        def start_run(self, *, request: RunRequest, runtime_source: object | None = None) -> None:
            del request, runtime_source

        def stop_run(self) -> None:
            captured["stopped"] = True

        def snapshot(self) -> RunSnapshot:
            return RunSnapshot()

        def shutdown(self, *, preserve_local_head: bool = False) -> None:
            captured["shutdown"] = preserve_local_head

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main._launch_rerun_viewer", lambda **kwargs: viewer)
    monkeypatch.setattr(
        "prml_vslam.main._shutdown_rerun_viewer", lambda current: captured.setdefault("viewer", current)
    )
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: object())
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr(
        "prml_vslam.main._wait_for_pipeline_terminal_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    with pytest.raises(typer.Exit) as exc_info:
        run_config(Path(".configs/pipelines/vista-full.toml"))

    assert exc_info.value.exit_code == 130
    assert captured["stopped"] is True
    assert captured["viewer"] is viewer


def test_build_runtime_source_from_request_caps_streaming_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="demo-streaming",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(
            dataset_id="advio",
            sequence_id="advio-01",
            dataset_serving={
                "dataset_id": "advio",
                "pose_source": "ground_truth",
                "pose_frame_mode": "provider_world",
            },
            respect_video_rotation=True,
        ),
        slam=SlamStageConfig(backend={"kind": "mock", "max_frames": 2}),
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

    class FakeAdvioService:
        def __init__(self, path_config: PathConfig) -> None:
            del path_config

        def resolve_sequence_id(self, sequence_id: str) -> str:
            return sequence_id

        def build_streaming_source(self, **kwargs: object) -> FakeStreamingSource:
            captured.update(kwargs)
            return fake_source

    monkeypatch.setattr("prml_vslam.pipeline.demo.AdvioDatasetService", FakeAdvioService)

    capped_source = build_runtime_source_from_request(request=request, path_config=path_config)
    assert capped_source is not None
    assert captured["dataset_serving"] == request.source.dataset_serving
    assert captured["respect_video_rotation"] is True

    stream = capped_source.open_stream(loop=False)
    stream.connect()
    assert stream.wait_for_packet() == "frame-0"
    assert stream.wait_for_packet() == "frame-1"
    with pytest.raises(EOFError):
        stream.wait_for_packet()
