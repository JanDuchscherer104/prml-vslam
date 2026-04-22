"""Tests for target pipeline stage runtime contracts."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from prml_vslam.interfaces.ingest import SequenceManifest
from prml_vslam.interfaces.transforms import FrameTransform
from prml_vslam.pipeline.contracts.events import StageOutcome
from prml_vslam.pipeline.contracts.provenance import StageStatus
from prml_vslam.pipeline.contracts.stages import StageKey
from prml_vslam.pipeline.stages.base.contracts import (
    StageResult,
    StageRuntimeStatus,
    StageRuntimeUpdate,
    VisualizationIntent,
    VisualizationItem,
)
from prml_vslam.pipeline.stages.base.handles import TransientPayloadRef
from prml_vslam.pipeline.stages.base.protocols import (
    BaseStageRuntime,
    LiveUpdateStageRuntime,
    OfflineStageRuntime,
    StreamingStageRuntime,
)
from prml_vslam.utils import BaseData


class _OfflineInput(BaseData):
    sequence: SequenceManifest


class _StreamingInput(BaseData):
    run_label: str


class _StreamItem(BaseData):
    seq: int


def _outcome(stage_key: StageKey = StageKey.INGEST) -> StageOutcome:
    return StageOutcome(
        stage_key=stage_key,
        status=StageStatus.COMPLETED,
        config_hash="config",
        input_fingerprint="input",
    )


def _status(stage_key: StageKey = StageKey.INGEST) -> StageRuntimeStatus:
    return StageRuntimeStatus(
        stage_key=stage_key,
        lifecycle_state=StageStatus.COMPLETED,
        progress_message="done",
        completed_steps=1,
        total_steps=1,
        progress_unit="stage",
        submitted_count=1,
        completed_count=1,
        processed_items=1,
        fps=30.0,
        throughput=1.0,
        throughput_unit="stage/s",
        latency_ms=4.0,
        executor_id="local",
        resource_assignment={"cpu": 1.0, "node": "local"},
        updated_at_ns=10,
    )


def test_stage_result_holds_domain_payload_and_final_status() -> None:
    manifest = SequenceManifest(sequence_id="seq-1")
    result = StageResult(
        stage_key=StageKey.INGEST,
        payload=manifest,
        outcome=_outcome(),
        final_runtime_status=_status(),
    )

    assert result.payload == manifest
    assert result.outcome.status is StageStatus.COMPLETED
    assert result.final_runtime_status.lifecycle_state is StageStatus.COMPLETED


def test_stage_runtime_status_is_frozen_and_strict() -> None:
    status = _status()

    with pytest.raises(ValidationError):
        status.lifecycle_state = StageStatus.FAILED

    with pytest.raises(ValidationError):
        StageRuntimeStatus.model_validate({"stage_key": "slam", "unexpected": "field"})

    with pytest.raises(ValidationError):
        StageRuntimeStatus(stage_key=StageKey.SLAM, in_flight_count=-1)


def test_visualization_item_carries_transient_payload_refs_without_sdk_fields() -> None:
    image_ref = TransientPayloadRef(
        handle_id="payload-1",
        payload_kind="image",
        media_type="image/rgb",
        shape=(2, 3, 3),
        dtype="uint8",
        size_bytes=18,
    )
    item = VisualizationItem(
        intent=VisualizationIntent.RGB_IMAGE,
        role="model_rgb",
        payload_refs={"image": image_ref},
        pose=FrameTransform(qx=0.0, qy=0.0, qz=0.0, qw=1.0, tx=0.0, ty=0.0, tz=0.0),
        frame_index=2,
        keyframe_index=1,
        space="camera_local",
        metadata={"is_keyframe": True},
    )

    dumped = item.model_dump(mode="json")

    assert dumped["payload_refs"]["image"]["handle_id"] == "payload-1"
    assert dumped["intent"] == "rgb_image"
    assert "rerun" not in dumped
    assert "entity_path" not in dumped
    assert "timeline" not in dumped


def test_stage_runtime_update_projects_to_json() -> None:
    update = StageRuntimeUpdate(
        stage_key=StageKey.SLAM,
        timestamp_ns=123,
        semantic_events=[SequenceManifest(sequence_id="seq-1")],
        visualizations=[
            VisualizationItem(
                intent=VisualizationIntent.CLEAR,
                role="reset",
            )
        ],
        runtime_status=_status(StageKey.SLAM),
    )

    dumped = update.model_dump(mode="json")

    assert dumped["stage_key"] == "slam"
    assert dumped["semantic_events"][0]["sequence_id"] == "seq-1"
    assert dumped["visualizations"][0]["intent"] == "clear"
    assert dumped["runtime_status"]["lifecycle_state"] == "completed"


def test_runtime_protocols_accept_small_fake_implementations() -> None:
    class FakeRuntime:
        def __init__(self) -> None:
            self.items: list[_StreamItem] = []

        def status(self) -> StageRuntimeStatus:
            return _status(StageKey.SLAM)

        def stop(self) -> None:
            return None

        def run_offline(self, input_payload: _OfflineInput) -> StageResult:
            return StageResult(
                stage_key=StageKey.INGEST,
                payload=input_payload.sequence,
                outcome=_outcome(StageKey.INGEST),
                final_runtime_status=_status(StageKey.INGEST),
            )

        def drain_runtime_updates(self, max_items: int | None = None) -> list[StageRuntimeUpdate]:
            return [StageRuntimeUpdate(stage_key=StageKey.SLAM, timestamp_ns=1)][:max_items]

        def start_streaming(self, input_payload: _StreamingInput) -> None:
            assert input_payload.run_label

        def submit_stream_item(self, item: _StreamItem) -> None:
            self.items.append(item)

        def finish_streaming(self) -> StageResult:
            return StageResult(
                stage_key=StageKey.SLAM,
                payload=None,
                outcome=_outcome(StageKey.SLAM),
                final_runtime_status=_status(StageKey.SLAM),
            )

    runtime = FakeRuntime()

    assert isinstance(runtime, BaseStageRuntime)
    assert isinstance(runtime, OfflineStageRuntime)
    assert isinstance(runtime, LiveUpdateStageRuntime)
    assert isinstance(runtime, StreamingStageRuntime)
    assert (
        runtime.run_offline(_OfflineInput(sequence=SequenceManifest(sequence_id="seq-1"))).stage_key is StageKey.INGEST
    )
    assert runtime.drain_runtime_updates(max_items=1)[0].stage_key is StageKey.SLAM
    runtime.start_streaming(_StreamingInput(run_label="demo"))
    runtime.submit_stream_item(_StreamItem(seq=1))
    assert runtime.finish_streaming().stage_key is StageKey.SLAM
