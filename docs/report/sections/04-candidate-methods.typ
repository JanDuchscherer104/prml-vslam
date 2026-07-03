#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Reference Methods

This section details the state-of-the-art dense monocular SLAM systems chosen for analysis. Each method consumes an ordered image stream and returns camera poses with dense or semi-dense geometry. These systems employ flexible output representations rather than a strict global map, generating structures such as local pointmaps, fused clouds, depth maps, confidence rasters, keyframes, or transformer memories. The primary distinction among them lies in how these varied representations handle frame placement, drift correction, and final dense geometry estimation.

== ViSTA-SLAM
// RESPONSIBLIY: Lukas (ViSTA-SLAM subsection)

ViSTA-SLAM operates as an intrinsics-free dense monocular SLAM system using symmetric two-view association @zhang2026vistaslam. The architecture splits into a frontend for local geometry extraction and a pose graph backend for global optimization.

The Symmetric Two-view Association (STA) frontend processes uncalibrated RGB image pairs via a shared Vision Transformer encoder. Unlike asymmetric models that regress geometry into a single reference frame, STA predicts local point clouds for each view alongside their relative pose. This symmetric formulation reduces the overall parameter count compared to asymmetric baselines, enabling efficient real-time inference. The frontend optimizes pointmap regression, geometric consistency, and relative pose alignment. The relative pose loss incorporates cycle consistency along the $op("SE")(3)$ manifold:

$
  L_("pose") & = w_(i j) ( L_R (bold(R)_(i j), hat(bold(R))_(i j)) \
             & quad + L_t (bold(t)_(i j), hat(bold(t))_(i j)) + L_("id") ) \
             & quad - alpha log(w_(i j))
$

The backend mitigates trajectory drift through $op("Sim")(3)$ pose graph optimization. Graph nodes encode absolute camera poses and independent scale factors. The graph connects these nodes using pose edges from single forward passes and scale edges across different passes of the same view. The system minimizes the residual error in the Lie algebra $frak(s)frak(i)frak(m)(3)$ via the Levenberg-Marquardt algorithm:

$ min_({bold(v)_i^j}) sum_(bold(e)_(i j)) norm(log_("Sim"(3)) (bold(e)_(i j) dot (bold(v)_i^j)^(-1) dot bold(v)_j^i))_(bold(Omega)_(i j))^2 $

This representation matches raw smartphone video constraints. It removes the requirement for known intrinsics while supplying dense 3D geometry. Pairwise learned pointmaps present a specific evaluation risk: the network can generate plausible local geometry that retains correlated scale or shape distortions. This requires benchmark adapters to validate both trajectory alignment and dense cloud placement to verify metric consistency.

== MASt3R-SLAM
// RESPONSIBLIY: Christopher (MASt3R-SLAM subsection)

MASt3R-SLAM is the second method we add to the benchmark. It is a learning-based
SLAM method that builds a dense 3D reconstruction from a single camera
@murai2025mast3rslam. It estimates the 3D scene directly from the images and does
not need the camera calibration. This is why it fits uncalibrated input such as a
smartphone video.

Three things set MASt3R apart from a classical SLAM system. First, a large,
pre-trained network sits behind it (a foundation model): it has learned 3D geometry
from very many images and therefore gives robust 3D estimates even for unfamiliar
footage.

Second, MASt3R does not need the camera parameters in advance, above all not the
focal length. A classical method needs the focal length to turn a pixel into a
viewing ray into the scene, and only then determines the depth. MASt3R turns this
around: the network predicts the 3D point for each pixel directly — that is,
direction and depth at once. You do not need to know the focal length; it can be
read off these 3D points afterwards. The matching between two images therefore also
happens directly in 3D space and not through classical 2D image features.

Third, the camera is allowed to change during the recording — for example a zoom in
the middle of the video. This is possible because the focal length is not fixed in
advance.

MASt3R-SLAM is more than this single network, though: an online system runs on top
of it. It tracks each new frame against the existing keyframes, fuses them into a
shared set of 3D points, and — when the camera revisits a place — closes the loop
and re-optimises all keyframes together. This is what keeps the trajectory globally
consistent and the drift small over a long video.

We connect MASt3R-SLAM through the same interface as ViSTA-SLAM. Both methods read
the same input frames and write the same output files.

MASt3R-SLAM can run with or without a known calibration. If the calibration is
given, we pass it to the method. If not, the method estimates the camera focal
length on its own. Either way it runs on the raw video.

A second setting controls how dense the reconstruction is. It defines how often a
new keyframe is added. More keyframes give a denser point cloud and cover more of
the image, but the run takes longer.

Each run produces two files: the camera path in the TUM format, and a dense,
coloured point cloud. Both files are the input for the trajectory and
reconstruction evaluation in the next sections.

== LingBot-Map
// RESPONSIBLIY: JAN (LingBot-Map subsection)

// <I revised this section>
LingBot-Map is an end-to-end optimized feed-forward streaming reconstruction model and does not maintain a traditional SLAM graph backend@chen2026gct. Instead, it employs Geometric Context Attention (GCA) to maintain a local window of recent frames and their dense geometry, while also keeping compressed trajectory memory for older frames, hence allowing the emergence of graph-like behavior through learned attention mechanisms.
// The model predicts camera poses and dense depth maps causally as the stream progresses, with scale semantics learned from anchor-frame normalization.
The method employs a DINOv2 backbone to extract image features, which are concatenated with per-frame camera, register, and anchor tokens. These tokens are subsequently processed through an auto-regressive transformer decoder
The GCA module maintains anchor frames for coordinate and scale grounding, a local pose-reference window for recent dense geometry, and compressed trajectory memory for older context to enable capturing long-range dependencies, hence reducing per-frame context growth by roughly 80$times$ over naïve causal attention.
// </I revised this section>


The model predicts poses and dense depth maps causally as the stream progresses. The distinguishing detail is that these are not just cache
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
    [Per-pixel 3D pointmaps; no known focal length needed.],
    [Keyframe fusion, loop closure, and global optimization.],

    [Keyframe density and CUDA runtime shape the result.],
    [LingBot-Map],
    [Anchor-grounded coordinate and scale for streaming.],
    [GCA with local window and trajectory memory.],

    [Anchor errors and compressed memory are hard to audit.], bottomrule(),
  ),
  caption: [Representation choices that determine how each method should be adapted and evaluated.],
) <tab:method-representation>
