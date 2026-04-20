# Alignment

This package owns derived alignment logic that consumes normalized SLAM
artifacts and produces explicit, repo-owned alignment metadata.

It does not mutate backend-native outputs and it does not own benchmark
evaluation or Rerun logging. The first implementation detects a dominant ground
plane from the final SLAM point cloud and derives a viewer-scoped transform
`T_viewer_world_world`.

## Current Scope

- detect a dominant ground plane from normalized SLAM point clouds
- derive a viewer-scoped alignment transform from native `world` into
  `viewer_world`
- emit confidence, diagnostics, and finite plane-patch geometry for future
  visualization consumers

## Frame Semantics

- native backend frame: `world`
- derived viewer frame: `viewer_world`
- `T_viewer_world_world` maps points and poses from native `world` into
  `viewer_world`

Ground alignment is a viewer/interpretation boundary only. Native
`slam/trajectory.tum` and native point-cloud artifacts remain authoritative
backend outputs.
