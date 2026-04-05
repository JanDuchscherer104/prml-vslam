# Record3D Transport Protocol

This note defines the Record3D data surfaces currently used in this repository.

## Summary

- USB streaming uses the upstream Python bindings from the `record3d` package.
- Wi-Fi streaming uses the browser/WebRTC path from Record3D's official demos.
- The two transports do **not** expose the same payload.

## USB Streaming

USB is the richer transport and is the only one that currently exposes typed per-frame pose data in this repo.

### Session discovery and lifecycle

- Enumerate devices with `Record3DStream.get_connected_devices()`.
- Connect with `Record3DStream.connect(device)`.
- Receive lifecycle callbacks through:
  - `on_new_frame`
  - `on_stream_stopped`

### Per-frame payload

For each frame, the upstream Python bindings expose:

- `get_rgb_frame()`
  - RGB image
- `get_depth_frame()`
  - depth image
- `get_confidence_frame()`
  - confidence image aligned to depth
- `get_intrinsic_mat()`
  - intrinsic coefficients `fx, fy, tx, ty`
- `get_camera_pose()`
  - camera pose `(qx, qy, qz, qw, tx, ty, tz)`
- `get_device_type()`
  - `TRUEDEPTH` or `LIDAR`
- `get_misc_data()`
  - reserved upstream buffer; currently unused in this repo

### Repo mapping

In this repo, USB frames are normalized into `Record3DFrame` in [record3d.py](record3d.py):

- `rgb`
- `depth`
- `confidence`
- `intrinsic_matrix: CameraIntrinsics`
- `camera_pose: SE3Pose`
- `device_type`

### Implication

Yes: USB gives us ego pose already.

More precisely, it gives the upstream Record3D/ARKit camera pose attached to the current frame. In the codebase this is exposed as `SE3Pose` with explicit camera-to-world semantics.

## Wi-Fi Streaming

Wi-Fi uses Record3D's browser/WebRTC signaling flow.

### Signaling endpoints

The current official Wi-Fi demos use:

- `GET /getOffer`
  - fetch the remote WebRTC offer
- `POST /answer`
  - send the local WebRTC answer
- `GET /metadata`
  - fetch side metadata for the current stream

### Stream payload

The Wi-Fi track is a **composite video**:

- left half: depth encoded into color
- right half: RGB image

The official Wi-Fi RGBD demo treats the video width as `2 * frame_width` and decodes depth from the left half in shader/browser code.

### Metadata payload

The official Wi-Fi demos currently consume:

- `metadata["K"]`
  - flat intrinsic matrix payload
- `metadata["originalSize"]`
  - original source resolution when present

### What Wi-Fi does not expose here

In the current official Wi-Fi/browser flow used by this repo, we do **not** have a separate transport for:

- per-frame camera pose / ego pose
- IMU samples
- confidence map
- separate `inv_dist_std`
- Python-side raw `Record3DFrame` objects

Our current viewer therefore:

- renders RGB from the right half of the composite frame
- decodes depth from the left half
- shows `confidence` as unavailable on Wi-Fi
- renders intrinsics from `/metadata`

### Implication

No: the current Wi-Fi path in this repo does not provide ego pose.

If pose is required for evaluation or ingestion, the current practical path is USB, or a future custom Wi-Fi bridge if Record3D exposes a richer browser-side API later.

## Current Repo Contract

### USB path

- transport: native Python bindings
- consumer: [record3d.py](record3d.py)
- output:
  - RGB
  - depth
  - confidence
  - intrinsics
  - camera pose
  - device type

### Wi-Fi path

- transport: browser WebRTC + HTTP metadata
- consumer: [wifi_session.py](wifi_session.py), [wifi_signaling.py](wifi_signaling.py), and [wifi_packets.py](wifi_packets.py)
- output:
  - composite RGBD video preview
  - decoded RGB preview
  - decoded depth preview
  - typed `/metadata` model with:
    - `intrinsics: CameraIntrinsics | None`
    - `original_size: ImageSize | None`
    - `extra_metadata: dict[str, JsonValue]`
  - no pose

## Confidence vs `inv_dist_std`

These should not be treated as interchangeable by default.

- USB exposes a concrete `confidence` image through `get_confidence_frame()`.
- The current Wi-Fi/WebRTC path used by the official browser demos does not expose a separate confidence image.
- The official Wi-Fi demos also do not expose a separate `inv_dist_std` image.

So in this repo:

- USB has a real confidence modality.
- Wi-Fi does not currently expose either confidence or `inv_dist_std` as a separate image transport.

## Sources

- Official Record3D README:
  [record3d README](https://github.com/marek-simonik/record3d/blob/master/README.md)
- Official Python bindings:
  [PythonBindings.cpp](https://github.com/marek-simonik/record3d/blob/master/python-bindings/src/PythonBindings.cpp)
- Official Wi-Fi signaling / metadata demo:
  [SignalingClient.js](https://github.com/marek-simonik/record3d-wifi-streaming-and-rgbd-mp4-3d-video-demo/blob/master/js/app/video-sources/SignalingClient.js)
- Official Wi-Fi RGBD video handling:
  [WiFiStreamedVideoSource.js](https://github.com/marek-simonik/record3d-wifi-streaming-and-rgbd-mp4-3d-video-demo/blob/master/js/app/video-sources/WiFiStreamedVideoSource.js)
