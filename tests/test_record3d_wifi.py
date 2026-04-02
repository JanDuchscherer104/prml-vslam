"""Tests for the Python-side Record3D Wi-Fi transport."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from urllib.error import HTTPError

import numpy as np

from prml_vslam.io.record3d import Record3DConnectionError, Record3DTransportId
from prml_vslam.io.record3d_wifi import (
    Record3DWiFiMetadata,
    Record3DWiFiSignalingClient,
    Record3DWiFiStreamConfig,
    Record3DWiFiStreamSession,
    decode_record3d_wifi_depth,
    normalize_record3d_device_address,
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

    assert metadata.intrinsic_matrix is not None
    assert metadata.intrinsic_matrix.fx == 100.0
    assert metadata.intrinsic_matrix.fy == 200.0
    assert metadata.intrinsic_matrix.tx == 10.0
    assert metadata.intrinsic_matrix.ty == 20.0
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
    packet = Record3DWiFiStreamSession._packet_from_video_frame(FakeVideoFrame(), metadata=metadata)

    assert packet.transport is Record3DTransportId.WIFI
    assert packet.rgb.shape == (2, 2, 3)
    assert packet.depth.shape == (2, 2)
    assert packet.uncertainty is None
    assert packet.intrinsic_matrix is not None
    assert packet.intrinsic_matrix.fx == 100.0
    assert packet.metadata["device_address"] == "http://myiPhone.local"


def test_record3d_wifi_stream_config_keeps_manual_device_address() -> None:
    config = Record3DWiFiStreamConfig(device_address="myiPhone.local")

    assert config.device_address == "myiPhone.local"


def test_record3d_wifi_answer_payload_matches_official_demo() -> None:
    payload = Record3DWiFiStreamSession._answer_request_payload(sdp="demo-sdp")

    assert payload == {"type": "answer", "data": "demo-sdp"}


def test_record3d_wifi_disconnect_does_not_raise_when_worker_lingers(monkeypatch) -> None:
    session = Record3DWiFiStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None
    warnings: list[str] = []
    fake_worker = SimpleNamespace(
        join=lambda timeout: None,
        is_alive=lambda: True,
    )
    session._worker = fake_worker
    monkeypatch.setattr(session.console, "warning", lambda message, *args: warnings.append(message % args if args else message))

    session.disconnect()

    assert warnings == ["Timed out stopping the Record3D Wi-Fi worker thread during cleanup."]


def test_record3d_wifi_closed_before_track_sets_setup_failure_without_logging(monkeypatch) -> None:
    session = Record3DWiFiStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None
    errors: list[str] = []
    stop_requests: list[bool] = []
    future = SimpleNamespace(
        _done=False,
        exception=None,
        done=lambda: future._done,
        set_exception=lambda exc: setattr(future, "_done", True) or setattr(future, "exception", exc),
    )
    monkeypatch.setattr(session.console, "error", lambda message, *args: errors.append(message % args if args else message))
    session._async_stop = SimpleNamespace(set=lambda: stop_requests.append(True))

    session._handle_connection_state_change(connection_state="closed", video_track_ready=future)

    assert errors == []
    assert not session._failure_event.is_set()
    assert stop_requests == [True]
    assert isinstance(future.exception, Record3DConnectionError)
    assert str(future.exception) == (
        "The Record3D Wi-Fi peer connection entered `closed` before the video track became available."
    )


def test_record3d_wifi_closed_after_connect_logs_runtime_failure(monkeypatch) -> None:
    session = Record3DWiFiStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None
    errors: list[str] = []
    stop_requests: list[bool] = []
    monkeypatch.setattr(session.console, "error", lambda message, *args: errors.append(message % args if args else message))
    session._async_stop = SimpleNamespace(set=lambda: stop_requests.append(True))
    session._connected_event.set()

    session._handle_connection_state_change(connection_state="closed", video_track_ready=None)

    assert session._failure_event.is_set()
    assert stop_requests == [True]
    assert errors == ["The Record3D Wi-Fi peer connection entered `closed`."]


def test_record3d_wifi_shutdown_exception_filter_only_suppresses_expected_stop_noise() -> None:
    session = Record3DWiFiStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None

    assert session._should_suppress_async_exception(
        exception=AttributeError("'NoneType' object has no attribute 'sendto'"),
        message="Exception in callback Transaction.__retry()",
        stop_requested=True,
    )
    assert session._should_suppress_async_exception(
        exception=RuntimeError("RTCIceTransport is closed"),
        message="Task exception was never retrieved",
        stop_requested=True,
    )
    assert not session._should_suppress_async_exception(
        exception=RuntimeError("unexpected"),
        message="Task exception was never retrieved",
        stop_requested=True,
    )
    assert not session._should_suppress_async_exception(
        exception=AttributeError("'NoneType' object has no attribute 'sendto'"),
        message="Exception in callback Transaction.__retry()",
        stop_requested=False,
    )


def test_record3d_wifi_metadata_failure_is_non_fatal(monkeypatch) -> None:
    session = Record3DWiFiStreamConfig(device_address="myiPhone.local").setup_target()
    assert session is not None
    session._metadata = Record3DWiFiMetadata(device_address="http://myiPhone.local")
    warnings: list[str] = []
    monkeypatch.setattr(session.signaling_client, "get_metadata", lambda: (_ for _ in ()).throw(TimeoutError("slow")))
    monkeypatch.setattr(session.console, "warning", lambda message, *args: warnings.append(message % args if args else message))

    asyncio.run(session._load_metadata_best_effort())

    assert warnings == ["Could not retrieve Record3D Wi-Fi metadata: slow"]
    assert session._metadata.device_address == "http://myiPhone.local"
