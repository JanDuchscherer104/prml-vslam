# Rendering

This package generates the *image* side of an image-quality comparison from
VSLAM geometry. It is the producer that pairs with the pure metric module in
[`../eval/image_metrics.py`](../eval/image_metrics.py).

## Scope

`PointCloudRenderer` ([`point_cloud_renderer.py`](./point_cloud_renderer.py))
rasterizes a colored world-space point cloud (for example a SLAM dense cloud,
`slam/dense_points.ply`) from a camera pose and intrinsics into a
`RenderedView`: an RGB image, metric depth, and a boolean coverage mask.

It uses Open3D's GL-free tensor projection
(`open3d.t.geometry.PointCloud.project_to_rgbd_image`), so it runs headless (WSL,
CI) with no OpenGL/Filament context. Sparse clouds leave holes; the coverage mask
lets `compute_image_metrics(reference, rendered, mask=view.coverage)` score only
the pixels a point actually filled. An optional `dilation_px` performs a coarse
morphological hole-fill.

## Conventions

- Poses are `world <- camera_rdf` (`FrameTransform`), matching the rest of the
  repo. The Open3D extrinsic is `inv(pose.as_matrix())`, exactly as in
  `reconstruction/open3d_tsdf.py`.
- The renderer is **frame-agnostic**: it renders whatever world frame the cloud
  and poses already share. Aligning an estimate cloud into a ground-truth frame
  (e.g. via the trajectory Sim(3) alignment) is the caller's responsibility, not
  the renderer's.

## Boundary

This package only produces images. It does not own SLAM, reconstruction, the
image metrics themselves, or pipeline-stage policy. The `prml-vslam render-cloud`
CLI renders frames along a trajectory and can optionally score them against a
reference image directory via the eval image-quality service.
