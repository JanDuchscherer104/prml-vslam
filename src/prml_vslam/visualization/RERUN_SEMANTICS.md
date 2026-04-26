# Rerun Semantics

Use this document when changing the repo-owned Rerun scene tree, frame
conventions, or logging helpers.

For normative package requirements, read [`REQUIREMENTS.md`](./REQUIREMENTS.md)
first. This file is explanatory rather than authoritative.

## Rerun Mental Model

Treat the integration as four separate concerns:

1. Recording and sinks
   - Create one explicit `rr.RecordingStream` per pipeline run.
   - Attach one or more sinks to that stream.
   - Use one recording id per run so live viewing and exported `.rrd` files are
     different views of the same event stream.
2. Entity tree
   - Every payload belongs to one entity path such as
     `world/keyframes/points/000123/points`.
   - Transforms compose along the entity tree.
3. Timelines
   - Use one integer sequence timeline for frame/keyframe order.
   - Add a timestamp timeline only when capture or wall-clock time matters.
4. Blueprint
   - Blueprints describe viewer layout only.
   - They do not change the recorded data model.

## APIs We Actively Use

| API | Current meaning in this repo |
| --- | --- |
| `rr.RecordingStream` | One explicit recording per run. |
| `rr.GrpcSink`, `rr.FileSink`, `set_sinks` | Live streaming plus durable `.rrd` export from the same stream. |
| `rr.log` | Primary logging entry point for entity-path-based data. |
| `rr.set_time` | Frame/keyframe timeline control. |
| `rr.ViewCoordinates` | Explicit root-world and camera basis declarations when needed. |
| `rr.Transform3D` | Repo poses and explicit transform ownership. |
| `rr.Pinhole` | Intrinsics, frusta, and camera coordinate semantics. |
| `rr.Image` | Actual RGB or explicit diagnostic previews. |
| `rr.DepthImage` | Metric depth rasters back-projected through `Pinhole`. |
| `rr.Points3D` | Camera-local pointmaps or world-space clouds. |
| `rr.LineStrips3D` | Trajectory polylines. |
| `rr.Transform3D` under `.../trajectory/.../poses/<id>` | Optional visible per-pose SE3 trajectory axes when `trajectory_pose_axis_length > 0`. |
| `rr.Clear` | Sliding-window frusta cleanup without clearing keyed point history. |
| `rr.blueprint.Spatial3DView`, `rr.blueprint.Spatial2DView` | Stable 3D + 2D default layout. |

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
- `rr.Pinhole.camera_xyz = rr.ViewCoordinates.RDF` matches the pinhole
  projection convention and the ViSTA camera basis.
- `rr.Pinhole.resolution` is `[width, height]`, not `[height, width]`.
- `rr.DepthImage(..., meter=...)` needs the physical scale of the stored depth
  units.
- Rerun 0.24 does not support left-handed coordinate systems.

### The One Transform Rule

If the repo pose is `T_world_camera`, then the logged Rerun transform must
describe the entity-to-parent mapping, not the inverse. In practice:

- use default semantics consistently, or
- use explicit `ParentFromChild` when logging repo poses.

Do not pass a repo `T_world_camera` matrix together with
`rr.TransformRelation.ChildFromParent` unless you invert the transform first.

## Canonical Entity Layout

The current repo-owned scene tree should converge on the following shape:

```text
world
world/reference/trajectory/ground_truth/aligned
                                         LineStrips3D(reference trajectory)
world/reference/points/tango_area_learning/aligned/...
                                         Points3D(reference cloud)

world/live/source/rgb                   Image(source_rgb)
world/live/tracking/camera              Transform3D(T_world_camera_tracking, axis_length=0)

world/live/model                        Transform3D(T_world_camera_live, axis_length=0)
world/live/model/diag/rgb               Image(rgb_live_model_raster)        # 2D-only view surface
world/live/model/camera/image           Pinhole(K_live, resolution, camera_xyz=RDF)
world/live/model/camera/image           Image(rgb_live_camera_surface)
world/live/model/camera/image/depth     DepthImage(depth_live_m, meter=1.0)
world/live/model/diag/preview           Image(debug_preview_live)           # only when enabled
world/live/model/points                 Points3D(pointmap_xyz_camera_live)  # latest/debug surface

world/keyframes/cameras/000000          Transform3D(T_world_camera_keyframe, axis_length=0)
world/keyframes/cameras/000000/image    Pinhole(K_keyframe, resolution, camera_xyz=RDF)
world/keyframes/cameras/000000/image    Image(rgb_keyframe)
world/keyframes/cameras/000000/image/depth  DepthImage(depth_keyframe_m, meter=1.0)
world/keyframes/cameras/000000/diag/preview  Image(debug_preview_keyframe)
world/keyframes/points/000000           Transform3D(T_world_camera_keyframe, axis_length=0)
world/keyframes/points/000000/points    Points3D(pointmap_xyz_camera_keyframe)

world/slam/vista_slam_world/trajectory/raw
world/slam/vista_slam_world/trajectory/raw/poses/000000
                                         Transform3D(T_world_camera_pose, axis_length=configured)
                                         # only when trajectory_pose_axis_length > 0
world/global_dense_points               Points3D(world-space fused cloud)
```

Important consequences:

- `world/live/model/diag/rgb` is a dedicated 2D-only model RGB surface.
- `world/live/model/camera/image` is the 3D camera-image entity and should only
  receive image/depth payloads when a coherent `Pinhole` is also available.
- `Pinhole` and the image it describes live on the same camera-image entity.
- `DepthImage` lives under that same camera-image entity so Rerun can
  back-project it through the camera model.
- Camera-local pointmaps stay camera-local and inherit world placement from the
  posed parent entity.
- `world/live/model/points` is mutable latest/debug geometry.
- `world/keyframes/points/<id>/points` is the persistent keyed-history map
  surface and should be the default 3D geometry in the viewer.
- `world/keyframes/cameras/<id>` is a frustum/history surface that may be
  cleared once it falls outside the configured sliding window.
- `world/slam/vista_slam_world/trajectory/raw` and its pose children must never
  be cleared by frusta eviction.
- The root `world` entity declares the explicit viewer world basis and keeps the
  only intentionally visible axes marker at the origin.
- The default 3D blueprint uses a narrow allow-list for aligned references,
  reconstruction/alignment/overlay branches, live pose branches, keyed frusta,
  keyed point clouds, and SLAM branches. It does not broadly include raster
  parents and then hide image/depth children with negative filters.
- Source-native references remain logged for provenance, but the default 3D
  view shows only aligned reference branches.

## Current Implementation

The current implementation remains intentionally thin:

- [`rerun.py`](./rerun.py) creates recordings, attaches sinks, logs transforms,
  pinholes, RGB images, depth images, `Points3D`, `LineStrips3D`, and preserves
  native `.rrd` artifacts.
- [`../pipeline/sinks/rerun.py`](../pipeline/sinks/rerun.py) owns the
  repo-managed recording stream and event-driven sink surface.
- [`../pipeline/sinks/rerun_policy.py`](../pipeline/sinks/rerun_policy.py)
  translates pipeline events into entity-path logging policy.
- [`../methods/vista/session.py`](../methods/vista/session.py) converts
  upstream ViSTA payloads into repo-owned live telemetry.

Current limitations:

- Offline runs still preserve upstream visualization artifacts instead of
  synthesizing a repo-owned offline `.rrd`.
- The repo-owned stream does not yet log a world-space dense cloud separate
  from per-keyframe pointmaps.
- The recording is optimized for keyed-history-first viewing rather than for a
  full multi-surface operator UI.

## Current And Future Modalities

Current repo-owned export surfaces:

- aligned reference clouds from benchmark inputs
- source RGB observations
- live tracking and live model transforms
- model-raster RGB camera images
- metric `DepthImage` payloads
- keyed pointmaps as `Points3D`
- diagnostic preview images
- trajectory polylines plus optional per-pose `Transform3D` axis children
- live gRPC streaming and repo-owned `.rrd` export for streaming runs
- preserved native upstream `.rrd` files when present

Still missing or future-facing:

- a world-space dense reconstruction layer separate from camera-local pointmaps
- BEV or operator-facing top-down views
- explicit sparse-vs-dense reconstruction layers
