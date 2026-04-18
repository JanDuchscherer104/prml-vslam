# Official Examples Map

Prefer the direct example page links below. Fall back to the official examples
index when a direct link changes:

- `https://rerun.io/examples`

If a Context7 MCP server is available, pair the direct example page with the
listed query. If not, open the example page directly and follow its `Python
source` link when you need the actual implementation.

## Depth And Pinhole

### RGBD

- Teaches: the cleanest minimal reference for `Pinhole` plus `DepthImage`,
  metric depth scaling, and a camera/image/depth entity split.
- Open when: you need a baseline for RGB-D backprojection, correct
  `resolution=[width, height]`, or simple timeline usage.
- Example page: [RGBD](https://rerun.io/examples/robotics/rgbd)
- Source code:
  [rerun/examples/python/rgbd](https://github.com/rerun-io/rerun/tree/docs-latest/examples/python/rgbd)
- Context7/example query: `RGBD example Pinhole DepthImage Python`

### Live depth sensor

- Teaches: live sensor streaming, continuous depth logging, and real-time depth
  inspection.
- Open when: the workflow is sensor-driven or the problem only appears in a live
  stream.
- Example page:
  [Live depth sensor](https://rerun.io/examples/robotics/live_depth_sensor)
- Source code: follow the `Live depth sensor` example from the official index.
- Context7/example query: `Live depth sensor example depth backprojection Python`

### Depth compare

- Teaches: depth-centric comparison workflows and mixed 2D/3D depth inspection.
- Open when: you want to compare multiple depth producers or debug visual depth
  disagreements.
- Example page:
  [Depth compare](https://rerun.io/examples/image-and-video-understanding/depth_compare)
- Source code: follow the `Depth compare` example from the official index.
- Context7/example query: `Depth compare example depth pinhole Python`

## SLAM And Reconstruction

### DROID

- Teaches: dense geometry plus pinhole camera plus blueprint usage in a
  SLAM-style Python workflow.
- Open when: the task is closest to visual odometry, dense mapping, or
  keyframe-oriented logging.
- Example page: [DROID](https://rerun.io/examples/robotics/droid)
- Source code: follow the `DROID` example from the official index.
- Context7/example query: `DROID example depth pinhole blueprint Python`

### ARKit scenes

- Teaches: mixed 2D, 3D, depth, mesh, and pinhole camera logging in one
  coherent scene.
- Open when: you need a spatial-computing reference with multiple synchronized
  modalities.
- Example page:
  [ARKit scenes](https://rerun.io/examples/spatial-computing/arkit_scenes)
- Source code: follow the `ARKit scenes` example from the official index.
- Context7/example query: `ARKit scenes example depth mesh pinhole blueprint`

### 3D line mapping revisited

- Teaches: structure-from-motion style scene graphs, pinhole camera usage, and
  time-aware multi-view visualization.
- Open when: you need a reference closer to SfM or multi-view reconstruction
  than raw RGB-D.
- Example page:
  [3D line mapping revisited](https://rerun.io/examples/spatial-computing/3d_line_mapping_revisited)
- Source code: follow the `3D line mapping revisited` example from the official
  index.
- Context7/example query: `3D line mapping revisited example pinhole time series`

## Transforms And Frames

### ROS TF

- Teaches: transform trees, parent/child frame reasoning, and coordinate-frame
  debugging.
- Open when: points, cameras, or robot frames land in the wrong place and the
  main suspect is transform composition.
- Example page: [ROS TF](https://rerun.io/examples/robotics/ros_tf)
- Source code: follow the `ROS TF` example from the official index.
- Context7/example query: `ROS TF example transform coordinate frame`

## Multi-View Layout And Blueprint Patterns

### nuScenes

- Teaches: larger scene graphs, multi-view camera setup, 2D plus 3D overlays,
  and blueprint-driven layout.
- Open when: one camera is not enough or the scene has multiple sensing
  modalities that need to share a world root.
- Example page: [nuScenes](https://rerun.io/examples/robotics/nuscenes)
- Source code:
  [rerun/examples/python/nuscenes_dataset](https://github.com/rerun-io/rerun/tree/docs-latest/examples/python/nuscenes_dataset)
- Context7/example query: `nuScenes example pinhole blueprint`

### Eye control

- Teaches: camera perspective presentation and how view controls affect 3D
  inspection.
- Open when: the data is correct but the default 3D view is hard to inspect or
  the camera frustum behavior is confusing.
- Example page: [Eye control](https://rerun.io/examples/robotics/eye_control)
- Source code: follow the `Eye control` example from the official index.
- Context7/example query: `Eye control example pinhole`

### Objectron

- Teaches: 2D and 3D overlays with a pinhole camera and blueprint-backed view
  layout.
- Open when: you need a compact reference for camera-centric overlays rather
  than full dense mapping.
- Example page:
  [Objectron](https://rerun.io/examples/spatial-computing/objectron)
- Source code: follow the `Objectron` example from the official index.
- Context7/example query: `Objectron example pinhole blueprint`

## Selection Heuristic

- Start with `RGBD` for the simplest correct `Pinhole` plus `DepthImage`
  pattern.
- Switch to `DROID` when the shape is closer to SLAM than generic RGB-D.
- Switch to `ROS TF` when frame composition is the main uncertainty.
- Switch to `nuScenes` or `Objectron` when layout, overlays, or multi-view
  organization matter more than the underlying geometry algorithm.
- Use `ARKit scenes` when the task mixes cameras, depth, mesh, and world-space
  scene understanding.
