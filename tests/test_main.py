"""Minimal CLI-facing smoke tests for the refactored pipeline module."""

from __future__ import annotations

from pathlib import Path

import pytest

from prml_vslam.main import _print_pipeline_demo_snapshot, plan_run, run_config
from prml_vslam.methods import MethodId
from prml_vslam.pipeline import PipelineMode, RunRequest
from prml_vslam.pipeline.demo import build_advio_demo_request, build_runtime_source_from_request
from prml_vslam.pipeline.contracts.request import DatasetSourceSpec, SlamStageConfig
from prml_vslam.pipeline.contracts.runtime import RunSnapshot, RunState
from prml_vslam.utils import PathConfig


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

    monkeypatch.setattr("prml_vslam.main.get_path_config", lambda: path_config)
    monkeypatch.setattr("prml_vslam.main.load_run_request_toml", lambda **kwargs: request)
    monkeypatch.setattr("prml_vslam.main.build_runtime_source_from_request", lambda **kwargs: runtime_source)
    monkeypatch.setattr("prml_vslam.main.RunService", FakeRunService)
    monkeypatch.setattr("prml_vslam.main._wait_for_pipeline_terminal_snapshot", lambda *args, **kwargs: RunSnapshot())
    monkeypatch.setattr("prml_vslam.main._print_pipeline_demo_snapshot", lambda snapshot: None)

    run_config(Path(".configs/pipelines/vista-full.toml"))

    assert captured["request"] is request
    assert captured["runtime_source"] is runtime_source


def test_build_runtime_source_from_request_caps_streaming_replay(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[1], artifacts_dir=tmp_path / ".artifacts")
    request = RunRequest(
        experiment_name="demo-streaming",
        mode=PipelineMode.STREAMING,
        output_dir=path_config.artifacts_dir,
        source=DatasetSourceSpec(dataset_id="advio", sequence_id="advio-01"),
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

    class FakeAdvioService:
        def __init__(self, path_config: PathConfig) -> None:
            del path_config

        def resolve_sequence_id(self, sequence_id: str) -> str:
            return sequence_id

        def build_streaming_source(self, **kwargs: object) -> FakeStreamingSource:
            return fake_source

    monkeypatch.setattr("prml_vslam.pipeline.demo.AdvioDatasetService", FakeAdvioService)

    capped_source = build_runtime_source_from_request(request=request, path_config=path_config)
    assert capped_source is not None

    stream = capped_source.open_stream(loop=False)
    stream.connect()
    assert stream.wait_for_packet() == "frame-0"
    assert stream.wait_for_packet() == "frame-1"
    with pytest.raises(EOFError):
        stream.wait_for_packet()
