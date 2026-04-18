# Context7 Queries

Use the Context7 library ID `/rerun-io/rerun`.

Start with one narrow query. Add version or example names only if the first
results are too broad.

## Core Logging

| Goal | Query |
| --- | --- |
| Recording lifecycle | `RecordingStream application_id recording_id Python` |
| Multiple sinks | `set_sinks GrpcSink FileSink RecordingStream Python` |
| Logging API | `rr.log entity path static recording Python` |
| Timelines | `set_time set_time_sequence sequence timeline Python` |

## Transforms And Frames

| Goal | Query |
| --- | --- |
| Transform basics | `Transform3D Python` |
| Relation semantics | `Transform3D TransformRelation ParentFromChild ChildFromParent Python` |
| Legacy flag | `Transform3D from_parent relation Python` |
| World conventions | `ViewCoordinates RIGHT_HAND_Y_UP RIGHT_HAND_Z_UP Python` |
| Camera conventions | `ViewCoordinates RDF RUB camera_xyz Python` |

## Cameras, Images, Depth, And Geometry

| Goal | Query |
| --- | --- |
| Pinhole camera | `Pinhole image_from_camera resolution camera_xyz Python` |
| Resolution semantics | `Pinhole resolution width height Python` |
| RGB images | `Image compress EncodedImage Python` |
| Metric depth | `DepthImage meter point_fill_ratio Python` |
| Auto backprojection | `DepthImage Pinhole 3D backproject Python` |
| Point clouds | `Points3D colors radii Python` |
| Trajectories | `LineStrips3D trajectory polyline Python` |

## Blueprints

| Goal | Query |
| --- | --- |
| Layout basics | `blueprint Blueprint send_blueprint RecordingStream Python` |
| 3D view | `blueprint Spatial3DView origin Python` |
| 2D view | `blueprint Spatial2DView origin Python` |
| Eye controls | `EyeControls3D Spatial3DView Python` |

## Official Example Discovery

Use these when you want working reference code instead of pure API docs.

| Problem | Query |
| --- | --- |
| RGB-D + pinhole + depth | `RGBD example Pinhole DepthImage Python` |
| Live depth sensor | `Live depth sensor example depth backprojection Python` |
| SLAM dense geometry | `DROID example depth pinhole blueprint Python` |
| Transform trees | `ROS TF example transform coordinate frame` |
| Multi-view + blueprint | `nuScenes example pinhole blueprint` |
| Camera eye behavior | `Eye control example pinhole` |
| AR scene + depth | `ARKit scenes example depth mesh pinhole blueprint` |
| 2D and 3D object overlays | `Objectron example pinhole blueprint` |
| SfM-style scene graph | `3D line mapping revisited example pinhole time series` |

## Repo-Aware Queries

Use these after grounding in official Rerun behavior.

| Problem | Query |
| --- | --- |
| Compare local ViSTA reference | `external/vista-slam run.py run_live.py rerun Pinhole Transform3D` |
| Compare current PRML wrapper | `prml_vslam visualization rerun Transform3D Pinhole DepthImage pointmap` |
| Find relation mismatch risks | `TransformRelation ChildFromParent ParentFromChild T_world_camera` |

## Query Notes

- If the integration is pinned to a specific SDK release, append the version,
  for example `0.24` or `0.24.1`.
- If you already know the example name, query that exact name before broad
  category terms.
- If no Context7 MCP server is available in the current session, open the direct
  example page from `official-examples-map.md` and use its Python source link.
- If Context7 results are shallow, fall back to the official docs at
  `https://ref.rerun.io/docs/python/stable/common/` and the examples index at
  `https://rerun.io/examples`.
