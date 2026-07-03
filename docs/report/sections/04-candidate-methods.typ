#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Reference Methods

This section details the state-of-the-art dense monocular SLAM systems chosen for analysis. Each method consumes an ordered image stream and returns camera poses with dense or semi-dense geometry. These systems employ flexible output representations rather than a strict global map, generating structures such as local pointmaps, fused clouds, depth maps, confidence rasters, keyframes, or transformer memories. The primary distinction among them lies in how these varied representations handle frame placement, drift correction, and final dense geometry estimation.

== ViSTA-SLAM
// RESPONSIBLIY: Lukas (ViSTA-SLAM subsection)

ViSTA-SLAM is an intrinsics-free dense monocular SLAM system that relies on symmetric two-view association @zhang2026vistaslam. Instead of regressing geometry into a single reference frame, the model utilizes a Symmetric Two-view Association (STA) frontend for local geometry extraction and a pose graph backend for global optimization.

#figure(
  image("/docs/figures/papers/figure-2-vista-architecture.png", width: 100%),
  caption: [The symmetric two-view association architecture of ViSTA-SLAM. A shared Vision Transformer encoder extracts features which are then processed by a single symmetric decoder to predict local point clouds and relative poses @zhang2026vistaslam.],
) <fig:vista_architecture>

The method employs a shared Vision Transformer encoder to extract features from uncalibrated RGB image pairs. These features pass through a symmetric decoder that predicts local point clouds for each view alongside their relative pose. This formulation reduces the parameter count compared to asymmetric baselines and enables real-time inference. The frontend trains by optimizing pointmap regression, geometric consistency, and relative pose alignment. The relative pose loss enforces cycle consistency along the $op("SE")(3)$ manifold:

$
  L_("pose") & = w_(i j) ( L_R (bold(R)_(i j), hat(bold(R))_(i j)) \
             & quad + L_t (bold(t)_(i j), hat(bold(t))_(i j)) + L_("id") ) \
             & quad - alpha log(w_(i j))
$

The backend optimizes absolute camera poses and independent scale factors as graph nodes as the image stream progresses. The pose graph connects these nodes using pose edges from single forward passes and scale edges across repeated passes of the same view. The system mitigates trajectory drift by minimizing the residual error in the Lie algebra $frak(s)frak(i)frak(m)(3)$ via the Levenberg-Marquardt algorithm:

$ min_({bold(v)_i^j}) sum_(bold(e)_(i j)) norm(log_("Sim"(3)) (bold(e)_(i j) dot (bold(v)_i^j)^(-1) dot bold(v)_j^i))_(bold(Omega)_(i j))^2 $

This design makes pairwise geometry consistency part of the learned state. The system handles raw smartphone video by removing the requirement for known intrinsics while supplying dense 3D geometry. Pairwise learned pointmaps present an evaluation risk: the network can generate plausible local geometry that retains correlated scale or shape distortions. The adapter treats ViSTA-SLAM as a dual trajectory and dense-cloud exporter, requiring validation of both trajectory alignment and dense cloud placement to verify metric consistency.

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
    [Per-pixel 3D pointmaps; no known focal length needed.],
    [Keyframe fusion, loop closure, and global optimization.],

    [Keyframe density and CUDA runtime shape the result.],
    [LingBot-Map],
    [Anchor-grounded coordinate and scale for streaming.],
    [GCA with local window and six-token trajectory memory.],

    [No explicit loop closure; compressed memory is opaque.], bottomrule(),
  ),
  caption: [Representation choices that determine how each method should be adapted and evaluated.],
) <tab:method-representation>
