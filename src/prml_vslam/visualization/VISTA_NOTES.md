# ViSTA Notes

Use this document when comparing the repo-owned visualization path with
upstream ViSTA-SLAM or when reasoning about ViSTA-specific live payload
semantics.

For package-level invariants, read [`REQUIREMENTS.md`](./REQUIREMENTS.md). For
the current repo-owned scene tree, read [`RERUN_SEMANTICS.md`](./RERUN_SEMANTICS.md).

## Upstream Reference Surfaces

The main upstream comparison points are:

- [`../../../external/vista-slam/run.py`](../../../external/vista-slam/run.py)
- [`../../../external/vista-slam/run_live.py`](../../../external/vista-slam/run_live.py)
- [`../../../external/vista-slam/vista_slam/slam.py`](../../../external/vista-slam/vista_slam/slam.py)

Upstream ViSTA’s working Rerun path does five important things:

1. Logs a neutral `/world` root.
2. Logs the camera pose on `world/est/<topic>`.
3. Logs `rr.Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)` on
   `world/est/<topic>/cam`.
4. Logs the image on that same `.../cam` entity.
5. Logs camera-local point clouds under `world/est/<topic>/points`.

That means upstream treats the point cloud as camera-local geometry and relies
on the camera transform to place it in the scene.

## Current Repo-Specific Findings

### Transform Relation Must Match Repo Pose Direction

The repo stores camera poses as `T_world_camera`, so the helper path must log
them with parent-from-child semantics. The repo-owned path keeps ViSTA’s native
world semantics instead of remapping ViSTA into a repo-specific viewer basis.

### Camera-Complete 3D Entities Need A Pinhole

The 3D camera-image entity is only coherent when `Pinhole`, RGB, and depth all
refer to the same raster. The repo-owned path now keeps a separate
`world/live/model/diag/rgb` surface for the always-visible 2D model RGB view
and reserves `world/live/model/camera/image` for coherent 3D camera bundles.

### `preview_rgb` Is Diagnostic Preview Only

Upstream `get_pointmap_vis(...)` returns:

- a pseudo-color visualization produced from normalized XYZ values
- the actual camera-local point cloud

The repo keeps that pseudo-colored payload on `.../diag/preview`. It is not
the camera image entity and it is not the depth entity.

### ViSTA Live Payloads Use The ViSTA Raster

The streaming adapter resizes input frames to `224x224` before sending them to
ViSTA. `Pinhole`, `Image`, `DepthImage`, and point geometry logged from live
ViSTA outputs must stay consistent with that raster.

### Keep Upstream ViSTA World Semantics Unless A Shared Alignment Layer Exists

The current live viewer path keeps ViSTA’s native world orientation instead of
applying a viewer-only basis conversion. If the repo later wants one shared
cross-method viewer world, that normalization should live in an explicit,
method-agnostic alignment layer rather than in the ViSTA viewer hook alone.

The current repo-owned path makes that unchanged world explicit by logging
`world` as:

- a neutral `Transform3D(axis_length=1.0)`
- a static `ViewCoordinates.RDF`

### The Viewer Intentionally Shows Multiple Raster Surfaces

The live sink keeps these surfaces distinct:

- `world/live/source/rgb`: original source-frame raster from ingress
- `world/live/model/diag/rgb`: model-raster RGB shown in the dedicated 2D tab
- `world/live/model/camera/image`, `.../depth`, `.../points`, and
  `.../diag/preview`: coherent 3D camera bundle on the ViSTA model raster

This is an intentional divergence from a naive “one camera image everywhere”
mental model.

### Live Pointmaps And Exported Dense Clouds Are Different Products

The current ViSTA integration exposes two separate geometry surfaces:

- live/session readback produces scaled camera-local pointmaps that remain
  under posed parent entities
- native export produces `pointcloud.ply`, a fused world-space dense cloud

They should only be compared after composing the live pointmap through its
parent pose into world coordinates.

## Current Discrepancy Matrix

| Area | Status | Classification | Notes |
| --- | --- | --- | --- |
| Upstream crop/resize preprocessing parity | Confirmed | intentional difference | Wrapper preserves upstream ingest semantics. |
| Source RGB vs ViSTA model raster | Different surfaces | expected | `world/live/source/rgb` is source-frame only; model-raster payloads stay separate. |
| Live pointmap vs exported `pointcloud.ply` | Different products | expected | Live path is scaled camera-local; export path is fused world-space geometry. |
| Repo entity layout vs upstream `world/est/cam_n` layout | Different layout | intentional difference | Path parity is not required if composed world placement is equivalent. |
| ViSTA-native RDF-like world semantics in repo viewer | Confirmed | expected | Repo path preserves ViSTA-native semantics instead of normalizing to world-up. |
| Root world declaration | Explicit | intentional difference | Repo path now logs a visible root-world marker via `Transform3D(axis_length=1.0)`. |
| Keyed point persistence vs frusta eviction | Guarded | expected | Points persist; stale keyed camera branches may be cleared. |
| Offline preserved native visualization vs repo-owned live `.rrd` | Different product surface | intentional difference | Offline repo-owned `.rrd` synthesis remains out of scope. |

## Recommended Integration Pattern

For a correct repo-owned camera export, the logging sequence should look like
this:

```python
import rerun as rr

recording = rr.RecordingStream(application_id="prml-vslam", recording_id=run_id)
recording.set_sinks(rr.GrpcSink(grpc_url), rr.FileSink(str(viewer_rrd_path)))
recording.send_blueprint(blueprint)
recording.log("world", rr.Transform3D(axis_length=1.0), static=True)
recording.log("world", rr.ViewCoordinates.RDF, static=True)

recording.log(
    f"world/keyframes/cameras/{keyframe_index:06d}",
    rr.Transform3D(
        translation=T_world_camera[:3, 3],
        mat3x3=T_world_camera[:3, :3],
        relation=rr.TransformRelation.ParentFromChild,
        axis_length=0.0,
    ),
)
recording.log(
    f"world/keyframes/cameras/{keyframe_index:06d}/image",
    rr.Pinhole(
        image_from_camera=K,
        resolution=[width, height],
        camera_xyz=rr.ViewCoordinates.RDF,
    ),
)
recording.log(f"world/keyframes/cameras/{keyframe_index:06d}/image", rr.Image(rgb))
recording.log(
    f"world/keyframes/cameras/{keyframe_index:06d}/image/depth",
    rr.DepthImage(depth_m, meter=1.0),
)
recording.log(
    f"world/keyframes/points/{keyframe_index:06d}",
    rr.Transform3D(
        translation=T_world_camera[:3, 3],
        mat3x3=T_world_camera[:3, :3],
        relation=rr.TransformRelation.ParentFromChild,
        axis_length=0.0,
    ),
)
recording.log(
    f"world/keyframes/points/{keyframe_index:06d}/points",
    rr.Points3D(points_xyz_camera, colors=colors),
)
```

If the point cloud is already in world coordinates, log it directly under a
world-space entity without the camera parent transform.

## Still Useful Follow-Ups

- Add an explicit world-space dense cloud layer separate from camera-local
  pointmaps.
- Add repo-owned offline `.rrd` synthesis if offline viewer parity becomes a
  priority.
- Keep the ViSTA comparison notes current whenever the repo changes its viewer
  world policy or live camera/image entity layout.
