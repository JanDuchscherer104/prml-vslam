# LingBot-Map Method Wrapper

This package owns the repo adapter for the operator-managed
`Robbyant/lingbot-map` checkout. The wrapper consumes normalized observations,
runs upstream inference, and writes repository-owned SLAM artifacts.

## Normalized Artifacts

LingBot trajectories are normalized to `T_world_camera` and written to
`slam/trajectory.tum`. Dense geometry is written to `slam/point_cloud.ply` and
returned through the shared `dense_points_ply` contract field.

When dense geometry is enabled, the adapter also writes processed model-raster
arrays as first-class SLAM artifacts:

- `depth_maps_npz`: `slam/depth_maps.npz`
- `point_maps_npz`: `slam/point_maps.npz`
- `point_cloud_confidences_npz`: `slam/point_cloud_confidences.npz`

Each NPZ includes frame order, timestamps, raster-space metadata, frame
semantics, confidence source, confidence threshold, point stride, and depth
filtering policy. These arrays stay in LingBot's processed raster space; they
are not resampled back to source RGB resolution.
