#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Reference Methods

The benchmark treats each reconstruction system as a method that consumes an ordered image stream
and returns camera poses with dense or semi-dense geometry. This abstraction is deliberately weaker
than a shared internal map representation. A learned method may produce local pointmaps, fused
world-space clouds, depth maps, confidence rasters, keyframes, or transformer memories; the
benchmark-facing contract records only the outputs needed for comparison and provenance. The
scientific value of the method section is therefore to explain the representation choices that later
affect alignment and interpretation.

== ViSTA-SLAM

ViSTA-SLAM is an intrinsics-free dense monocular SLAM system whose central idea is symmetric
two-view association @zhang2026vistaslam. Rather than regressing both images into the coordinate
system of a designated reference view, the frontend predicts local pointmaps in each view's own
coordinate system together with a relative pose. This symmetry is important for uncalibrated
benchmarking because it avoids privileging one frame as the global coordinate anchor at the
two-view stage. It also makes pairwise measurements suitable for a backend in which each view can be
represented by graph nodes connected through relative Sim(3) constraints.

The backend constructs a Sim(3) pose graph with pose edges, scale edges, and loop-closure edges.
Scale edges are needed because pointmaps predicted for the same view in different forward passes may
not share the same scale. Loop closure adds long-range constraints when image retrieval and the
frontend relative-pose confidence indicate that a candidate pair is geometrically plausible. In this
design, the learned frontend supplies local geometric constraints and the optimization backend
imposes global consistency.

For this framework, ViSTA-SLAM is relevant because its assumptions match raw smartphone video:
known intrinsics are not required and dense output is available. The same representation also
defines an evaluation risk. The method depends on the quality and consistency of learned pairwise
pointmap predictions, so a visually plausible fused cloud should not be treated as an absolute
reference. The benchmark should therefore evaluate both trajectory alignment and dense-geometry
placement.

== MASt3R-SLAM

MASt3R-SLAM represents a learned-prior-plus-optimization design point @murai2025mast3rslam. It
starts from MASt3R two-view predictions, which provide pointmaps and matching features, and builds a
real-time dense SLAM system around efficient pointmap matching, tracking, keyframe fusion, loop
closure, and second-order global optimization. The method assumes only a generic central camera
model: each image has a unique camera center and can be represented by rays, without requiring a
fixed pinhole calibration model for the whole sequence. This makes it relevant for phone videos in
which calibration may be unavailable, distorted, or time-varying.

The most relevant technical feature for the benchmark is MASt3R-SLAM's treatment of pointmaps as
geometric pseudo-measurements. Matching is formulated through projective pointmap alignment and ray
error, tracking estimates the current frame relative to a keyframe, and local fusion maintains a
canonical keyframe pointmap. Backend optimization then enforces large-scale consistency over the
keyframe graph. In contrast to pure feed-forward global prediction, this keeps an explicit
optimization layer where loop closures and geometric residuals can correct drift.

The method also exposes important evaluation caveats. Its claim of weak camera-model assumptions
does not remove the need to record the image preprocessing, pointmap frame, and runtime environment
used by an implementation. The system is CUDA-oriented and relies on efficient matching and
optimization kernels, which makes runtime environment part of reproducibility. Learned pointmaps can
also contain correlated geometric errors; dense geometry should be compared only after the benchmark
records the pointmap-derived cloud, its frame, and the alignment used to place it against a
reference.

== LingBot-Map

LingBot-Map, through GCT, differs most strongly from the other two methods because it is a
feed-forward streaming reconstruction model rather than a local tracking system with an explicit
graph backend @chen2026gct. Its Geometric Context Attention decomposes the streaming state into
three contexts. Anchor frames establish a coordinate and scale reference; a local pose-reference
window keeps dense recent observations for local geometry; and trajectory memory compresses older
frames into compact tokens so long-range context remains available without storing all image tokens.
The model then predicts camera poses and dense depth maps causally as the stream progresses.

This design is scientifically interesting because it moves a structure inspired by SLAM into the
attention mechanism itself. Classical systems maintain a local tracking window, a global map, and
loop-closure or optimization machinery. GCT abstracts part of that state into learned attention over
anchors, local windows, and compressed history. Direct Output mode keeps a single continuous
streaming state, while Visual-Odometry mode splits long sequences into overlapping windows and
fuses them through Sim(3). The upstream paper reports this as a route to long-sequence streaming
inference with bounded memory growth.

The same representation choice creates a useful critique. Because GCT uses early anchor frames for
coordinate and scale grounding, errors or limited scene coverage in the anchor context may influence
the entire sequence. The compressed trajectory memory can preserve long-range cues, but it is less
directly inspectable than explicit graph edges. The benchmark adapter also does not expose an
explicit bundle-adjustment-like correction artifact. In the benchmark framework, LingBot-Map is
therefore treated as a method that exports a trajectory and a dense point-cloud artifact derived
from predicted depth, while its internal attention state remains an upstream model representation
rather than a benchmark reference.

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
    [Anchor errors and compressed memory are hard to audit.],
    bottomrule(),
  ),
  caption: [Representation choices that determine how each method should be adapted and evaluated.],
) <tab:method-representation>
