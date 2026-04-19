# ViSTA-SLAM Wrapper

This package contains the canonical ViSTA-SLAM backend integration used by the pipeline.

## Current Scope

- run ViSTA through the upstream `OnlineSLAM` runtime for both offline and streaming pipeline modes
- keep `adapter.py` thin by delegating upstream bootstrap, preprocessing, session stepping, and artifact import to package-local helpers
- preserve exact upstream image preprocessing semantics via the upstream crop-and-resize helper path
- require normalized offline manifests with canonical `rgb_dir` and normalized `timestamps_path`
- preserve native output directories and native `.rrd` files when present
- import native outputs back into normalized `SlamArtifacts`
- require `DBoW3Py` to be importable from the declared `vista` extra and load `vista_slam` from the checked-out upstream repo explicitly, without mutating global `sys.path`

## Frame Conventions

- upstream ViSTA camera-frame outputs use the `RDF` axis convention: `x` right, `y` down, `z` forward
- STA pointmaps and depth-derived point clouds are local camera-space geometry for each view, not pre-transformed world-space points
- upstream `OnlineSLAM.get_view(...).pose` and saved `trajectory.npy` poses use `T_world_camera` (`world <- camera` / camera-to-world)
- upstream world-space exports are formed by applying those `T_world_camera` poses directly to local camera-space points
- upstream live preview and export paths both apply the Sim(3) scale; `get_pointmap_vis()` returns scaled camera-local geometry, while `save_data_all()` additionally transforms the scaled points into the SLAM-local world frame for `pointcloud.ply`
- the ViSTA `world` frame is SLAM-local and initialized from the first keyframe; it is not an externally aligned ENU, ROS, or benchmark-global world frame

## Current Discrepancies

- `intentional difference`: preprocessing preserves upstream crop/resize behavior, so the current RDF-like world semantics are not caused by wrapper-side preprocessing drift
- `documentation gap`: `world/live/source/rgb` is the original source-frame raster, while `world/live/model/camera/image`, depth, pointmap, preview, and intrinsics all belong to the ViSTA-preprocessed model raster
- `documentation gap`: live/session readback exposes scaled camera-local pointmaps, while exported `pointcloud.ply` is a separate fused world-space dense cloud
- `intentional difference`: the repo-owned Rerun tree uses split branches such as `world/live/model` and `world/keyframes/...` rather than upstream `world/est/cam_n` paths; path parity is not required when composed world placement matches upstream
- `documentation gap`: the repo viewer intentionally preserves ViSTA-native RDF-like world semantics instead of normalizing the scene into an operator/world-up basis
- `intentional difference`: offline runs preserve upstream-native visualization artifacts and do not yet synthesize a repo-owned offline `.rrd`

## Preprocessing Steps
![ViSTA preprocessing sequence](../../../../docs/figures/mermaid/vista/vista_preprocessing_sequence.svg)

The repo wrapper preserves the upstream image-ingest path instead of reimplementing it locally. The sequence diagram source lives at [`docs/figures/mermaid/vista/vista_preprocessing_sequence.mmd`](../../../../docs/figures/mermaid/vista/vista_preprocessing_sequence.mmd).

- `build_vista_runtime_components()` resolves repo paths, ensures the upstream `vista_slam` namespace package exists, imports `DBoW3Py`, optionally builds a binary vocabulary cache from the configured text vocabulary, and instantiates `_FastOnlineSLAM`, `FlowTracker`, and `UpstreamVistaFramePreprocessor`.
- Offline frames enter through `VistaSlamBackend.run_sequence()`, while streaming frames enter through `VistaSlamSession.step()`. Both paths pass repository RGB arrays into `UpstreamVistaFramePreprocessor.prepare()`.
- `prepare()` delegates to upstream `SLAM_image_only._crop_resize_if_necessary_image_only()`, which calls `BaseViewGraphDataset._crop_resize_if_necessary_image_only()` to crop around the assumed image-center principal point, respect portrait inputs by transposing the requested resolution when needed, downscale with Lanczos, and apply a final centered crop to the upstream 224x224 raster.
- The same upstream dataset object then applies `ImgGray` and `ImgNorm`, yielding the grayscale `uint8` image used by `FlowTracker.compute_disparity()` and the normalized RGB tensor used by `OnlineSLAM.step()`.
- Frames that fail the optical-flow disparity gate are dropped as non-keyframes. Accepted frames are packaged as `{"rgb", "shape", "gray", "view_name"}` and forwarded into `OnlineSLAM.step()`.
- Inside `OnlineSLAM.step()`, ViSTA encodes the new image with `add_view()`, connects it to the neighbor window with `connect_view_i_j()`, runs `regress_two_views()` to execute `STA._decode_stereo()`, `head_pose_s()`, and `head_pts()`, and adds pose and scale edges to the Sim(3) pose graph.
- `LoopDetector.detect_loop()` extracts ORB descriptors from the grayscale keyframe, scores bag-of-words similarity against earlier frames, and returns loop candidates that satisfy the non-maximum-suppression and minimum-distance thresholds. Accepted candidates are reprocessed through the same `connect_view_i_j()` path as neighbor edges.
- Whenever `view_num % pgo_every == 0` or `force_pgo=True`, `pose_graph_optimize()` runs Levenberg-Marquardt optimization over the selected Sim(3) nodes. The wrapper's live mode forces upstream defaults of `max_view_num=1000`, `neighbor_edge_num=2`, `loop_edge_num=2`, and `pgo_every=50`.

## Postprocessing Steps
![ViSTA postprocessing sequence](../../../../docs/figures/mermaid/vista/vista_postprocessing_sequence.svg)

The wrapper has two postprocessing surfaces: incremental live readback after accepted keyframes, and end-of-run export plus normalization. The sequence diagram source lives at [`docs/figures/mermaid/vista/vista_postprocessing_sequence.mmd`](../../../../docs/figures/mermaid/vista/vista_postprocessing_sequence.mmd).

- `_build_live_update()` reads the best node for one view through `OnlineSLAM.get_view(..., return_pose=True, return_depth=True, return_intri=True)`. Upstream applies the node's Sim(3) scale inside `get_view()` before returning the depth raster.
- The wrapper converts `view.pose` into a canonical `FrameTransform`, converts `view.intri` into `CameraIntrinsics`, and stores the scaled upstream depth raster as `SlamUpdate.depth_map`.
- The same live path then calls `get_pointmap_vis(view_index)`. Upstream reuses `get_view(filter_outlier=False)` and `compute_local_pointclouds()` to produce a scaled camera-local pointmap together with a pseudo-colored preview image.
- The wrapper copies that pointmap into `SlamUpdate.pointmap`, counts valid finite `z > 0` points, and emits a non-fatal backend warning when dense output was requested but no usable pointmap is available.
- `VistaSlamSession.close()` persists native outputs through `save_data_all(native_output_dir, save_images=False, save_depths=False)`. With those arguments, upstream still writes `view_graph.npz`, `trajectory.npy`, `scales.npy`, `confs.npz`, `intrinsics.npy`, and `pointcloud.ply`; it simply omits `images.npy` and `depths.npy`.
- When `save_ply=True`, upstream export multiplies each best-node depth map by its Sim(3) scale, unprojects the scaled depth with `compute_local_pointclouds()`, and then applies the corresponding `T_world_camera` pose before writing `pointcloud.ply`.
- `build_vista_artifacts()` normalizes those native outputs back into repository-owned contracts by converting `trajectory.npy` into canonical `FrameTransform` entries and `slam/trajectory.tum`, optionally re-encoding `pointcloud.ply` into the repo-owned `slam/point_cloud.ply`, and retaining the remaining native files as `extras`.
- The main live/export asymmetry is coordinate frame, not scale handling: the live pointmap path returns scaled camera-local geometry, while the export path returns scaled world-space geometry in ViSTA's SLAM-local world frame.

## Rerun Logging

The repo wrapper does not invoke upstream `run.py` or `run_live.py` during normal execution; it embeds `OnlineSLAM` directly. Those scripts are still the best reference for how the upstream project logs ViSTA state into Rerun.

- Both scripts initialize Rerun with `rr.init("slam", ...)`, optionally call `rr.save(...)` and `rr.connect_grpc(...)`, and log a root `/world` transform before any camera state is displayed.
- `rerun_vis_views()` fetches `pose`, `depth`, and `intri` via `get_view()`, reconstructs a camera-local point cloud with `compute_local_pointclouds(depth, intri)`, and fetches the pseudo-colored preview plus scaled camera-local pointmap through `get_pointmap_vis()`.
- `log_view()` writes `rr.Transform3D` at `world/est/<topic>`, a `rr.Pinhole(..., camera_xyz=rr.ViewCoordinates.RDF)` and `rr.Image` under `world/est/<topic>/cam`, and `rr.Points3D` under `world/est/<topic>/points`.
- This logging tree is frame-consistent because the point cloud remains camera-local and sits underneath a posed camera entity. The preview image is a pseudo-colored pointmap diagnostic, not a raw RGB frame and not a metric depth raster.
- The offline script advances time with `rr.set_time("index", sequence=t)`. The live script instead keeps a sliding window of recent cameras and currently leaves the explicit time update commented out.
