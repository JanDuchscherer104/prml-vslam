# LingBot-Map Method Wrapper

This package owns the repo adapter for the optional `lingbot` dependency group.
The wrapper consumes normalized observations, runs upstream inference, and
writes repository-owned SLAM artifacts.

## Parameter Parity

The main full-scene config is `.configs/pipelines/lingbot-full.toml`. It is
tuned to complete all ADVIO-20 frames on an RTX 3080 Ti without source-side
frame sampling or SLAM frame caps:

| Setting | Upstream / paper baseline | Repo benchmark choice | Rationale |
| --- | --- | --- | --- |
| `mode` | Direct Output Mode via streaming inference; windowed inference for long sequences | `windowed` | Bounds GPU residency for long scenes. |
| `image_size` | `518` width, about `518x378` in the paper | `84` | Keeps all-frame ADVIO-20 dense prediction tensors within local RAM. |
| `num_scale_frames` | `8`; upstream recommends `2` for limited VRAM | `2` | Uses upstream's first limited-VRAM adjustment; `8` OOMs before completing this run. |
| `kv_cache_sliding_window` | `64` | `64` | Matches the local pose-reference window size `k=64`. |
| `keyframe_interval` | `auto`: `1` up to about 320 frames, then `ceil(N/320)` | `auto` | Lets upstream bound retained keyframes for the selected sequence length. |
| `window_size` / `overlap_keyframes` | windowed inference controls | `128` / `8` | Long-scene windowing profile used for ADVIO-20 completion. |
| `camera_num_iterations` | `4` | `4` | Keeps pose refinement at the accuracy-oriented default. |
| `use_amp` / dtype | bfloat16/float16 inference through CUDA autocast | `use_amp=true`, `model_dtype=auto` | Matches upstream precision handling while reducing memory pressure. |
| `use_sdpa` | `false` when FlashInfer is installed; SDPA fallback documented | `false` | Uses FlashInfer for benchmark runs from the `prml-vslam` mamba environment. |
| `enable_point_head` | upstream benchmark notes depth backprojection is used | `false` | Avoids running an unsupported point-head path for the maintained checkpoint. |
| `confidence_threshold` | upstream viewer/export default varies by entry point | `0.5` | Filters low-confidence depth before durable point-cloud export. |

The current robustness-sensitive choice is avoiding source sampling. ADVIO-20
has more than 18k RGB frames locally, and upstream windowed inference still
stitches dense prediction tensors after all windows complete. The full config
therefore uses `image_size=84`, `checkpoint_pos_embed="interpolate"`, and
windowed inference as the all-frame completion profile. The previous TUM cabinet
quality profile used `image_size=392`; keep that as historical tuning evidence,
not the default full-scene config.

## Normalized Artifacts

LingBot trajectories are normalized to `T_world_camera` and written to
`slam/trajectory.tum`. Dense geometry is written to `slam/point_cloud.ply` and
returned through the shared `dense_points_ply` contract field.

The adapter intentionally does not export LingBot depth maps, point maps, or
confidence rasters as first-class artifacts. Those arrays remain upstream-native
model internals unless a later task needs them enough to justify a tested
contract. The current durable contract is the trajectory, the point cloud, and
small native metadata extras under `native/`.
