#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Alignment and Evaluation Protocol

Evaluation begins with frame semantics. The repository uses an RDF camera convention for normalized
observations, and a camera pose maps camera-frame coordinates into the selected world frame. For a
depth pixel with image coordinates $(u_j, v_j)$, depth $z_j$ in meters, and intrinsic matrix $K$,
the camera-frame point is obtained by pinhole backprojection:

$
  bold(q)_j = z_j bold(K)^(-1) mat(u_j; v_j; 1).
$

If a pose $bold(T)^"w"_"c"$ is available, the point is placed in the selected world frame by
$bold(p)_j = bold(T)^"w"_"c" bold(q)_j$. The same convention is used when method-predicted depth is
converted into a point cloud or when RGB-D reference data are converted into diagnostic geometry.
The resulting cloud is meaningful only together with its frame label, depth units, intrinsics, and
pose provenance.

This convention is intentionally close to the ViSTA-SLAM adapter boundary. ViSTA's upstream
visualization logs pinhole cameras in RDF coordinates, matching Rerun's documented RDF camera
convention, and exposes dense pointmaps as camera-local geometry under a camera pose; the benchmark
keeps that separation instead of baking a viewer transform into the method output
@zhang2026vistaslam @zhang2026vistaslamRepo @rerun2026. The same pinhole equation is used for
source-prepared TUM RGB-D and Record3D reference clouds and for depth-backed method clouds.

Reference clouds are sampled in two stages. First, only pixels on the configured depth stride are
unprojected and non-finite or non-positive depths are rejected:

$
  cal(Omega)_d =
  { (u, v) | u equiv 0 mod d, v equiv 0 mod d }.
$

The valid-depth stride set is

$
  cal(J)_d = { (u, v) in cal(Omega)_d | z(u,v) > 0 } .
$

Second, the fused cloud is capped by a deterministic random subset without replacement,

$
  cal(I) subset {1, dots, N},
  quad
  abs(cal(I)) = min(N, M).
$

The persisted capped cloud is

$
  P_M = { bold(p)_i | i in cal(I) } .
$

This cap is part of persisted benchmark preprocessing because it controls reference-cloud size after
all selected observations have contributed. Rerun point-cloud decimation is a separate visualization
policy and does not define the metric artifact.

Monocular trajectories are generally observable only up to a similarity transform. After timestamp
association, the standard trajectory placement estimates a Sim(3) transform that maps estimated
positions into the reference trajectory:

$
  bold(S)^* =
  arg min_(bold(S) in "Sim"(3)) sum_i
  norm(bold(x)_i^"ref" - bold(S) bold(x)_i^"est")^2 .
$

The transform acts on a point as

$
  bold(S) bold(x) = s bold(R) bold(x) + bold(t).
$

This least-squares formulation follows Umeyama alignment @umeyama1991least. The alignment choice is
not a cosmetic detail: changing from timestamp-only absolute pose error to Sim(3)-aligned absolute
trajectory error changes the scientific question from metric-scale recovery to trajectory-shape
agreement. The trajectory-evaluation literature therefore recommends reporting the alignment
transformation type together with the error metric @zhang2018trajectory.

A trajectory pair is admissible only after timestamp association, pose-relation agreement, and
target-frame agreement have been established from metadata. Let $bold(T)_i$ and
$hat(bold(T))_i$ denote the reference pose and aligned estimate at associated index $i$, both in the
selected target frame. The translational absolute pose error (APE) residual is

$
  bold(e)^"ape"_i =
  op("trans")(bold(T)_i^(-1) hat(bold(T))_i).
$

The APE table reports the configured aggregate, with root-mean-square error (RMSE) defined as

$
  "RMSE"_"ape" =
  sqrt(frac(1, n) sum_i norm(bold(e)^"ape"_i)^2).
$

For a temporal lag $h$, relative pose error (RPE) compares frame-to-frame motion rather than
absolute placement. The reference and estimated relative motions are

$
  bold(D)^"ref"_(i,h) = bold(T)_i^(-1) bold(T)_(i+h),
  quad
  bold(D)^"est"_(i,h) = hat(bold(T))_i^(-1) hat(bold(T))_(i+h).
$

The RPE residual is

$
  bold(E)^"rpe"_i =
  (bold(D)^"ref"_(i,h))^(-1) bold(D)^"est"_(i,h).
$

The reported translational RPE is the norm of $op("trans")(bold(E)^"rpe"_i)$, aggregated with the
same statistic as the APE table. These definitions match common visual-odometry evaluation practice
and the `evo` tool family used by many SLAM studies @zhang2018trajectory @grupp2017evo.

For mobile-provider trajectories with an observable vertical axis, an unconstrained 3D rotation can
be too permissive. The framework therefore distinguishes full Sim(3) alignment from a gravity-aware
variant that estimates scale, yaw, and translation while preserving the known up direction:

$
  bold(S)^* =
  arg min_(s, theta, bold(t)) sum_i
  norm(bold(x)_i^"ref" - (s bold(R)_"yaw"(theta) bold(x)_i^"est" + bold(t)))^2 .
$

The yaw constraint preserves the source up direction $bold(u)$:

$
  bold(R)_"yaw" bold(u) = bold(u).
$

This constraint is especially relevant for near-planar phone trajectories, where arbitrary roll or
pitch can visually improve a trajectory overlay while violating the source's gravity semantics.
For ADVIO datastore candidates, the fixedpoint-common-start publication already places GT, ARCore,
and ARKit in one benchmark target frame before evaluation; post-hoc GT-aligned provider trajectories
are diagnostic references rather than candidate trajectories.

Point-cloud registration is a placement diagnostic after global trajectory alignment, not a
replacement for trajectory evaluation. Given a Sim(3)-placed method cloud $P$ and a reference cloud
$Q$, point-to-point ICP estimates a local rigid correction:

$
  bold(T)^* =
  arg min_(bold(T) in "SE"(3)) sum_(bold(p) in P)
  norm(bold(T) bold(p) - op("NN")_Q(bold(T) bold(p)))^2 .
$

A correspondence threshold $tau$ defines which nearest-neighbor matches count as inliers:

$
  cal(C)_tau =
  { (bold(p), op("NN")_Q(bold(T)^* bold(p))) |
    norm(bold(T)^* bold(p) - op("NN")_Q(bold(T)^* bold(p))) <= tau } .
$

The threshold affects fitness, inlier root-mean-square error, and any later dense-geometry score, so
it is part of the metric record @besl1992method @zhou2018open3d. The framework can persist Sim(3)
trajectory alignment, aligned trajectories, Sim(3)-placed point clouds, and ICP placement metadata.
Dense-cloud accuracy, completeness, Chamfer distance, or F-score should be reported only after the
dense metric runtime is validated against the same frozen experiment matrix.

#figure(
  table(
    columns: (0.92fr, 1.3fr, 1.35fr),
    align: (left, left, left),
    inset: (x: 0.24em, y: 0.21em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Protocol item], [Required choice], [Why it affects interpretation]),
    midrule(),
    [Trajectory association],
    [Timestamp tolerance and selected reference source.],
    [Controls which poses enter the error computation.],
    [Similarity alignment],
    [SE(3), Sim(3), or gravity-aware scale-yaw-translation alignment.],
    [Determines whether scale recovery or shape agreement is being measured.],
    [ADVIO publication],
    [Raw-to-RDF, fixedpoint registration, common-start local frame, and diagnostic-only GT alignments.],
    [Prevents provider-local frames or oracle alignments from entering candidate metrics.],
    [Reference-cloud sampling],
    [Depth stride, validity mask, maximum point count, and random seed.],
    [Keeps dense geometry reproducible without changing the selected source frames.],
    [Point-cloud placement],
    [Reference cloud, initialization, ICP threshold, and inlier statistics.],
    [Separates global trajectory placement from local dense-geometry refinement.],
    [Metric reporting],
    [Metric definition, units, pose relation, and artifact path.],
    [Makes numerical values reproducible from persisted artifacts.],
    bottomrule(),
  ),
  caption: [Protocol fields that must accompany trajectory and dense-geometry metrics.],
) <tab:alignment-protocol>
