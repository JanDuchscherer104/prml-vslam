# Streaming IO for VSLAM Benchmarking

This README explains the current Record3D transport implementation in `prml_vslam.io`.

Use [RECORD3D_PROTOCOL.md](./RECORD3D_PROTOCOL.md) for the detailed transport breakdown. Use this file for the repo-owned entry points and the current capability split between transports.

## Current Transport Support

[Record3D](https://record3d.app) ([GitHub](https://github.com/marek-simonik/record3d)) allows recording and streaming RGBD data from an iPhone. The repo currently supports two Record3D transport paths:

- `USB`
  - native `record3d` Python bindings
  - canonical programmatic ingress in this repo
- `Wi-Fi Preview`
  - Python-side WebRTC receiver plus HTTP signaling and metadata
  - implemented for the app and bounded live-source flows, but lower fidelity

## Repo-Owned Entry Points

- `prml-vslam record3d-devices`
  - lists USB-connected Record3D devices exposed by the upstream bindings
- `uv run streamlit run streamlit_app.py`
  - exposes a dedicated `Record3D` page for USB and Wi-Fi Preview
- `Record3DStreamingSource`
  - satisfies the shared `StreamingSequenceSource` protocol for pipeline-owned live sessions and currently supports both Record3D transports

## Capability Split

- `USB`
  - device discovery through the upstream bindings
  - RGB, depth, confidence, intrinsics, and pose in shared `FramePacket` objects
  - richer capture surface and the canonical ingress path
- `Wi-Fi Preview`
  - manual device-address entry and Python-side WebRTC negotiation
  - decoded RGB and depth plus intrinsics when metadata is available
  - no pose or confidence parity with USB
  - lower-fidelity preview path rather than the canonical ingestion surface

## Setup

The upstream `record3d` package currently requires the native Record3D prerequisites from the official project README:

- CMake on all platforms
- iTunes on macOS and Windows
- `libusbmuxd` on Linux

```bash
uv sync --extra streaming
uv run streamlit run streamlit_app.py
```

## Current Limitations

- Record3D allows only one Wi-Fi receiver at a time.
- The Wi-Fi Preview path does not currently expose a separate depth-confidence image, so packet `confidence` stays empty there.
- The Wi-Fi Preview path does not currently expose per-frame pose.
- The bounded pipeline live path can plan both Record3D transports, but the live `SequenceManifest` boundary is still minimal today and does not yet capture the richer source metadata that the longer-term offline-core design wants.
