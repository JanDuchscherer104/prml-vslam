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

## Stage Integration

- Config: [`stage/config.py`](./stage/config.py) defines
  `GroundAlignmentStageConfig` for the `gravity.align` stage. It declares the
  ground-alignment output path, checks that the selected SLAM backend can emit
  point-cloud artifacts, and builds the runtime input.
- Input DTO: [`stage/contracts.py`](./stage/contracts.py) defines
  `GroundAlignmentStageInput` with `GroundAlignmentConfig`, run artifact paths,
  and normalized `SlamArtifacts`.
- Runtime: [`stage/runtime.py`](./stage/runtime.py) adapts
  `GroundAlignmentService` into the pipeline `OfflineStageRuntime` contract and
  returns `GroundAlignmentMetadata` inside `StageResult`.
- I/O: input is normalized SLAM trajectory/point-cloud artifacts; output is the
  ground-alignment metadata artifact declared by pipeline run paths.

Alignment has no streaming hot-path protocol and no Rerun SDK dependency.
Visualization consumers should use the metadata artifact or neutral
visualization items produced elsewhere.
