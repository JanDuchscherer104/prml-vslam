# Streaming IO for VSLAM Benchmarking

[Record3D](https://record3d.app) ([GitHub](https://github.com/marek-simonik/record3d))
allows recording and streaming RGBD data from an iPhone.

- We can use Apple's built-in ARKit odometry and IMU data as GT baseline for
  trajectory evaluation.

## Implemented Consumers

- `prml-vslam record3d-devices` lists USB-connected Record3D devices exposed by
  the upstream Python bindings.

The upstream `record3d` package currently requires the native Record3D
prerequisites from the official project README:

- CMake on all platforms
- iTunes on macOS and Windows
- `libusbmuxd` on Linux

### Streamlit Record3D Page

- `uv run prml-vslam-app` opens the packaged Streamlit app.
- The app exposes a dedicated `Record3D` page that renders pure Streamlit
  controls and previews.
- The page can start the official USB packet source or an optional Python-side
  Wi-Fi preview receiver.
- [`io.record3d_source`](./record3d_source.py) also exposes
  [`Record3DStreamingSource`](./record3d_source.py), which satisfies the shared
  [`StreamingSequenceSource`](../protocols/source.py) protocol for
  pipeline-owned live sessions.

### Wi-Fi Python Preview Receiver

- The Wi-Fi path now runs in Python instead of in a browser-owned custom
  component.
- The receiver negotiates the Record3D WebRTC session through `/metadata`,
  `/getOffer`, and `/answer` or `/sendAnswer`.
- Wi-Fi frames are decoded in Python from the composite RGBD video into shared
  [`FramePacket`](../interfaces/runtime.py) objects.
- The Wi-Fi path exposes RGB, depth, and intrinsics when available.
- The current Wi-Fi transport does not expose a separate depth-confidence
  image, so packet `confidence` stays empty on that path.
- Manual device-address entry is the default. Enter the address shown in the
  Record3D iPhone app, such as `myiPhone.local` or a LAN IP.
- Record3D allows only one Wi-Fi receiver at a time.
- Wi-Fi preview is lower fidelity than the USB Python integration and remains a
  preview-only fallback instead of the canonical ingestion path.

```bash
uv sync --extra streaming
uv run prml-vslam-app
```

## Remaining Work

- Integrate [`LiveSourceSpec`](../pipeline/contracts.py) resolution so pipeline
  orchestration can build the appropriate Record3D streaming source directly
  from typed live-source config.
- Decide how much Wi-Fi-derived depth fidelity is sufficient for downstream
  consumers beyond visualization and diagnostics.
