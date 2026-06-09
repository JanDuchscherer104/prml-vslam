# LingBot-Map Method Wrapper

This package owns the repo adapter for the operator-managed
`Robbyant/lingbot-map` checkout. The wrapper consumes normalized observations,
runs upstream inference, and writes repository-owned SLAM artifacts.

## Parameter Parity

The main benchmark config is `.configs/pipelines/lingbot-full.toml`. It is
tuned to match the LingBot paper and upstream defaults where practical on an
RTX 3080 Ti:

| Setting | Upstream / paper baseline | Repo benchmark choice | Rationale |
| --- | --- | --- | --- |
| `mode` | Direct Output Mode via streaming inference | `streaming` | Matches the causal GCT path used for ordinary sequences. |
| `image_size` | `518` width, about `518x378` in the paper | `392` | The local SDPA path OOMs before frame 50 at `518` and before frame 60 at `448`; `392` is the current full-run fit candidate. |
| `num_scale_frames` | `8`; upstream recommends `2` for limited VRAM | `2` | Uses upstream's first limited-VRAM adjustment; `8` OOMs before completing this run. |
| `kv_cache_sliding_window` | `64` | `64` | Matches the local pose-reference window size `k=64`. |
| `keyframe_interval` | `auto`: `1` up to about 320 frames, then `ceil(N/320)` | `6` | Retains fewer frames in the KV cache while still predicting all processed frames. |
| `camera_num_iterations` | `4` | `4` | Keeps pose refinement at the accuracy-oriented default. |
| `use_amp` / dtype | bfloat16 inference on Ampere-class CUDA | `use_amp=true`, `model_dtype=auto` | Matches paper precision while reducing memory pressure. |
| `use_sdpa` | `false` when FlashInfer is installed; SDPA fallback documented | `true` | The local `prml-vslam` environment has not provided FlashInfer; SDPA is the streamlined fallback. |
| `enable_point_head` | upstream benchmark notes depth backprojection is used | `false` | Avoids running an unsupported point-head path for the maintained checkpoint. |
| `confidence_threshold` | `1.5` viewer/export default | `1.5` | Filters low-confidence depth before durable point-cloud export. |

The current quality-sensitive choice is source sampling: LingBot's paper states
that Direct mode is trained with keyframe interval `m=1` at 320 views. For the
TUM cabinet sequence, `frame_stride=5` keeps the full benchmark near that range.
On this RTX 3080 Ti without FlashInfer, however, 518-wide SDPA inference OOMs
before frame 50 even with a sparse keyframe interval. The main config therefore
uses `image_size=392`, `checkpoint_pos_embed="interpolate"`, and
`keyframe_interval=6` as the current fit candidate. If FlashInfer is installed
or a larger GPU is available, retry `image_size=518`, `checkpoint_pos_embed =
"error"`, `keyframe_interval = "auto"`, and `use_sdpa = false`.

## Normalized Artifacts

LingBot trajectories are normalized to `T_world_camera` and written to
`slam/trajectory.tum`. Dense geometry is written to `slam/point_cloud.ply` and
returned through the shared `dense_points_ply` contract field.

The adapter intentionally does not export LingBot depth maps, point maps, or
confidence rasters as first-class artifacts. Those arrays remain upstream-native
model internals unless a later task needs them enough to justify a tested
contract. The current durable contract is the trajectory, the point cloud, and
small native metadata extras under `native/`.
