# Visualization

This package owns viewer/export policy plus the repo-owned Rerun integration
layer for PRML VSLAM.

It does not own Streamlit widgets, pipeline planning, or SLAM math. Rerun
recordings are viewer artifacts only. TUM trajectories, PLY clouds, manifests,
and stage summaries remain the scientific and provenance source of truth.

## Package Surface

- [`contracts.py`](./contracts.py)
  - `VisualizationConfig`: per-run viewer policy
  - `VisualizationArtifacts`: preserved native viewer artifacts plus repo-owned
    `.rrd` outputs
- [`rerun.py`](./rerun.py)
  - thin wrappers around the pinned `rerun-sdk==0.24.1` API
- [`../pipeline/streaming.py`](../pipeline/streaming.py)
  - viewer-specific pose adaptation hooks
- [`../pipeline/streaming_coordinator.py`](../pipeline/streaming_coordinator.py)
  - live logging call sites and entity-path policy
- [`../methods/vista/adapter.py`](../methods/vista/adapter.py)
  - conversion of upstream ViSTA payloads into repo-owned telemetry

## Quick Start

Install the optional Rerun dependency set:

```bash
uv sync --extra vista
```

Start the viewer with the committed blueprint:

```bash
uv run --extra vista rerun \
  .configs/visualization/vista_blueprint.rbl \
  --serve-web
```

When using the web viewer, open:

```text
http://127.0.0.1:9090/?url=rerun%2Bhttp%3A%2F%2F127.0.0.1%3A9876%2Fproxy
```

Enable live streaming and/or repo-owned `.rrd` export in a run request:

```toml
[visualization]
connect_live_viewer = true
export_viewer_rrd = true
```

Inspect a persisted repo-owned recording:

```bash
uv run rerun \
  .artifacts/<run_id>/visualization/viewer_recording.rrd \
  .configs/visualization/vista_blueprint.rbl
```

`connect_live_viewer` and `export_viewer_rrd` can be enabled together. The
streaming runner attaches both sinks to the same explicit recording stream.

## Primary References

- Rerun Python API index:
  [ref.rerun.io/docs/python/stable/common/](https://ref.rerun.io/docs/python/stable/common/)
- Initialization, `RecordingStream`, sinks, and `set_time`:
  [ref.rerun.io/docs/python/stable/common/initialization_functions/](https://ref.rerun.io/docs/python/stable/common/initialization_functions/)
- `rr.log` and entity-path semantics:
  [ref.rerun.io/docs/python/stable/common/logging_functions/](https://ref.rerun.io/docs/python/stable/common/logging_functions/)
- Archetypes such as `Transform3D`, `Pinhole`, `Image`, `DepthImage`,
  `Points3D`, and `ViewCoordinates`:
  [ref.rerun.io/docs/python/stable/common/archetypes/](https://ref.rerun.io/docs/python/stable/common/archetypes/)
- Blueprint APIs such as `Spatial3DView` and `Spatial2DView`:
  [ref.rerun.io/docs/python/stable/common/blueprint_apis/](https://ref.rerun.io/docs/python/stable/common/blueprint_apis/)
- Repo pin:
  [`../../../pyproject.toml`](../../../pyproject.toml)

This README assumes the repo pin `rerun-sdk==0.24.1`, not an arbitrary future
Rerun release.

## Rerun Mental Model

Rerun is easiest to integrate when you treat it as four separate concerns:

1. Recording and sinks
   - Create one explicit `rr.RecordingStream` per pipeline run.
   - Attach one or more sinks to that stream:
     - live viewer via `rr.GrpcSink`
     - persisted archive via `rr.FileSink`
   - Use one recording id per run so live viewing and exported `.rrd` files are
     different views of the same event stream.

2. Entity tree
   - Every logged payload belongs to one entity path such as
     `world/est/pointmaps/cam_000123/points`.
   - Transforms compose along the entity tree.
   - If a point cloud is already in camera coordinates, log it under the camera
     entity and let the parent transform place it in world coordinates.

3. Timelines
   - Use one integer timeline for keyframe order and optionally a timestamp
     timeline for wall-clock or capture time.
   - In `rerun-sdk==0.24.1`, use `rr.set_time("timeline", sequence=...)`.
     `rr.set_time_sequence(...)` is deprecated.

4. Blueprint
   - Blueprints describe viewer layout only.
   - They do not change the recorded data model.
   - Use them for stable 3D + 2D default views, not for encoding scientific
     semantics.

## Rerun APIs We Need

| API | Current use | What it should mean in this repo |
| --- | --- | --- |
| `rr.RecordingStream` | yes | One explicit recording per run. |
| `rr.GrpcSink`, `rr.FileSink`, `set_sinks` | yes | Live streaming plus durable `.rrd` export from the same stream. |
| `rr.log` | yes | Primary logging entry point for entity-path-based data. |
| `rr.set_time` | yes | Keyframe timeline and optional timestamp timeline. |
| `rr.ViewCoordinates` | optional | Use only when a workflow needs an explicit root-world convention; the ViSTA-aligned path keeps upstream-native world semantics. |
| `rr.Transform3D` | yes | Log repo poses with the correct relation semantics for `T_world_camera`. |
| `rr.Pinhole` | yes | Log intrinsics, camera frusta, and camera coordinate semantics. |
| `rr.Image` | yes | Log actual RGB or explicit diagnostic previews. |
| `rr.DepthImage` | yes | Log metric depth rasters and let Rerun back-project them through `Pinhole`. |
| `rr.Points3D` | yes | Log camera-local pointmaps or world-space clouds. |
| `rr.LineStrips3D` | not yet | Log explicit trajectory lines when needed. |
| `rr.blueprint.Spatial3DView`, `rr.blueprint.Spatial2DView` | yes | Give runs a stable 3D scene and 2D image/depth view. |
| `rr.Clear` | future | Trim stale camera entities when showing sliding windows. |

## Frame Conventions

### Repo Conventions

- The canonical repo camera pose convention is world <- camera
  (`T_world_camera`).
- [`../interfaces/transforms.py`](../interfaces/transforms.py) stores that as a
  `FrameTransform` whose `target_frame` is the parent/world frame and whose
  `source_frame` is the camera frame.
- [`../interfaces/camera.py`](../interfaces/camera.py) stores pinhole
  intrinsics as a row-major matrix:

```text
[ fx   0  cx ]
[  0  fy  cy ]
[  0   0   1 ]
```

### Rerun Conventions That Matter Here

- `rr.ViewCoordinates` declares how a space should be interpreted.
- `rr.Pinhole.image_from_camera` assumes camera image axes
  `X = Right`, `Y = Down`, `Z = Forward`.
- `rr.Pinhole.camera_xyz = rr.ViewCoordinates.RDF` is the recommended camera
  convention and matches the pinhole projection convention.
- `rr.Pinhole.resolution` is `[width, height]`, not `[height, width]`.
- `rr.DepthImage(..., meter=...)` needs the physical scale of the stored depth
  units:
  - if the depth array is already in meters, use `meter = 1.0`
  - if the depth array is millimeters in `uint16`, use `meter = 1000.0`
- Rerun 0.24 does not support left-handed coordinate systems.

### The One Transform Rule

If the repo pose is `T_world_camera`, then the logged Rerun transform must
describe the entity-to-parent mapping, not the inverse. In Rerun terms that
means default semantics or explicit `ParentFromChild`.

Do not pass a repo `T_world_camera` matrix together with
`rr.TransformRelation.ChildFromParent` unless you invert the transform first.

## Canonical Entity Layout

The repo should converge on the following scene tree:

```text
world
world/reference/aligned_gt_world/...    Points3D in world coordinates

world/live/camera                       Transform3D(T_world_camera_live)
world/live/camera/cam                   Pinhole(K_live, resolution, camera_xyz=RDF)
world/live/camera/cam                   Image(rgb_live)
world/live/camera/cam/depth             DepthImage(depth_live_m, meter=1.0)
world/live/camera/preview               Image(debug_preview_live)
world/live/pointmap                     Transform3D(T_world_camera_live, axis_length=0)
world/live/pointmap/points              Points3D(pointmap_xyz_camera_live)

world/est/cameras/cam_000000            Transform3D(T_world_camera_keyframe)
world/est/cameras/cam_000000/cam        Pinhole(K_keyframe, resolution, camera_xyz=RDF)
world/est/cameras/cam_000000/cam        Image(rgb_keyframe)
world/est/cameras/cam_000000/cam/depth  DepthImage(depth_keyframe_m, meter=1.0)
world/est/cameras/cam_000000/preview    Image(debug_preview_keyframe)
world/est/pointmaps/cam_000000          Transform3D(T_world_camera_keyframe, axis_length=0)
world/est/pointmaps/cam_000000/points   Points3D(pointmap_xyz_camera_keyframe)

world/est/trajectory                    LineStrips3D(world positions)
world/est/global_dense_points           Points3D(world-space fused cloud)
```

Important consequences:

- `Pinhole` and the image it describes should live on the same camera entity.
- `DepthImage` should live under that camera entity so Rerun can back-project it
  through the camera model.
- Camera-local pointmaps should live under a separate posed pointmap branch when
  the user needs to hide camera frusta and camera frames without hiding the
  points.
- Pointmap transform branches should log `axis_length=0` so they do not add
  another visible frame to the 3D scene.

## Modalities We Want To Export

### Current repo-owned export

- aligned reference clouds from benchmark inputs
- live camera transform
- keyframe transforms
- camera intrinsics and frusta via `rr.Pinhole`
- actual RGB camera images via `rr.Image`
- metric depth via `rr.DepthImage`
- keyframe pointmaps via `rr.Points3D`
- diagnostic preview images separate from the camera image entity
- live gRPC streaming and repo-owned `.rrd` export for streaming runs
- preserved native upstream `.rrd` files when present

### Missing but required for a correct camera visualization

- explicit trajectory visualization
- a clear split between camera-local pointmaps and world-space fused clouds

### Future or optional surfaces

- global dense reconstruction in world coordinates
- BEV or operator-facing top-down summaries from the same scene graph
- explicit sparse-vs-dense reconstruction layers

## Current State In This Repository

The current implementation is intentionally thin but incomplete:

- [`rerun.py`](./rerun.py) creates recordings, attaches sinks, logs a world
  `ViewCoordinates`, logs transforms, pinhole cameras, RGB images, depth
  images, and `Points3D`, and preserves native `.rrd` artifacts.
- [`../pipeline/streaming_coordinator.py`](../pipeline/streaming_coordinator.py)
  logs reference clouds, the live camera pose, per-keyframe poses, camera
  intrinsics, actual camera images, diagnostic previews, depth images, and
  pointmaps.
- Offline runs currently preserve native upstream visualization artifacts but do
  not synthesize a repo-owned offline `.rrd`.

The current repo-owned stream does not yet log:

- trajectory polylines
- a world-space dense cloud separate from per-keyframe pointmaps

## Comparison With Upstream ViSTA

The relevant upstream references are:

- [`../../../external/vista-slam/run.py`](../../../external/vista-slam/run.py)
- [`../../../external/vista-slam/run_live.py`](../../../external/vista-slam/run_live.py)
- [`../../../external/vista-slam/vista_slam/slam.py`](../../../external/vista-slam/vista_slam/slam.py)

Upstream ViSTA's working Rerun path does four important things:

1. It logs the camera pose directly on `world/est/<topic>` with the default
   `Transform3D` relation semantics.
2. It logs `rr.Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)` on the camera
   entity `world/est/<topic>/cam`.
3. It logs the image on that same `.../cam` entity.
4. It logs a point cloud generated from `compute_local_pointclouds(depth, intri)`
   under `world/est/<topic>/points`.

That means upstream treats the point cloud as camera-local geometry and relies
on the camera transform to place it in the scene.

## Findings From Comparing Our Wrapper Against Upstream

### 1. The transform relation must match the canonical repo pose direction

The repo stores camera poses as `T_world_camera`, so the Rerun helper must log
them with parent-from-child semantics.

The repo-owned path now uses explicit `ParentFromChild` semantics and keeps the
same world/frame orientation as upstream ViSTA instead of remapping ViSTA into a
repo-specific Y-up viewer world.

If future pointmaps look mirrored or displaced again, inspect transform
relations before touching basis-conversion code.

### 2. Camera-complete entities require `Pinhole`, RGB, and `DepthImage`

The repo-owned streaming path now logs `Pinhole`, actual RGB, and metric depth
under camera entities. Keep those payloads synchronized and raster-consistent.

### 3. `preview_rgb` is diagnostic preview only

Upstream `get_pointmap_vis(...)` in
[`../../../external/vista-slam/vista_slam/slam.py`](../../../external/vista-slam/vista_slam/slam.py)
returns:

- a pseudo-color visualization produced from normalized XYZ values
- the actual camera-local point cloud

The repo now keeps that pseudo-colored payload on separate `.../preview`
entities. It is not the camera image entity and it is not the depth entity.

### 4. ViSTA live payloads are in ViSTA resolution, not capture resolution

The streaming adapter resizes input frames to `224x224` before sending them to
ViSTA.

`Pinhole`, `Image`, and `DepthImage` logged from live ViSTA outputs must use
intrinsics and resolution consistent with that raster. Do not mix
original-capture intrinsics with ViSTA-resized pointmaps.

### 5. Keep upstream ViSTA world semantics unless there is a method-agnostic normalization layer

The current live viewer path now keeps ViSTA's native world orientation instead
of applying a viewer-only basis conversion. If the repo later wants one shared
cross-method viewer world, that normalization should live in an explicit,
method-agnostic alignment layer rather than in the ViSTA viewer hook alone.

## Recommended Integration Pattern

For a correct repo-owned camera export, the logging sequence should look like
this:

```python
import rerun as rr

recording = rr.RecordingStream(application_id="prml-vslam", recording_id=run_id)
recording.set_sinks(rr.GrpcSink(grpc_url), rr.FileSink(str(viewer_rrd_path)))
recording.send_blueprint(blueprint)

recording.set_time("keyframe", sequence=keyframe_index)

recording.log(
    f"world/est/cameras/cam_{keyframe_index:06d}",
    rr.Transform3D(
        translation=T_world_camera[:3, 3],
        mat3x3=T_world_camera[:3, :3],
        relation=rr.TransformRelation.ParentFromChild,
    ),
)

recording.log(
    f"world/est/cameras/cam_{keyframe_index:06d}/cam",
    rr.Pinhole(
        image_from_camera=K,
        resolution=[width, height],
        camera_xyz=rr.ViewCoordinates.RDF,
    ),
)

recording.log(
    f"world/est/pointmaps/cam_{keyframe_index:06d}",
    rr.Transform3D(
        translation=T_world_camera[:3, 3],
        mat3x3=T_world_camera[:3, :3],
        relation=rr.TransformRelation.ParentFromChild,
        axis_length=0.0,
    ),
)
recording.log(f"world/est/cameras/cam_{keyframe_index:06d}/cam", rr.Image(rgb))
recording.log(f"world/est/cameras/cam_{keyframe_index:06d}/cam/depth", rr.DepthImage(depth_m, meter=1.0))
recording.log(f"world/est/pointmaps/cam_{keyframe_index:06d}/points", rr.Points3D(points_xyz_camera, colors=colors))
```

If the point cloud is already in world coordinates, log it somewhere under
`world/...` without the camera parent transform.

## Remaining Follow-Ups

1. Add explicit trajectory overlays.
2. Add a world-space fused dense cloud layer separate from camera-local
   pointmaps.
3. Add repo-owned offline `.rrd` synthesis if offline viewer parity becomes a
   priority.
