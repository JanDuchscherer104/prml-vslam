# Python SDK Patterns

Use this file for behavior-level guidance when integrating Rerun into Python
SLAM, RGB-D, or reconstruction code.

## Recording And Sinks

- Create one explicit `RecordingStream` per pipeline run.
- Use a stable `recording_id` so live viewing and `.rrd` export describe the
  same recording.
- Attach sinks explicitly:
  - live viewer via `GrpcSink`
  - persisted archive via `FileSink`
- Treat blueprints as viewer layout only. They should not carry scientific
  semantics.

## Recommended Entity Tree

Use an entity tree that separates camera pose, camera model, 2D payloads, and
3D geometry:

```text
world
world/reference/...

world/live_camera
world/live_camera/cam
world/live_camera/cam/depth
world/live_camera/points

world/est/cam_000000
world/est/cam_000000/cam
world/est/cam_000000/cam/depth
world/est/cam_000000/points

world/est/trajectory
world/est/global_dense_points
```

Use the camera entity for pose. Use the `.../cam` entity for `Pinhole` and the
matching image payloads. Use `.../points` for point clouds.

## Root And Camera Conventions

- Declare one right-handed world convention at the scene root, typically
  `rr.ViewCoordinates.RIGHT_HAND_Y_UP`.
- Use `camera_xyz=rr.ViewCoordinates.RDF` for pinhole cameras unless a different
  camera basis is explicitly required and documented.
- Keep camera basis and world basis separate in your reasoning. They do not have
  to use the same up direction.

## Transforms

- Decide what transform you have before logging it.
- If your pose is `T_world_camera`, then the logged transform must describe the
  camera-to-parent mapping:
  - use default parent semantics consistently, or
  - use `relation=rr.TransformRelation.ParentFromChild`
- Do not log `T_world_camera` with
  `rr.TransformRelation.ChildFromParent` unless you invert the matrix first.
- If points appear mirrored, displaced, or anchored to the wrong entity, inspect
  transform relation semantics before inspecting everything else.

## Pinhole, Image, And Depth

- Log `Pinhole` on the camera image entity, not on the world root.
- `Pinhole.resolution` is `[width, height]`.
- `image_from_camera` is a row-major pinhole matrix.
- `Pinhole` and the image it describes should live on the same entity.
- If the image was cropped or resized, update intrinsics before logging.
- Use `DepthImage(..., meter=...)` for metric depth:
  - `meter=1.0` if the depth array is already meters
  - use the native scale if it is stored in millimeters or another unit
- Prefer `DepthImage` for actual depth and `Image` for actual RGB.
- Do not treat a pseudo-colored debug visualization as either raw RGB or metric
  depth.

## Camera-Local Vs World-Space Geometry

- Camera-local pointmaps belong under a posed camera entity.
- World-space fused clouds should live directly in a world-space entity.
- Do not pre-transform camera-local points into world coordinates and then also
  log them under a camera transform. That double-applies the pose.
- Do not log world-space geometry under a camera entity unless you explicitly
  want it to inherit the camera transform.

## Timelines

- Use one sequence timeline for keyframes or frames.
- Add a timestamp timeline only when real capture or wall-clock time matters.
- Keep timeline naming stable across related entities.
- If data disappears or looks desynchronized, inspect timeline mismatches before
  assuming the geometry is wrong.

## Blueprints

- Use blueprints to define the default 3D and 2D views.
- Use `Spatial3DView` for the scene root.
- Use `Spatial2DView` for image or depth inspection.
- Set the blueprint once per recording unless the workflow genuinely requires
  dynamic layout changes.

## What To Inspect First

1. Transform relation mismatch
2. Wrong world basis or camera basis assumption
3. Resized or cropped image with stale intrinsics
4. Camera-local points logged as if they were world-space points
5. World-space points logged under a camera transform
6. Debug preview mislabeled as metric depth
7. Width and height swapped in `Pinhole.resolution`
8. Wrong `DepthImage(..., meter=...)` scale
9. Timeline mismatch between transforms and payloads
