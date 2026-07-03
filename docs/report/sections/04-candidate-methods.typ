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

LingBot-Map, through GCT, is a feed-forward streaming reconstruction model rather than a local
tracker with an explicit graph backend @chen2026gct. Geometric Context Attention maintains anchor
frames for coordinate and scale grounding, a local pose-reference window for recent dense geometry,
and compressed trajectory memory for older context. The model predicts poses and dense depth maps
causally as the stream progresses. The distinguishing detail is that these are not just cache
policies: the paper trains a DINOv2-based transformer with camera, register, and anchor tokens,
camera-to-world pose supervision, depth supervision, and a relative pose loss inside the local
window. Its scale semantics are learned from anchor-frame normalization, while its long-range state
keeps only compact per-frame trajectory tokens after image tokens leave the local window.

This design makes coordinate commitment part of the learned state. Anchor errors or limited anchor
coverage can affect the full sequence, and compressed trajectory memory is less auditable than
explicit graph edges. The adapter therefore treats LingBot-Map as a trajectory and depth-derived
cloud exporter; its attention state is not a benchmark reference. In the final local evidence pass,
LingBot-Map is retained as a reference method and contributes only TUM RGB-D dense-cloud diagnostic
values where completed artifacts exist. It is not treated as a full cross-dataset trajectory
candidate or as phone-video leaderboard evidence.

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
    [GCA with local window and trajectory memory.],

    [Anchor errors and compressed memory are hard to audit.], bottomrule(),
  ),
  caption: [Representation choices that determine how each method should be adapted and evaluated.],
) <tab:method-representation>
