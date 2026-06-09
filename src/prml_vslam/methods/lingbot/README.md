# LingBot-Map Method Wrapper

This package owns the repo adapter for the operator-managed
`Robbyant/lingbot-map` checkout. The wrapper consumes normalized observations,
runs upstream inference, and writes repository-owned SLAM artifacts.

## Normalized Artifacts

LingBot trajectories are normalized to `T_world_camera` and written to
`slam/trajectory.tum`. Dense geometry is written to `slam/point_cloud.ply` and
returned through the shared `dense_points_ply` contract field.

The adapter intentionally does not export LingBot depth maps, point maps, or
confidence rasters as first-class artifacts. Those arrays remain upstream-native
model internals unless a later task needs them enough to justify a tested
contract. The current durable contract is the trajectory, the point cloud, and
small native metadata extras under `native/`.
