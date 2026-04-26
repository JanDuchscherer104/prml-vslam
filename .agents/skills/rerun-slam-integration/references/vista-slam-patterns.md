# ViSTA-SLAM Patterns

Use this file when you need a concrete SLAM integration reference inside this
repo.

The local ViSTA files are examples of one working integration pattern. They are
not the canonical source for Rerun semantics. Ground in official Rerun behavior
first, then compare.

## Primary Repo-Local Reference Surfaces

### `external/vista-slam/run.py`

- Purpose: offline ViSTA run with saved or live Rerun output.
- Key pattern:
  - initialize Rerun once
  - log a root `world`
  - log `Transform3D` on `world/est/<topic>`
  - log `Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)` on
    `world/est/<topic>/cam`
  - log `Image` on that same `.../cam` entity
  - log camera-local `Points3D` on `world/est/<topic>/points`
  - advance time with `rr.set_time("index", sequence=t)`
- Open when: you need the clearest local reference for an offline SLAM viewer
  tree.

### `external/vista-slam/run_live.py`

- Purpose: live camera integration for ViSTA.
- Key pattern:
  - same core entity layout as the offline path
  - live frame ingestion and repeated visualization updates
  - camera-local point clouds may be downsampled for viewer performance
- Open when: a bug only appears in the live path or performance-sensitive
  visualization is involved.

### `external/vista-slam/vista_slam/slam.py`

- Purpose: the data source for ViSTA runtime view payloads.
- Key pattern:
  - `get_view(...)` returns pose, depth, and intrinsics
  - `get_pointmap_vis(...)` returns:
    - a pseudo-colored visualization built from normalized XYZ
    - a camera-local point cloud built from `compute_local_pointclouds`
- Open when: the meaning of a ViSTA payload is unclear.

## Important ViSTA Takeaways

- Upstream ViSTA uses `camera_xyz=RDF` for the camera model.
- Upstream ViSTA groups camera transform, `Pinhole`, `Image`, and point cloud by
  camera entity.
- The point cloud logged from `get_pointmap_vis(...)` is camera-local geometry.
- The colored preview returned by `get_pointmap_vis(...)` is a diagnostic
  visualization, not raw RGB and not a metric depth image.

## Compare Against The Current PRML Wrapper

When comparing the repo-local PRML wrapper against upstream ViSTA, inspect these
files:

- `src/prml_vslam/visualization/rerun.py`
- `src/prml_vslam/pipeline/streaming.py`
- `src/prml_vslam/pipeline/streaming_coordinator.py`
- `src/prml_vslam/methods/vista/adapter.py`

Use this comparison when symptoms include:

- points landing in the wrong place
- depth previews looking cropped or semantically wrong
- pinhole or camera frustum missing from the repo-owned path
- differences between upstream ViSTA `.rrd` output and the repo-owned wrapper

## High-Value Comparison Checks

1. Compare transform relation semantics first.
   - If the repo wrapper stores `T_world_camera`, logging it as
     `ChildFromParent` is a mismatch unless the transform is inverted first.
2. Compare where points live in the entity tree.
   - Upstream ViSTA logs camera-local points under a posed camera entity.
3. Compare what image payload is being logged.
   - A pseudo-color pointmap preview should not be treated as either RGB or
     metric depth.
4. Compare raster resolution and intrinsics together.
   - Live ViSTA operates on resized imagery; `Pinhole`, `Image`, `DepthImage`,
     and point geometry must use the same raster assumptions.
5. Compare any viewer-basis adapter only once.
   - If the repo adds a basis conversion between ViSTA world and viewer world,
     it should be explicit and singular.
