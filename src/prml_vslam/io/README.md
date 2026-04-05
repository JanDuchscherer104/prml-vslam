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

- `uv run streamlit run streamlit_app.py` opens the packaged Streamlit app.
- The app exposes a dedicated `Record3D` page that renders pure Streamlit
  controls and previews.
- The page can start either a USB packet source or a Python-side Wi-Fi receiver.

### Wi-Fi Python Receiver

- The Wi-Fi path now runs in Python instead of in a browser-owned custom
  component.
- The receiver negotiates the Record3D WebRTC session through `/metadata`,
  `/getOffer`, and `/answer` or `/sendAnswer`.
- Wi-Fi frames are decoded in Python from the composite RGBD video into shared
  `Record3DFramePacket` objects.
- The Wi-Fi path exposes RGB, depth, and intrinsics when available.
- The current Wi-Fi transport does not expose a separate uncertainty or
  confidence image, so packet `uncertainty` stays empty on that path.
- Manual device-address entry is the default. Enter the address shown in the
  Record3D iPhone app, such as `myiPhone.local` or a LAN IP.
- Record3D allows only one Wi-Fi receiver at a time.
- Wi-Fi streaming is lower fidelity than the USB Python integration.

```bash
uv sync --extra streaming
uv run streamlit run streamlit_app.py
```

## Remaining Work

- Feed the shared typed `Record3DFramePacket` stream into the benchmark pipeline
  once the separate pipeline workspace is ready to consume live frames.
- Decide how much Wi-Fi-derived depth fidelity is sufficient for downstream
  consumers beyond visualization and diagnostics.
