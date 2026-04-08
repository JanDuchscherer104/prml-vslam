# Record3D Transport Protocol

This note catalogs the upstream Record3D surfaces followed by the repo-owned adapters. It intentionally includes the full method inventory exposed by the referenced USB bindings and official Wi-Fi demos so capability and modality questions can be answered from one page.

For repo-owned entry points and higher-level transport guidance, see [README.md](./README.md).

## Version And Transport Scope

- The repo uses two upstream-facing Record3D surfaces:
  - USB via the native `record3d` Python bindings
  - Wi-Fi Preview via the official HTTP plus WebRTC browser demos
- The two transports are not payload-equivalent and should not be treated as interchangeable ingestion contracts.

## USB Binding Surface

### Exposed Python Types

| Type | Exposed fields | Meaning | Repo use |
| --- | --- | --- | --- |
| `DeviceInfo` | `product_id`, `udid`, `_handle` | connected iOS device identity and native handle | `product_id` and `udid` are normalized into `Record3DDevice`; `_handle` is not used |
| `IntrinsicMatrixCoeffs` | `fx`, `fy`, `tx`, `ty` | upstream intrinsic coefficients | normalized into `CameraIntrinsics(fx, fy, cx=tx, cy=ty)` |
| `CameraPose` | `qx`, `qy`, `qz`, `qw`, `tx`, `ty`, `tz` | per-frame camera pose from Record3D / ARKit | normalized into `SE3Pose` |

### Exposed `Record3DStream` Methods And Callbacks

| Member | Kind | Functionality / payload | Repo use |
| --- | --- | --- | --- |
| `Record3DStream()` | constructor | create one stream object | used directly |
| `get_connected_devices()` | static method | enumerate currently connected USB devices | used directly |
| `connect(device)` | method | connect to one paired iOS device and begin streaming | used directly |
| `disconnect()` | method | stop streaming and tear down the current USB connection | used directly |
| `get_depth_frame()` | method | current depth frame | used directly |
| `get_rgb_frame()` | method | current RGB frame | used directly |
| `get_confidence_frame()` | method | confidence image aligned to the current depth frame | used directly |
| `get_misc_data()` | method | reserved misc-data buffer | currently ignored |
| `get_intrinsic_mat()` | method | current-frame intrinsic coefficients | used directly |
| `get_camera_pose()` | method | current-frame camera pose | used directly |
| `get_device_type()` | method | device type enum: `TRUEDEPTH = 0`, `LIDAR = 1` | used directly |
| `on_new_frame` | callback field | invoked when a new frame arrives | used directly |
| `on_stream_stopped` | callback field | invoked when the stream stops | used directly |

### USB Modalities

| Modality | Upstream USB support | Repo normalization |
| --- | --- | --- |
| RGB | yes | `FramePacket.rgb` |
| Depth | yes | `FramePacket.depth` |
| Confidence | yes | `FramePacket.confidence` |
| Intrinsics | yes | `FramePacket.intrinsics` |
| Camera pose | yes | `FramePacket.pose` |
| Device type | yes | `FramePacket.metadata["device_type"]` |
| Reserved misc buffer | yes | not currently surfaced |

USB is therefore the canonical Record3D ingress in this repo and the only transport that currently carries typed per-frame pose and confidence.

## Wi-Fi Preview Demo Surface

### Official Signaling And Metadata Endpoints

| Surface | Kind | Functionality / payload | Repo handling |
| --- | --- | --- | --- |
| `GET /getOffer` | HTTP endpoint | fetch the device WebRTC offer; upstream README notes HTTP `403` when another peer is already connected | used directly |
| `POST /sendAnswer` | HTTP endpoint | send the local WebRTC answer back to the device | supported for compatibility |
| `POST /answer` | HTTP endpoint | send the local WebRTC answer back to the device; used by the Three.js demo | supported for compatibility |
| `GET /metadata` | HTTP endpoint | fetch stream metadata such as `K` and optional original size | used directly |

### Official Demo Client Methods

#### `SignalingClient.js`

| Member | Kind | Functionality / payload | Repo parity |
| --- | --- | --- | --- |
| `Record3DSignalingClient(serverURL)` | constructor | store the device base URL | mirrored by `Record3DWiFiSignalingClient` |
| `retrieveOffer()` | method | fetch `/getOffer` and decode JSON | mirrored by `get_offer()` |
| `sendAnswer(answer)` | method | POST answer JSON to `/answer` | mirrored by `send_answer()` with `/answer` and `/sendAnswer` fallback |
| `getMetadata(serverURL)` | function | fetch `/metadata` and decode JSON | mirrored by `get_metadata()` |

#### `WiFiStreamedVideoSource.js`

| Member | Kind | Functionality / payload | Repo parity |
| --- | --- | --- | --- |
| `WiFiStreamedVideoSource(deviceAddress)` | constructor | initialize one Wi-Fi video source, state, and hidden HTML video tag | mirrored structurally in the repo runtime |
| `connect()` | method | establish `RTCPeerConnection`, pull the remote offer, create the local answer, and attach the incoming media track | mirrored |
| `updateVideoResolution()` | method | refresh metadata when the incoming video size changes | mirrored in repo metadata refresh behavior |
| `getVideoSize()` | method | return logical RGB frame size as half of the composite width | mirrored implicitly during composite split |
| `toggle()` | method | pause or resume the HTML video element | demo-only UI behavior |
| `toggleAudio()` | method | mute or unmute the HTML video element | demo-only UI behavior |
| `updateIntrinsicMatrix(intrMat)` | method | replace the stored intrinsic matrix | demo-local helper; repo computes typed intrinsics instead |
| `processIntrMat(origIntrMatElements, origVideoSize)` | method | build a display-space intrinsic matrix from metadata and current video resolution | repo parses typed intrinsics and retains metadata separately |
| `processMetadata(metadata)` | method | parse `originalSize`, compute intrinsics from `K`, and notify listeners | mirrored by `Record3DWiFiMetadata.from_api_payload()` |

### Wi-Fi Modalities And Format

| Modality / protocol detail | Official Wi-Fi demo surface | Repo normalization |
| --- | --- | --- |
| RGB | yes, in the right half of the composite frame | `FramePacket.rgb` |
| Depth | yes, HSV-encoded in the left half of the composite frame | decoded into `FramePacket.depth` |
| Intrinsics | yes, via metadata key `K` | `FramePacket.intrinsics` when parsing succeeds |
| Original source size | yes, via metadata key `originalSize` | preserved in metadata-derived fields |
| Depth range | yes, documented by the Wi-Fi README as `0` to `3` meters | `depth_max_meters`, default `3.0` when no override key is present |
| Camera pose | no public Wi-Fi demo surface | unavailable |
| Confidence | no public Wi-Fi demo surface | unavailable |
| IMU | no public Wi-Fi demo surface | unavailable |
| Audio in live stream | no, per the Wi-Fi README | ignored |
| Single-receiver limit | yes, one Wi-Fi peer at a time | surfaced as a connection error |

The official Wi-Fi README also documents the following operational constraints:

- the phone and receiver must be on the same Wi-Fi network
- the stream quality and resolution degrade with bandwidth
- Wi-Fi is lower fidelity than USB and is not recommended when accurate depth is required
- Wi-Fi Streaming and RGBD mp4 export use the same composite RGBD format

## Repo Mapping

| Transport | Repo adapter | Normalized frame surface | Current gaps |
| --- | --- | --- | --- |
| USB | [record3d.py](./record3d.py) | `rgb`, `depth`, `confidence`, `intrinsics`, `pose`, `metadata["device_type"]` | reserved misc buffer not surfaced |
| Wi-Fi Preview | [wifi_signaling.py](./wifi_signaling.py), [wifi_receiver.py](./wifi_receiver.py), and [wifi_packets.py](./wifi_packets.py) | `rgb`, decoded `depth`, optional `intrinsics`, raw metadata | no pose, no confidence, no IMU |

## Sources

- Official Record3D USB library README: [record3d README](https://github.com/marek-simonik/record3d/blob/master/README.md)
- Official Python bindings: [PythonBindings.cpp](https://github.com/marek-simonik/record3d/blob/master/python-bindings/src/PythonBindings.cpp)
- Official simple Wi-Fi demo README: [record3d-simple-wifi-streaming-demo](https://github.com/marek-simonik/record3d-simple-wifi-streaming-demo)
- Official Wi-Fi signaling / metadata demo: [SignalingClient.js](https://github.com/marek-simonik/record3d-wifi-streaming-and-rgbd-mp4-3d-video-demo/blob/master/js/app/video-sources/SignalingClient.js)
- Official Wi-Fi RGBD video handling demo: [WiFiStreamedVideoSource.js](https://github.com/marek-simonik/record3d-wifi-streaming-and-rgbd-mp4-3d-video-demo/blob/master/js/app/video-sources/WiFiStreamedVideoSource.js)
