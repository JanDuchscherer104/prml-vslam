"""Minimal CLI-facing smoke tests for the refactored pipeline module."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
import typer

from prml_vslam.datasets.advio import AdvioPoseSource
from prml_vslam.main import _print_pipeline_demo_snapshot, plan_run, run_config
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


def test_print_pipeline_demo_snapshot_accepts_projected_snapshot(tmp_path: Path) -> None:
    snapshot = RunSnapshot(
        run_id="demo",
        state=RunState.COMPLETED,
        artifacts={},
        error_message="",
    )

    _print_pipeline_demo_snapshot(snapshot)

    assert snapshot.state is RunState.COMPLETED


def test_build_advio_demo_request_enables_live_viewer_by_default(tmp_path: Path) -> None:
    request = build_advio_demo_request(
        path_config=PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts"),
        sequence_id="advio-01",
        mode=PipelineMode.STREAMING,
        method=MethodId.VISTA,
    )

    assert request.visualization.connect_live_viewer is True
    assert request.source.pose_source is AdvioPoseSource.GROUND_TRUTH
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

    assert request.source.pose_source is AdvioPoseSource.ARCORE
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
        source=DatasetSourceSpec(dataset_id="advio", sequence_id="advio-01"),
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
            pose_source="ground_truth",
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
    assert captured["pose_source"] == request.source.pose_source
    assert captured["respect_video_rotation"] is True

    stream = capped_source.open_stream(loop=False)
    stream.connect()
    assert stream.wait_for_packet() == "frame-0"
    assert stream.wait_for_packet() == "frame-1"
    with pytest.raises(EOFError):
        stream.wait_for_packet()
