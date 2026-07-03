#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Trajectory Alignment

// TODO: Trajectory Alignment Methodology by VB.

= Trajectory Evaluation

// TODO: Trajectory Evaluation Methodology by VB.

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
