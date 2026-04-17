"""Tests for the Python-side Record3D Wi-Fi transport."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from urllib.error import HTTPError

import numpy as np

from prml_vslam.interfaces import FramePacket
from prml_vslam.io import wifi_session as wifi_session_module
from prml_vslam.io.record3d import Record3DTransportId
from prml_vslam.io.record3d_source import Record3DStreamingSourceConfig
from prml_vslam.io.wifi_packets import (
    Record3DWiFiMetadata,
    decode_record3d_wifi_depth,
    record3d_wifi_packet_from_video_frame,
)
from prml_vslam.io.wifi_receiver import (
    _Record3DWiFiReceiverRuntime,
    _should_suppress_record3d_async_exception,
)
from prml_vslam.io.wifi_session import Record3DWiFiPreviewStreamConfig, open_record3d_wifi_preview_stream
from prml_vslam.io.wifi_signaling import (
    Record3DWiFiSignalingClient,
    build_record3d_answer_request_payload,
    normalize_record3d_device_address,
)
from prml_vslam.protocols.source import OfflineSequenceSource, StreamingSequenceSource


def _build_runtime(
    *,
    console: SimpleNamespace | None = None,
    get_metadata=None,
    on_failure=None,
    stop_requested=None,
) -> _Record3DWiFiReceiverRuntime:
    return _Record3DWiFiReceiverRuntime(
        config=Record3DWiFiPreviewStreamConfig(device_address="myiPhone.local"),
        console=console or SimpleNamespace(warning=lambda *args: None),
        device_address="http://myiPhone.local",
        get_offer=lambda: {"type": "offer", "sdp": "demo"},
        get_metadata=get_metadata or (lambda: {}),
        send_answer=lambda answer: None,
        on_metadata=lambda metadata: None,
        on_connected=lambda metadata: None,
        on_packet=lambda packet: None,
        on_failure=on_failure or (lambda message: None),
        stop_requested=stop_requested or (lambda: False),
    )


def test_normalize_record3d_device_address_adds_http_scheme() -> None:
    assert normalize_record3d_device_address("myiPhone.local") == "http://myiPhone.local"
    assert normalize_record3d_device_address(" http://192.168.1.100/ ") == "http://192.168.1.100"


def test_record3d_wifi_metadata_parses_row_major_intrinsics_and_original_size() -> None:
    metadata = Record3DWiFiMetadata.from_api_payload(
        device_address="http://myiPhone.local",
        payload={
            "K": [100.0, 0.0, 10.0, 0.0, 200.0, 20.0, 0.0, 0.0, 1.0],
            "originalSize": [960, 720],
            "maxDepth": 3.0,
        },
    )

    assert metadata.intrinsics is not None
    assert metadata.intrinsics.fx == 100.0
    assert metadata.intrinsics.fy == 200.0
    assert metadata.intrinsics.cx == 10.0
    assert metadata.intrinsics.cy == 20.0
    assert metadata.original_width == 960
    assert metadata.original_height == 720
    assert metadata.depth_max_meters == 3.0


def test_decode_record3d_wifi_depth_maps_hue_to_depth_range() -> None:
    depth_rgb = np.array(
        [
            [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
        ],
        dtype=np.uint8,
    )

    decoded = decode_record3d_wifi_depth(depth_rgb, depth_max_meters=3.0)

    np.testing.assert_allclose(decoded[0, 0], 3.0)
    np.testing.assert_allclose(decoded[0, 1], 1.0, atol=1e-5)
    np.testing.assert_allclose(decoded[0, 2], 2.0, atol=1e-5)


def test_record3d_wifi_signaling_client_prefers_answer_endpoint(monkeypatch) -> None:
    client = Record3DWiFiSignalingClient("myiPhone.local", timeout_seconds=1.0)
    attempted_endpoints: list[str] = []

    def fake_request_json(method: str, endpoint: str, *, payload=None, expect_json: bool = True):
        attempted_endpoints.append(endpoint)
        return {}

    monkeypatch.setattr(client, "_request_json", fake_request_json)

    client.send_answer({"type": "answer", "data": "demo"})

    assert attempted_endpoints == ["/answer"]


def test_record3d_wifi_signaling_client_falls_back_to_send_answer_endpoint(monkeypatch) -> None:
    client = Record3DWiFiSignalingClient("myiPhone.local", timeout_seconds=1.0)
    attempted_endpoints: list[str] = []

    def fake_request_json(method: str, endpoint: str, *, payload=None, expect_json: bool = True):
        attempted_endpoints.append(endpoint)
        if endpoint == "/answer":
            raise HTTPError(url=endpoint, code=404, msg="missing", hdrs=None, fp=None)
        return {}

    monkeypatch.setattr(client, "_request_json", fake_request_json)

    client.send_answer({"type": "answer", "data": "demo"})

    assert attempted_endpoints == ["/answer", "/sendAnswer"]


def test_record3d_wifi_packet_decoder_emits_shared_contract() -> None:
    class FakeVideoFrame:
        def to_ndarray(self, *, format: str) -> np.ndarray:
            assert format == "rgb24"
            depth_half = np.array(
                [
                    [[255, 0, 0], [0, 255, 0]],
                    [[0, 0, 255], [255, 0, 0]],
                ],
                dtype=np.uint8,
            )
            rgb_half = np.array(
                [
                    [[1, 2, 3], [4, 5, 6]],
                    [[7, 8, 9], [10, 11, 12]],
                ],
                dtype=np.uint8,
            )
            return np.concatenate([depth_half, rgb_half], axis=1)

    metadata = Record3DWiFiMetadata.from_api_payload(
        device_address="http://myiPhone.local",
        payload={"K": [[100.0, 0.0, 10.0], [0.0, 200.0, 20.0], [0.0, 0.0, 1.0]], "maxDepth": 3.0},
    )
    packet = record3d_wifi_packet_from_video_frame(FakeVideoFrame(), metadata=metadata, seq=0)

    assert isinstance(packet, FramePacket)
    assert packet.provenance.transport is Record3DTransportId.WIFI
    assert packet.rgb.shape == (2, 2, 3)
    assert packet.depth.shape == (2, 2)
    assert packet.confidence is None
    assert packet.intrinsics is not None
    assert packet.intrinsics.fx == 100.0
    assert packet.provenance.device_address == "http://myiPhone.local"


def test_record3d_wifi_preview_stream_config_keeps_manual_device_address() -> None:
    config = Record3DWiFiPreviewStreamConfig(device_address="myiPhone.local")

    assert config.device_address == "myiPhone.local"
    session = open_record3d_wifi_preview_stream(device_address="myiPhone.local", frame_timeout_seconds=0.5)
    assert session.config.device_address == "myiPhone.local"
    assert session.config.frame_timeout_seconds == 1.0
    assert session.config.signaling_timeout_seconds == 10.0
    assert session.config.setup_timeout_seconds == 12.0


def test_record3d_wifi_answer_payload_matches_official_demo() -> None:
    payload = build_record3d_answer_request_payload(sdp="demo-sdp")

    assert payload == {"type": "answer", "data": "demo-sdp"}


def test_record3d_wifi_disconnect_does_not_raise_when_worker_lingers(monkeypatch) -> None:
    session = Record3DWiFiPreviewStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None
    warnings: list[str] = []
    fake_worker = SimpleNamespace(
        join=lambda timeout: None,
        is_alive=lambda: True,
    )
    session._worker = fake_worker
    monkeypatch.setattr(
        session.console, "warning", lambda message, *args: warnings.append(message % args if args else message)
    )

    session.disconnect()

    assert warnings == ["Timed out stopping the Record3D Wi-Fi preview worker thread during cleanup."]


def test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging() -> None:
    errors: list[str] = []
    stop_requests: list[bool] = []
    runtime = _build_runtime(on_failure=errors.append)
    future = SimpleNamespace(
        _done=False,
        exception=None,
        done=lambda: future._done,
        set_exception=lambda exc: setattr(future, "_done", True) or setattr(future, "exception", exc),
    )
    runtime._async_stop = SimpleNamespace(set=lambda: stop_requests.append(True))

    runtime._handle_connection_state_change(connection_state="closed", video_track_ready=future)

    assert errors == []
    assert stop_requests == [True]
    assert isinstance(future.exception, RuntimeError)
    assert str(future.exception) == (
        "The Record3D Wi-Fi peer connection entered `closed` before the video track became available."
    )


def test_record3d_wifi_closed_after_connect_logs_runtime_failure() -> None:
    errors: list[str] = []
    stop_requests: list[bool] = []
    runtime = _build_runtime(on_failure=errors.append)
    runtime._async_stop = SimpleNamespace(set=lambda: stop_requests.append(True))
    runtime._connected = True

    runtime._handle_connection_state_change(connection_state="closed", video_track_ready=None)

    assert stop_requests == [True]
    assert errors == ["The Record3D Wi-Fi peer connection entered `closed`."]


def test_record3d_wifi_shutdown_exception_filter_only_suppresses_expected_stop_noise() -> None:
    assert _should_suppress_record3d_async_exception(
        exception=AttributeError("'NoneType' object has no attribute 'sendto'"),
        message="Exception in callback Transaction.__retry()",
        stop_requested=True,
    )
    assert _should_suppress_record3d_async_exception(
        exception=RuntimeError("RTCIceTransport is closed"),
        message="Task exception was never retrieved",
        stop_requested=True,
    )
    assert not _should_suppress_record3d_async_exception(
        exception=RuntimeError("unexpected"),
        message="Task exception was never retrieved",
        stop_requested=True,
    )
    assert not _should_suppress_record3d_async_exception(
        exception=AttributeError("'NoneType' object has no attribute 'sendto'"),
        message="Exception in callback Transaction.__retry()",
        stop_requested=False,
    )


def test_record3d_wifi_metadata_failure_is_non_fatal() -> None:
    warnings: list[str] = []
    runtime = _build_runtime(
        console=SimpleNamespace(warning=lambda message, *args: warnings.append(message % args if args else message)),
        get_metadata=lambda: (_ for _ in ()).throw(TimeoutError("slow")),
    )

    asyncio.run(runtime._load_metadata_best_effort())

    assert warnings == ["Could not retrieve Record3D Wi-Fi metadata: slow"]
    assert runtime.metadata.device_address == "http://myiPhone.local"


def test_record3d_wifi_streaming_source_satisfies_shared_source_protocol(monkeypatch, tmp_path) -> None:
    sentinel_stream = object()
    monkeypatch.setattr(
        wifi_session_module,
        "open_record3d_wifi_preview_stream",
        lambda *, device_address, frame_timeout_seconds: (
            sentinel_stream if (device_address, frame_timeout_seconds) == ("myiPhone.local", 0.5) else None
        ),
    )

    source = Record3DStreamingSourceConfig(
        transport=Record3DTransportId.WIFI,
        device_address="myiPhone.local",
        frame_timeout_seconds=0.5,
    ).setup_target()

    assert source is not None
    assert isinstance(source, OfflineSequenceSource)
    assert isinstance(source, StreamingSequenceSource)
    assert source.label == "Record3D Wi-Fi Preview (myiPhone.local)"
    assert source.prepare_sequence_manifest(tmp_path).sequence_id == "record3d-wifi-myiphone-local"
    assert source.open_stream(loop=False) is sentinel_stream
