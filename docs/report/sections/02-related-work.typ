= Related Work

The closest analogues are research substrates rather than individual SLAM algorithms. Nerfstudio
standardizes data ingestion, model components, real-time visualization, and exports for neural
radiance-field research @tancik2023nerfstudio. SLAMBench2 defines an extensible SLAM interface over
algorithms, datasets, and metrics so that accuracy, runtime, and resource trade-offs can be
validated across systems @bodin2018slambench2. This paper applies the same idea to uncalibrated
phone VSLAM: the object of study is the measurement substrate that makes later comparison
defensible.

Trajectory evaluation is a second source of guidance because visual odometry and SLAM results are
not meaningful without an explicit alignment convention. Zhang and Scaramuzza emphasize that the
choice of transformation used for alignment depends on the sensing modality and the experimental
question @zhang2018trajectory. This distinction is central for monocular methods, where scale is
ambiguous, and for visual-inertial or phone-provider trajectories, where gravity may already be
observable. Frame direction, timestamp association, alignment mode, and metric interpretation are
therefore reported as protocol variables.

The reference methods represent three modern design points for dense uncalibrated reconstruction.
ViSTA-SLAM uses a symmetric two-view association frontend and a Sim(3) pose-graph backend with loop
closures @zhang2026vistaslam. MASt3R-SLAM builds an online dense SLAM system from learned two-view
3D reconstruction priors, efficient pointmap matching, local fusion, and second-order global
optimization @murai2025mast3rslam. LingBot-Map uses GCT, a feed-forward streaming model whose
Geometric Context Attention maintains anchors, a local pose-reference window, and trajectory memory
for causal long-sequence inference @chen2026gct. The benchmark interface must therefore accept
outputs from optimization-heavy pairwise systems and from feed-forward streaming systems without
assuming that their internal maps have the same coordinate or uncertainty semantics.

The selected datasets have complementary reference semantics. ADVIO provides smartphone
visual-inertial sequences with ground-truth trajectories and mobile-provider pose estimates
@cortes2018advio. TUM RGB-D pairs synchronized color and registered depth with motion-capture ground
truth @sturm2012benchmark. Record3D supplies the self-recorded iPhone RGB-D path @record3d2026.
Open3D provides point-cloud processing and registration primitives @zhou2018open3d; Umeyama
alignment @umeyama1991least and ICP @besl1992method provide the geometric basis for the transform
stages.
