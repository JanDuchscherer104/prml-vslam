= Related Work

The closest methodological analogue for this paper is not a single SLAM algorithm but a research
framework that makes an active problem easier to study reproducibly. Nerfstudio is a useful model:
it presents a modular framework for neural radiance field research with standardized data
ingestion, model components, real-time visualization, and exports to video, mesh, and point-cloud
representations @tancik2023nerfstudio. SLAMBench2 plays a similar role for SLAM by defining an
extensible benchmark interface over algorithms, datasets, and metrics, enabling comparable and
validatable experiments across systems with different accuracy, runtime, and resource trade-offs
@bodin2018slambench2. This paper follows the same framing for uncalibrated phone VSLAM: the primary
object of study is the measurement substrate that makes later method comparison defensible.

Trajectory evaluation is a second source of guidance because visual odometry and SLAM results are
not meaningful without an explicit alignment convention. Zhang and Scaramuzza emphasize that the
choice of transformation used for alignment depends on the sensing modality and the experimental
question @zhang2018trajectory. This distinction is central for monocular methods, where scale is
ambiguous, and for visual-inertial or phone-provider trajectories, where gravity may already be
observable. The report therefore treats frame direction, timestamp association, alignment mode, and
metric interpretation as part of the protocol rather than as implementation details.

The reference methods represent three modern design points for dense uncalibrated reconstruction.
ViSTA-SLAM uses a symmetric two-view association frontend and a Sim(3) pose-graph backend with loop
closures @zhang2026vistaslam. MASt3R-SLAM builds an online dense SLAM system from learned two-view
3D reconstruction priors, efficient pointmap matching, local fusion, and second-order global
optimization @murai2025mast3rslam. LingBot-Map uses GCT, a feed-forward streaming model whose
Geometric Context Attention maintains anchors, a local pose-reference window, and trajectory memory
for causal long-sequence inference @chen2026gct. The benchmark interface must therefore accept
outputs from optimization-heavy pairwise systems and from feed-forward streaming systems without
assuming that their internal maps have the same coordinate or uncertainty semantics.

The selected datasets cover complementary roles. ADVIO provides smartphone visual-inertial
sequences with ground-truth trajectories and mobile-provider pose estimates @cortes2018advio. TUM
RGB-D provides synchronized color and registered depth images with motion-capture ground truth,
which makes it suitable for controlled trajectory evaluation and depth-derived reference-cloud
preparation @sturm2012benchmark. Record3D supplies the self-recorded iPhone RGB-D path and therefore
connects public benchmarks to the custom smartphone-data requirement @record3d2026. Open3D provides
the practical point-cloud processing and registration primitives used by the implementation
@zhou2018open3d, while Umeyama alignment @umeyama1991least and ICP @besl1992method provide the
geometric basis for the transform stages.
