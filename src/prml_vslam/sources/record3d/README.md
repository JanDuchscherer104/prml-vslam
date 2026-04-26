# Record3D Sources

This README explains the current Record3D transport implementation under
`prml_vslam.sources.record3d`.

Use [RECORD3D_PROTOCOL.md](./RECORD3D_PROTOCOL.md) for the detailed transport breakdown. Use this file for the repo-owned entry points and the current capability split between transports.

## Current Transport Support

[Record3D](https://record3d.app) ([GitHub](https://github.com/marek-simonik/record3d)) allows recording and streaming RGBD data from an iPhone. The repo currently supports two Record3D transport paths:

- `USB`
  - native `record3d` Python bindings
  - device discovery through the upstream bindings
  - RGB, depth, confidence, intrinsics, and pose in shared `Observation` objects
  - stable repo-owned ingress path
- `Wi-Fi Preview`
  - Python-side WebRTC receiver plus HTTP signaling and metadata
  - decoded RGB and depth plus intrinsics when metadata is available
  - stable repo-owned ingress path with equivalent support in this repository

## Repo-Owned Entry Points

- `prml-vslam record3d-devices`
  - lists USB-connected Record3D devices exposed by the upstream bindings
- `uv run streamlit run streamlit_app.py`
  - exposes a dedicated `Record3D` page for USB and Wi-Fi Preview
- `Record3DStreamingSource`
  - satisfies the shared `StreamingSequenceSource` protocol from
    `prml_vslam.sources.protocols`
  - opens an `ObservationStream` that emits shared
    `prml_vslam.interfaces.Observation` values
  - currently supports both Record3D transports

## Current Limitations

- The bounded pipeline live path can plan both Record3D transports, but the
  live `SequenceManifest` boundary is still minimal today and does not yet
  capture richer source metadata such as detailed transport session state.
