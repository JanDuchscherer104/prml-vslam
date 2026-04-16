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
     `world/est/cam_000123/points`.
   - Transforms compose along the entity tree.
   - If a point cloud is already in camera coordinates, log it under the camera
     entity and let the parent transform place it in world coordinates.

3. Timelines
   - Use one integer timeline for keyframe order and optionally a timestamp
     timeline for wall-clock or capture time.
   - In `rerun-sdk==0.24.1`, both `rr.set_time_sequence(...)` and
     `rr.set_time("timeline", sequence=...)` exist. Prefer `set_time(...)` for
     new code.

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
| `rr.set_time` / `rr.set_time_sequence` | yes | Keyframe timeline and optional timestamp timeline. |
| `rr.ViewCoordinates` | yes | Declare the root world convention once and declare camera conventions explicitly. |
| `rr.Transform3D` | yes | Log repo poses with the correct relation semantics for `T_world_camera`. |
| `rr.Pinhole` | not yet | Log intrinsics, camera frusta, and camera coordinate semantics. |
| `rr.Image` | yes | Log actual RGB or explicit diagnostic previews. |
| `rr.DepthImage` | not yet | Log metric depth rasters and let Rerun back-project them through `Pinhole`. |
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
world                                   ViewCoordinates.RIGHT_HAND_Y_UP (static)
world/reference/aligned_gt_world/...    Points3D in world coordinates

world/live_camera                       Transform3D(T_world_camera_live)
world/live_camera/cam                   Pinhole(K_live, resolution, camera_xyz=RDF)
world/live_camera/cam                   Image(rgb_live) or diagnostic preview
world/live_camera/cam/depth             DepthImage(depth_live_m, meter=1.0)
world/live_camera/points                Points3D(pointmap_xyz_camera_live)

world/est/cam_000000                    Transform3D(T_world_camera_keyframe)
world/est/cam_000000/cam                Pinhole(K_keyframe, resolution, camera_xyz=RDF)
world/est/cam_000000/cam                Image(rgb_keyframe)
world/est/cam_000000/cam/depth          DepthImage(depth_keyframe_m, meter=1.0)
world/est/cam_000000/points             Points3D(pointmap_xyz_camera_keyframe)

world/est/trajectory                    LineStrips3D(world positions)
world/est/global_dense_points           Points3D(world-space fused cloud)
```

Important consequences:

- `Pinhole` and the image it describes should live on the same camera entity.
- `DepthImage` should live under that camera entity so Rerun can back-project it
  through the camera model.
- Camera-local pointmaps belong under the camera transform, not directly under
  `world`, unless they have already been transformed into world coordinates.

## Modalities We Want To Export

### Current repo-owned export

- aligned reference clouds from benchmark inputs
- live camera transform
- keyframe transforms
- keyframe pointmaps via `rr.Points3D`
- one preview image per keyframe
- live gRPC streaming and repo-owned `.rrd` export for streaming runs
- preserved native upstream `.rrd` files when present

### Missing but required for a correct camera visualization

- `rr.Pinhole` for every camera entity
- actual RGB keyframe images
- metric `rr.DepthImage` payloads
- explicit trajectory visualization
- a clear split between camera-local pointmaps and world-space fused clouds

### Future or optional surfaces

- global dense reconstruction in world coordinates
- BEV or operator-facing top-down summaries from the same scene graph
- explicit sparse-vs-dense reconstruction layers

## Current State In This Repository

The current implementation is intentionally thin but incomplete:

- [`rerun.py`](./rerun.py) creates recordings, attaches sinks, logs a world
  `ViewCoordinates`, logs transforms, images, and `Points3D`, and preserves
  native `.rrd` artifacts.
- [`../pipeline/streaming_coordinator.py`](../pipeline/streaming_coordinator.py)
  logs reference clouds, the live camera pose, per-keyframe poses, preview
  images, and pointmaps.
- Offline runs currently preserve native upstream visualization artifacts but do
  not synthesize a repo-owned offline `.rrd`.

The current repo-owned stream does not yet log:

- `rr.Pinhole`
- `rr.DepthImage`
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

### 1. The current transform relation is likely wrong

[`rerun.py`](./rerun.py) logs repo `FrameTransform` values with
`relation=rr.TransformRelation.ChildFromParent`.

That conflicts with repo semantics because `FrameTransform` stores
`T_world_camera`. Rerun's `ChildFromParent` means the logged matrix maps parent
space into child space. Upstream ViSTA does not set this relation at all, which
means the default `space -> parent` semantics apply and match a
camera-to-world pose.

This is the strongest candidate for the current "points do not unproject into
world coordinates correctly" symptom.

### 2. We do not currently log `Pinhole`

Without `rr.Pinhole` we lose:

- explicit camera frusta
- explicit camera coordinate semantics
- a direct visual cross-check between intrinsics, image, and pointmap
- Rerun's automatic depth-to-3D projection for `DepthImage`

Upstream ViSTA logs `Pinhole` on every camera entity. The repo wrapper should do
the same.

### 3. The current `preview_rgb` payload is not RGB and not depth

Upstream `get_pointmap_vis(...)` in
[`../../../external/vista-slam/vista_slam/slam.py`](../../../external/vista-slam/vista_slam/slam.py)
returns:

- a pseudo-color visualization produced from normalized XYZ values
- the actual camera-local point cloud

Our wrapper stores that first payload as `preview_rgb`. That means the current
viewer image is a diagnostic pointmap preview. It is not the original RGB frame
and it is not a metric depth image.

This explains why the current image payload does not behave like a true depth
view.

### 4. ViSTA live payloads are in ViSTA resolution, not capture resolution

The streaming adapter resizes input frames to `224x224` before sending them to
ViSTA.

Any future `Pinhole`, `Image`, or `DepthImage` logged from live ViSTA outputs
must use intrinsics and resolution consistent with that raster. We must not mix
original-capture intrinsics with ViSTA-resized pointmaps.

### 5. The current basis conversion must remain explicit and singular

[`../pipeline/streaming.py`](../pipeline/streaming.py) applies
`diag([1, -1, -1])` to ViSTA poses before logging them into a
`RIGHT_HAND_Y_UP` world.

That may be a valid viewer-basis adapter, but only if it is the single,
documented conversion point between ViSTA's internal world and the viewer's
world. The code and docs must treat it as an explicit boundary adapter, not an
implicit convention.

## Recommended Integration Pattern

For a correct repo-owned camera export, the logging sequence should look like
this:

```python
import rerun as rr

recording = rr.RecordingStream(application_id="prml-vslam", recording_id=run_id)
recording.set_sinks(rr.GrpcSink(grpc_url), rr.FileSink(str(viewer_rrd_path)))
recording.send_blueprint(blueprint)

recording.log("world", rr.ViewCoordinates.RIGHT_HAND_Y_UP, static=True)
recording.set_time("keyframe", sequence=keyframe_index)

recording.log(
    f"world/est/cam_{keyframe_index:06d}",
    rr.Transform3D(
        translation=T_world_camera[:3, 3],
        mat3x3=T_world_camera[:3, :3],
        relation=rr.TransformRelation.ParentFromChild,
    ),
)

recording.log(
    f"world/est/cam_{keyframe_index:06d}/cam",
    rr.Pinhole(
        image_from_camera=K,
        resolution=[width, height],
        camera_xyz=rr.ViewCoordinates.RDF,
    ),
)

recording.log(f"world/est/cam_{keyframe_index:06d}/cam", rr.Image(rgb))
recording.log(f"world/est/cam_{keyframe_index:06d}/cam/depth", rr.DepthImage(depth_m, meter=1.0))
recording.log(f"world/est/cam_{keyframe_index:06d}/points", rr.Points3D(points_xyz_camera, colors=colors))
```

If the point cloud is already in world coordinates, log it somewhere under
`world/...` without the camera parent transform.

## Short-Term Fix Checklist

1. Change repo transform logging so a repo `T_world_camera` is emitted with
   parent-from-child semantics.
2. Extend the live ViSTA update surface to carry actual intrinsics and metric
   depth, not only a pseudo-color preview plus pointmap.
3. Add `rr.Pinhole` to every logged camera entity.
4. Log true RGB and/or true `DepthImage` payloads separately from diagnostic
   previews.
5. Add one synthetic integration test that checks a known pose + depth map
   produces the expected world-space point cloud in Rerun semantics.
