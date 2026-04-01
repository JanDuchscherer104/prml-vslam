# Streaming IO for VSLAM Benchmarking

[Record3D](https://record3d.app) ([GitHub](https://github.com/marek-simonik/record3d)) allows recording and *streaming* RGBD data from an iPhone.
- We can use Apple's built-in ARKit odometry and IMU data as GT baseline for trajectory evaluation.

## Implemented Consumers

### USB Python Preview
- `prml-vslam record3d-devices` lists USB-connected Record3D devices exposed by the upstream Python bindings.
- `prml-vslam record3d-preview` opens a simple OpenCV consumer that displays the incoming RGB, depth, and optional confidence stream.
- The preview is intentionally decoupled from the VSLAM pipeline for now so it can later be wired into the separate pipeline workspace.

```bash
uv sync --extra streaming
prml-vslam record3d-devices
prml-vslam record3d-preview --device-index 0
```

The upstream `record3d` package currently requires the native Record3D prerequisites from the official project README:

- CMake on all platforms
- iTunes on macOS and Windows
- `libusbmuxd` on Linux

### Wi-Fi Streamlit Viewer

- `uv run streamlit run streamlit_app.py` opens the Streamlit workbench with a dedicated Record3D Wi-Fi viewer.
- The browser component talks directly to the Record3D Wi-Fi/WebRTC endpoints: `/metadata`, `/getOffer`, and `/answer`.
- The Wi-Fi path is intentionally display-only. It previews the composite RGBD video and metadata in the browser, but it does not expose Python-side `Record3DFrame` objects.
- Manual device-address entry is the default. Enter the address shown in the Record3D iPhone app, such as `myiPhone.local` or a LAN IP.
- Chrome and Safari are the supported browsers for this path. Record3D allows only one Wi-Fi receiver at a time.
- Wi-Fi streaming is lower fidelity than the USB Python integration.

```bash
uv run streamlit run streamlit_app.py
```

## Remaining Work

- Feed the typed USB `Record3DFrame` stream into the benchmark pipeline once the separate pipeline workspace is ready to consume live frames.
- Decide separately whether the Wi-Fi path needs a browser-to-Python bridge for benchmark ingestion, instead of treating it as a viewer-only surface.
