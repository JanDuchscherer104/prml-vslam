#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Trajectory Alignment and Evaluation

For benchmarking of the implemented SLAM methods, stages for #link("https://github.com/JanDuchscherer104/prml-vslam/tree/main/src/prml_vslam/align")[alignment] and #link("https://github.com/JanDuchscherer104/prml-vslam/blob/main/src/prml_vslam/eval/services/trajectory_evaluation.py")[evaluation] of the estimated trajectories of the VSLAM Methods against reference trajectories have been implemented in the pipeline. 

== Alignment problem

A monocular camera cannot observe metric scale, the world coordinate frame, or the orientation of
the world: a real scene and a uniformly scaled, translated, and rotated replica of it project to
identical images. Estimated and reference trajectories are therefore never in the same frame,
scale, or orientation, and no residual error is meaningful until a best-fit transform places the
estimate into the reference frame. The ambiguity has exactly three degrees of freedom -- scale,
translation, and rotation -- matching the parameters of a similarity transform, which motivates the
alignment model used below. Evaluation is explicit by construction: the trajectory-evaluation stage
only runs when a benchmark reference is available and requested by the experiment configuration, so
no metric is fabricated when a reference is missing.

// TODO: cite a general monocular VO/SLAM survey or tutorial for the scale/frame/orientation ambiguity claim above (see REPORT_PLAN_TRAJECTORY_EVALUATION.md Part C.1 -- unverified candidates, confirm before citing).

== Timestamp association

Estimated and reference trajectories are sampled at different, generally mismatched rates -- for
example a mobile-provider reference at device rate versus a SLAM trajectory at keyframe rate -- so
poses must be paired before alignment or metrics are computed. Pairing uses nearest-timestamp
association with a fixed tolerance of $0.01 "s"$ @grupp2017evo. Only associated pairs enter both
alignment and metric computation; if association coverage is insufficient, the metric is skipped for
that run rather than computed on a biased subset, consistent with the artifact-completeness
criterion in @tab:experiment-protocol.

== Sim(3) alignment (Umeyama)

Monocular trajectories are observable only up to a similarity transform. Alignment therefore solves

$
  bold(S)^* = arg min_(bold(S) in "Sim"(3)) sum_i norm(bold(x)_i^"ref" - bold(S) bold(x)_i^"est")^2,
  quad bold(S) bold(x) = s bold(R) bold(x) + bold(t),
$

in closed form via Umeyama's singular-value decomposition @umeyama1991least. $"SE"(3)$ has no scale
term and cannot correct the ambiguity above, while a full affine map has too many degrees of freedom
and can mask genuine drift as alignment; $"Sim"(3)$ matches the ambiguity exactly. A closed-form
estimator is preferred over an iterative refinement because it is deterministic and carries no
initialization or local-optimum risk. The recovered $(s, bold(R), bold(t))$ is itself a result:
$s approx 1$ indicates correct metric-scale recovery.

// TODO: cite Horn (1987) for the related scale-free absolute-orientation solution and state precisely what Umeyama's method adds beyond it (see REPORT_PLAN_TRAJECTORY_EVALUATION.md Part C.2 -- unverified, confirm before citing).

For references with a known up axis, an unconstrained rotation is too permissive: on near-planar
phone trajectories, Umeyama's fit can return an up/down-flipped $bold(R)$ that lowers the residual
while being physically nonsensical. We therefore also implement a gravity-aware variant that
constrains $bold(R)$ to a yaw rotation about the known up axis $bold(u)$,

$
  bold(S)^* = arg min_(s,theta,bold(t)) sum_i
  norm(bold(x)_i^"ref" - (s bold(R)_"yaw"(theta) bold(x)_i^"est" + bold(t)))^2,
  quad bold(R)_"yaw" bold(u) = bold(u),
$

solved in closed form by projecting centered positions onto the horizontal plane, recovering the yaw
angle via $op("atan2")$, and then back-solving scale and translation. This path applies only when
the reference's target frame is recognized as gravity-aligned, which the current implementation
tests by matching frame names of the form `advio_*_world`; in practice only ADVIO references receive
it, while TUM RGB-D and Record3D use the unconstrained fit (the trajectory-evaluation results below
discuss a case where this gate did not fire on ADVIO).

// TODO: cite a VIO gravity-initialization precedent (e.g. VINS-Mono, ORB-SLAM3) and state precisely how this post-hoc, evaluation-time gravity lock relates to gravity-constrained state estimation (see REPORT_PLAN_TRAJECTORY_EVALUATION.md Part C.3 -- unverified, confirm before citing).

This gravity-aware trajectory alignment changes the reported metric and is unrelated to the separate
RANSAC ground-plane fit used only to orient the point-cloud viewer for display; the latter never
affects a reported trajectory or dense-geometry metric.

== Metrics: APE and RPE

Let $bold(T)_i$ and $hat(bold(T))_i$ denote the associated, Sim(3)-aligned reference and estimated
poses. Absolute pose error (APE) measures global placement,

$
  bold(e)_i^"ape" = op("trans")(bold(T)_i^(-1) hat(bold(T))_i),
  quad
  "RMSE"_"ape" = sqrt(frac(1, n) sum_i norm(bold(e)_i^"ape")^2),
$

and is dominated by accumulated drift and loop-closure quality. Relative pose error (RPE) instead
compares motion over a lag $h$ chosen so consecutive poses are separated by a fixed path length
$Delta = 1 "m"$,

$
  bold(E)_i^"rpe" = (bold(T)_i^(-1) bold(T)_(i+h))^(-1) (hat(bold(T))_i^(-1) hat(bold(T))_(i+h)),
$

and is robust to a single large global error, so it measures local tracking consistency instead
@zhang2018trajectory @sturm2012benchmark. The two are complementary: low RPE with high APE indicates
good local tracking but weak or missing loop closure, whereas high RPE indicates locally
inconsistent odometry regardless of the global outcome @zhang2018trajectory. Each run persists seven
summary statistics per metric (RMSE, mean, median, standard deviation, minimum, maximum, and sum of
squared errors); RMSE is the reported headline as the outlier-sensitive, field-standard statistic,
while medians are additionally used in @tab:trajectory-results, where a single diverged sequence
would otherwise dominate the mean.

// TODO: cite a methodological source for reporting medians alongside RMSE under small sample sizes (see REPORT_PLAN_TRAJECTORY_EVALUATION.md Part C.5 -- unverified, confirm before citing).

// ------------------------------------ POINT-CLOUD -------------------------------------------

= Point Cloud Evaluation

// POINT-CLOUD

Most datasets used for dense-geometry evaluation come with reference point clouds. Given a Sim(3)-placed method cloud $P$ and a reference cloud $Q$,
point-to-point ICP estimates a correction:

$
  bold(T)^* =
  arg min_(bold(T) in "SE"(3)) sum_(bold(p) in P)
  norm(bold(T) bold(p) - op("NN")_Q(bold(T) bold(p)))^2 .
$

We define a threshold $tau$ that determines which nearest-neighbor matches count as inliers:

$
  cal(C)_tau =
  { (bold(p), op("NN")_Q(bold(T)^* bold(p))) |
    norm(bold(T)^* bold(p) - op("NN")_Q(bold(T)^* bold(p))) <= tau } .
$

The threshold affects fitness, inlier RMSE, and any dense-geometry score for later methods. It belongs in the metric record @besl1992method @zhou2018open3d. Dense-cloud accuracy,
completeness, Chamfer distance, and F-score should be reported only after the dense metric runtime is
validated against the same matrix.

For an estimate cloud $E$ and reference cloud $R$, the dense-cloud score uses the two
nearest-neighbor directions separately before combining them. The accuracy queries our estimate points
against the reference points,

$
  "accuracy" =
  frac(1, abs(E)) sum_(bold(e) in E) min_(bold(r) in R) norm(bold(e) - bold(r)),
$

and completeness queries reference points against the estimate,

$
  "completeness" =
  frac(1, abs(R)) sum_(bold(r) in R) min_(bold(e) in E) norm(bold(r) - bold(e)).
$

Their sum is the reported Chamfer distance:

$
  "Chamfer" = "accuracy" + "completeness".
$

This two-direction construction is illustrated in @fig:pointcloud-chamfer-metric.

#figure(
  image("../../figures/pointcloud/metric_schematics/pointcloud_chamfer.svg", width: 100%),
  caption: [Chamfer distance adds the estimate-to-reference and reference-to-estimate nearest-neighbor directions into one dense-cloud distance score.],
) <fig:pointcloud-chamfer-metric>

To calculate the F-score for this dense-cloud, we introduce a tolerance $tau$. Points outside this tolerance are counted as not covered. Analogous to the Chamfer distance, both the estimated point cloud and the reference point cloud are queried.
The *precision* $P$ is the fraction of estimate points within $tau$ of the reference and *recall* $R$ is the fraction of reference points within
$tau$ of the estimate. Let

$
  d_R(bold(e)) = min_(bold(r) in R) norm(bold(e) - bold(r)),
  quad
  d_E(bold(r)) = min_(bold(e) in E) norm(bold(r) - bold(e)).
$

Then

$
  P_tau =
  frac(abs({ bold(e) in E | d_R(bold(e)) <= tau }), abs(E)).
$

$
  R_tau =
  frac(abs({ bold(r) in R | d_E(bold(r)) <= tau }), abs(R)).
$

The dense-cloud F-score is

$
  F_1 = frac(2 P_tau R_tau, P_tau + R_tau).
$

The final dense-cloud tables use $tau = 0.05 "m"$, so the score reads as surface overlap at a
5 cm tolerance rather than an unbounded distance average. @fig:pointcloud-f1-metric visualizes this
thresholded overlap interpretation. Note: 5cm tolerance is quite strict.

#figure(
  image("../../figures/pointcloud/metric_schematics/pointcloud_f1.svg", width: 100%),
  caption: [Dense-cloud F-score converts nearest-neighbor distances into precision and recall under the 5 cm tolerance used for the final metric tables.],
) <fig:pointcloud-f1-metric>

#figure(
  table(
    columns: (0.92fr, 1.3fr, 1.35fr),
    align: (left, left, left),
    inset: (x: 0.24em, y: 0.21em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Protocol item], [Required choice], [Why it affects interpretation]),
    midrule(), [Trajectory association], [Timestamp tolerance and selected reference source.],
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

    [Makes numerical values reproducible from persisted artifacts.], bottomrule(),
  ),
  caption: [Protocol fields that must accompany trajectory and dense-geometry metrics.],
) <tab:alignment-protocol>
