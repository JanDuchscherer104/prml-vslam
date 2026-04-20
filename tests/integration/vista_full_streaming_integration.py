"""Opt-in real-data integration test for the full ViSTA streaming pipeline.

This file intentionally lives outside the default `test_*.py` discovery pattern,
so a normal `uv run pytest` does not execute it.

Run it explicitly with:

```bash
uv run pytest tests/integration/vista_full_streaming_integration.py -q -s
```
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from prml_vslam.pipeline.contracts.runtime import RunState
from prml_vslam.pipeline.demo import build_runtime_source_from_request, load_run_request_toml
from prml_vslam.pipeline.run_service import RunService
from prml_vslam.utils import PathConfig

_CONFIG_PATH = Path(".configs/pipelines/vista-full.toml")


def test_vista_full_streaming_pipeline_end_to_end() -> None:
    path_config = PathConfig(root=Path(__file__).resolve().parents[2])
    request = load_run_request_toml(path_config=path_config, config_path=_CONFIG_PATH)
    if request.mode.value != "streaming":
        pytest.skip("The configured integration request is not in streaming mode.")
    _require_vista_prerequisites(path_config)

    runtime_source = build_runtime_source_from_request(request=request, path_config=path_config)
    service = RunService(path_config=path_config)
    try:
        service.start_run(request=request, runtime_source=runtime_source)
        snapshot = _wait_for_terminal_snapshot(service, timeout_seconds=420.0)
    finally:
        service.shutdown()

    assert snapshot.state is RunState.COMPLETED, snapshot.error_message
    assert snapshot.sequence_manifest is not None
    assert snapshot.slam is not None
    assert snapshot.summary is not None


def _wait_for_terminal_snapshot(service: RunService, *, timeout_seconds: float):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        snapshot = service.snapshot()
        if snapshot.state not in {RunState.IDLE, RunState.PREPARING, RunState.RUNNING}:
            return snapshot
        time.sleep(1.0)
    raise AssertionError("Streaming ViSTA integration run did not reach a terminal state within the timeout.")


def _require_vista_prerequisites(path_config: PathConfig) -> None:
    if os.environ.get("CONDA_DEFAULT_ENV") != "prml-vslam":
        pytest.skip("ViSTA integration must run inside the 'prml-vslam' conda environment.")
    required_paths = [
        path_config.resolve_repo_path("external/vista-slam"),
        path_config.resolve_repo_path("external/vista-slam/pretrains/frontend_sta_weights.pth"),
        path_config.resolve_repo_path("external/vista-slam/pretrains/ORBvoc.txt"),
        path_config.resolve_dataset_dir("advio") / "advio-01" / "iphone" / "frames.mov",
    ]
    missing = [path for path in required_paths if not path.exists()]
    if missing:
        pytest.skip("ViSTA integration prerequisites are missing: " + ", ".join(str(path) for path in missing))
