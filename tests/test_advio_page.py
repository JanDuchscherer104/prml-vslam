from __future__ import annotations

import numpy as np

import prml_vslam.app.pages.advio as advio_page
from prml_vslam.interfaces import FramePacket, FramePacketProvenance


def test_advio_preview_frame_uses_live_image_renderer(monkeypatch) -> None:
    calls: dict[str, object] = {}
    monkeypatch.setattr(advio_page.st, "markdown", lambda text: calls.setdefault("markdown", text))
    monkeypatch.setattr(
        advio_page,
        "render_live_image",
        lambda image, **kwargs: calls.update(image=image, kwargs=kwargs),
    )
    packet = FramePacket(
        seq=0,
        timestamp_ns=1,
        arrival_timestamp_s=0.0,
        rgb=np.zeros((2, 2, 3), dtype=np.uint8),
        provenance=FramePacketProvenance(source_id="demo"),
    )

    advio_page._render_preview_frame(packet)

    assert calls["markdown"] == "**RGB Frame**"
    assert np.array_equal(calls["image"], packet.rgb)
    assert calls["kwargs"] == {"channels": "RGB", "clamp": True}
