"""HTTP signaling helpers for Record3D Wi-Fi preview streaming."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def normalize_record3d_device_address(value: str) -> str:
    """Normalize a Record3D device address into an explicit HTTP URL."""
    trimmed = value.strip()
    if trimmed == "":
        return ""
    if trimmed.startswith(("http://", "https://")):
        return trimmed.rstrip("/")
    return f"http://{trimmed.rstrip('/')}"


def build_record3d_answer_request_payload(*, sdp: str) -> dict[str, str]:
    """Build the JSON answer payload expected by Record3D's signaling API."""
    return {"type": "answer", "data": sdp}


class Record3DWiFiSignalingClient:
    """Small synchronous client for the Record3D Wi-Fi signaling endpoints."""

    def __init__(self, device_address: str, *, timeout_seconds: float) -> None:
        normalized = normalize_record3d_device_address(device_address)
        if normalized == "":
            raise RuntimeError("Record3D Wi-Fi preview requires a device address.")
        self.device_address = normalized
        self.timeout_seconds = timeout_seconds

    def get_offer(self) -> dict[str, Any]:
        """Fetch the device's WebRTC offer from `/getOffer`."""
        try:
            return self._request_json("GET", "/getOffer")
        except HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError(
                    "Record3D allows only one Wi-Fi receiver at a time. Disconnect the existing peer and retry."
                ) from exc
            raise RuntimeError(f"Record3D offer request failed with HTTP {exc.code}.") from exc
        except TimeoutError as exc:
            raise RuntimeError("Timed out waiting for the Record3D Wi-Fi offer from the device.") from exc
        except URLError as exc:
            raise RuntimeError(
                "Could not reach the Record3D device. Check that the iPhone and this machine are on the same network."
            ) from exc

    def get_metadata(self) -> dict[str, Any]:
        """Fetch the device metadata from `/metadata`."""
        try:
            return self._request_json("GET", "/metadata")
        except HTTPError as exc:
            raise RuntimeError(f"Record3D metadata request failed with HTTP {exc.code}.") from exc
        except TimeoutError as exc:
            raise RuntimeError("Timed out waiting for Record3D Wi-Fi metadata from the device.") from exc
        except URLError as exc:
            raise RuntimeError("Could not retrieve Record3D metadata from the configured device.") from exc

    def send_answer(self, answer: dict[str, Any]) -> None:
        """Post the local WebRTC answer back to the Record3D device."""
        for endpoint in ("/answer", "/sendAnswer"):
            try:
                self._request_json("POST", endpoint, payload=answer, expect_json=False)
                return
            except HTTPError as exc:
                if exc.code in {404, 405}:
                    continue
                raise RuntimeError(f"Record3D answer request to `{endpoint}` failed with HTTP {exc.code}.") from exc
            except TimeoutError as exc:
                if endpoint == "/answer":
                    continue
                raise RuntimeError(
                    f"Timed out sending the WebRTC answer to `{endpoint}` on the Record3D device."
                ) from exc
            except URLError as exc:
                raise RuntimeError("Could not send the WebRTC answer back to the Record3D device.") from exc

        raise RuntimeError("Record3D did not accept the WebRTC answer on `/answer` or `/sendAnswer`.")

    def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        payload: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{self.device_address}{endpoint}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if payload is not None else {},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
            body = response.read()
        if not expect_json:
            return {}
        loaded = json.loads(body.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise RuntimeError(f"Expected JSON object from `{endpoint}`, but received {type(loaded).__name__}.")
        return loaded
