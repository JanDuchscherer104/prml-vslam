#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Reference Methods

The benchmark treats each reconstruction system as a method that consumes an ordered image stream
and returns camera poses with dense or semi-dense geometry. The contract is intentionally weaker
than a shared map representation: methods may produce pointmaps, fused clouds, depth maps,
confidence rasters, keyframes, or transformer memories. The relevant distinction is how each
representation affects frame placement, drift correction, and dense-geometry interpretation.

== ViSTA-SLAM
// RESPONSIBLIY: Lukas (ViSTA-SLAM subsection)

ViSTA-SLAM is an intrinsics-free dense monocular SLAM system based on symmetric two-view
association @zhang2026vistaslam. Instead of regressing both images into a chosen reference view, the
frontend predicts local pointmaps in each view's coordinate system plus a relative pose. The backend
then optimizes a Sim(3) pose graph with pose, scale, and loop-closure edges. Scale edges are needed
because repeated pointmap predictions for the same view may not share a common scale.

This representation matches raw smartphone video because known intrinsics are not required and
dense output is available. It also defines the evaluation risk: pairwise learned pointmaps can yield
visually plausible fused geometry while retaining correlated scale or shape errors. ViSTA-SLAM
therefore needs both trajectory placement and dense-cloud placement checks.

== MASt3R-SLAM
// RESPONSIBLIY: Christopher (MASt3R-SLAM subsection)

MASt3R-SLAM combines learned two-view priors with an explicit SLAM backend @murai2025mast3rslam.
MASt3R predictions provide pointmaps and matching features; the online system adds efficient
pointmap matching, tracking, keyframe fusion, loop closure, and second-order global optimization.
Its generic central-camera assumption requires a unique camera center and ray representation per
image, but not a fixed calibrated pinhole model for the whole sequence.

For evaluation, pointmaps act as geometric pseudo-measurements. Tracking estimates a frame relative
to a keyframe, fusion maintains canonical keyframe pointmaps, and global optimization reconciles the
keyframe graph. The benchmark must therefore record image preprocessing, pointmap frame, CUDA
runtime, and cloud-placement transform; weak camera-model assumptions do not remove those
reproducibility variables.

== LingBot-Map
// RESPONSIBLIY: JAN (LingBot-Map subsection)

LingBot-Map is an end-to-end optimized streaming reconstruction model and does not maintain a traditional SLAM graph backend. The Geometric Context
Transformer (GCT) is a causal feed-forward model: at time $t$ it predicts a
camera-to-world pose and dense depth map from a _geometric_ context from frames up to $t$ @chen2026gct. A DINOv2 backbone encodes each uncalibrated RGB frame, augments it
with one camera token, four register tokens, and one anchor token, and alternates
per-frame attention with Geometric Context Attention (GCA). GCA gives the
streaming state three roles: anchor frames set the coordinate frame and
monocular scale, a local pose-reference window retains full image tokens for
recent overlap, and trajectory memory preserves only six context tokens per
older frame to capture necessary invariants.

This learned state is the main distinction that enables learned attention to stand in for a traditional SLAM graph optimization to capture long-term geometric context as it reduces per-frame memory growth by a factor of 80, with memory dropping from 36.06 GB to 13.28 GB and throughput rising
from 11.87 FPS to 20.29 FPS @chen2026gct.

Similarly to ViSTA-SLAM and MASt3R-SLAM, LingBot-Map supervises depth,
absolute camera-to-world pose, and relative poses within the local window, so
anchor, window, and cache settings affect the geometric estimate.

The method provides two modes: Streaming
mode runs one causal pass, whereas windowed mode resets the KV cache over
overlapping segments and aligns the resulting windows to bound peak memory, hence enabling indefinite-length sequences, at the cost of losing capactiy to capture connections between distant frames.

#figure(
  table(
    columns: (0.68fr, 1.08fr, 1.12fr, 1.1fr),
    align: (left, left, left, left),
    inset: (x: 0.22em, y: 0.2em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Method], [Coordinate strategy], [Consistency mechanism], [Benchmark caveat]),
    midrule(),
    [ViSTA-SLAM],
    [Local pointmaps and relative poses; no privileged reference view.],
    [Sim(3) graph with scale and loop-closure edges.],

    [Pairwise geometry errors can persist.],
    [MASt3R-SLAM],
    [Two-view pointmaps with central-camera rays.],
    [Keyframe fusion, loop closure, and global optimization.],

    [CUDA runtime and pointmap bias matter.],
    [LingBot-Map],
    [Anchor-grounded coordinate and scale for streaming.],
    [GCA with local window and six-token trajectory memory.],

    [No explicit loop closure; compressed memory is opaque.], bottomrule(),
  ),
  caption: [Representation choices that determine how each method should be adapted and evaluated.],
) <tab:method-representation>
