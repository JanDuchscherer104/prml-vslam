#import "@preview/booktabs:0.0.4": bottomrule, midrule, toprule

= Trajectory Metrics and Evaluation

For benchmarking of the implemented SLAM methods, stages for #link("https://github.com/JanDuchscherer104/prml-vslam/tree/main/src/prml_vslam/align")[alignment] and #link("https://github.com/JanDuchscherer104/prml-vslam/blob/main/src/prml_vslam/eval/services/trajectory_evaluation.py")[evaluation] of the estimated trajectories against reference trajectories have been implemented in the pipeline.

== Alignment problem <sec:alignment-problem>

A monocular camera cannot observe metric scale or the world coordinate frame @scaramuzza2011visual,
nor the orientation of the world. Estimated and reference trajectories are therefore never in the same frame,
scale, or orientation, and collected trajectory metrics are not  meaningful until a alignment between the trajectories was done.
To prevent invalid metrics the trajectory-evaluation stage only runs when a benchmark reference is available, the configuration requests it and the alignment stage finished succesfully.

== Timestamp association

Estimated and reference trajectories are sampled at different, generally mismatched rates -- for
example a mobile-provider reference at device rate versus a SLAM trajectory at keyframe rate -- so
poses must be paired before alignment or metrics are computed. Pairing uses nearest-timestamp
association with a fixed tolerance of $0.01 "s"$ @grupp2017evo. Only associated pairs enter both
alignment and metric computation. If association coverage is insufficient, the evaluation stage is skipped for
the run rather than computed on a biased subset, consistent with the benchmark framework's
artifact-completeness policy.

== Sim(3) alignment (Umeyama)

As described in the section #link(<sec:alignment-problem>)[alignment problem], trajectories must be aligned before comparison. The alignment stage therefore solves

$
  bold(S)^* = arg min_(bold(S) in "Sim"(3)) sum_i norm(bold(x)_i^"ref" - bold(S) bold(x)_i^"est")^2,
  quad bold(S) bold(x) = s bold(R) bold(x) + bold(t),
$

in closed form via Umeyama's singular-value decomposition @umeyama1991least. $"SE"(3)$ has no scale
term and cannot correct the ambiguity above, while a full affine map has too many degrees of freedom
and can mask genuine drift as alignment. $"Sim"(3)$ matches the ambiguity exactly. A closed-form
estimator is preferred over an iterative refinement because it is deterministic and carries no
initialization or local-optimum risk. The recovered $(s, bold(R), bold(t))$ is itself a result:
$s approx 1$ indicates correct metric-scale recovery.

A related closed-form absolute-orientation solution also recovers rotation, translation, and scale
via unit quaternions @Horn87. Umeyama's SVD-based formulation differs chiefly in guaranteeing a
proper, non-reflected rotation through an explicit determinant-correction term, which matters for
degenerate or near-planar point configurations where a naive SVD fit can otherwise yield a
reflection instead of a rotation.

// TODO: verify the determinant-correction distinction directly against Umeyama (1991) before submission -- stated here from established point-cloud-registration literature, not from a re-read of the primary source in this session.

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
tests by matching frame names of the form `advio_*_world`. In the given datasets only ADVIO references receive
it, while TUM RGB-D and Record3D use the unconstrained fit (the trajectory-evaluation results below
discuss a case where this gate did not fire on ADVIO). <sec:gravity-alignment>

This gravity-aware trajectory alignment changes the reported metric and is unrelated to the separate
RANSAC ground-plane fit used only to orient the point-cloud viewer for display. the latter never
affects a reported trajectory or dense-geometry metric.

== Metrics: APE and RPE

For comparison of the VSLAM methods, two types of metrics are calculated within the pipeline.

Let $bold(T)_i$ and $hat(bold(T))_i$ denote the associated, Sim(3)-aligned reference and estimated
poses. Absolute pose error (APE) measures global placement,

$
  bold(e)_i^"ape" = op("trans")(bold(T)_i^(-1) hat(bold(T))_i),
  quad
  "RMSE"_"ape" = sqrt(frac(1, n) sum_i norm(bold(e)_i^"ape")^2),
$

and reflects the error over the whole trajectory. The APE can point out accumulated drift accross the trajectory
and is a indicator for the methods loop-closure quality. Relative pose error (RPE) instead
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

== Trajectory Evaluation Results

The final local evidence set is the `benchmark-18` expirement. The experiment ran MASt3R-SLAM and
ViSTA-SLAM on 6 scenes per dataset, leading to a total of 18 scenes. LingBot-Map is not part of this sweep.
@tab:trajectory-results reports matched-scene medians -- for ADVIO and Record3D only scenes both methods completed are
compared, so that one method's failed runs are not silently excluded from just its own column. All
values are Sim(3)-aligned RMSE and therefore measure trajectory-shape agreement rather than raw
metric-scale accuracy, which is reported separately below. Medians are used because a single
diverged sequence otherwise dominates the mean (e.g. ViSTA-SLAM on ADVIO: mean 15.3 m versus median
8.4 m); with only four to six sequences per dataset, these remain point estimates without confidence
intervals, and a superiority claim requires the full originally-planned matrix.

Regarding stability of the methods, ViSTA-SLAM completed all 18 runs, while MASt3R-SLAM completed only 15 of 18. MASt3R-SLAM fails on the three longest
sequences (two ADVIO, one Record3D) with an identical out-of-bounds error. MASt3R-SLAM's keyframe
buffer is fixed in size, so runs executed without a frame cap can overflow it. This is an
architectural ceiling rather than a tuning fault @murai2025mast3rslam. ViSTA-SLAM instead subsamples
to a bounded number of keyframes, trading accuracy for robustness rather than failing outright
@zhang2026vistaslam. The same mechanism reappears in the length-crossover analysis below.


#figure(
  {
    set text(size: 7.4pt)
    table(
      columns: (0.72fr, 0.32fr, 0.58fr, 0.72fr, 0.72fr),
      align: (left, right, left, right, right),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.28em,
      toprule(),
      table.header([Dataset], [$n$], [Method], [APE t / rot], [RPE t / rot]),
      midrule(),
      [TUM RGB-D], [6], [MASt3R], [0.05 m / 2.3#sym.degree], [0.09 m / 2.0#sym.degree],
      [], [], [ViSTA], [0.14 m / 6.1#sym.degree], [0.17 m / 3.9#sym.degree],
      [Record3D], [5], [MASt3R], [1.97 m / 6.0#sym.degree], [0.41 m / 1.2#sym.degree],
      [], [], [ViSTA], [2.02 m / 7.9#sym.degree], [2.03 m / 4.6#sym.degree],
      [ADVIO], [4], [MASt3R], [5.4 m / 88#sym.degree], [4.2 m / 7.0#sym.degree],
      [], [], [ViSTA], [17.3 m / 112#sym.degree], [4.3 m / 13.5#sym.degree],
      bottomrule(),
    )
  },
  caption: [Matched-scene trajectory medians from local `benchmark-18` sweep summaries; raw metric files are not checked into the manuscript source tree.],
) <tab:trajectory-results>

On TUM RGB-D both methods succeed, with MASt3R-SLAM delivering roughly three times more accurate results.
The TUM RGB-D scenes have short trajectories (6--16 m),  that are slow, and richly textured, favoring MASt3R-SLAM's dense two-view matching and
global optimization. ViSTA-SLAM's specific weak point within TUM RGB-D is rotation-heavy motion
(`freiburg1_360`), where its APE rotation is falling behind MAST3R. On Record3D, global
accuracy (APE) is nearly tied, but MASt3R-SLAM's local drift (RPE) is roughly five times lower. Following the APE metric,
this difference would not be visible, which is why both metrics are reported jointly above. On
ADVIO both methods fail, dominated by rotation (88°--112° APE rotation) with RPE
translation near 4 m per metre traveled. Part of this is attributable to
#link(<sec:advio-gate>)[the alignment-gate issue discussed below],
but low-tilt runs still show comparable rotation error, so genuine long-walk drift dominates and the
alignment issue only compounds it.

On Record3D, where capture style is held constant and path length is close to the only free
variable, the ViSTA-SLAM/MASt3R-SLAM APE ratio changes monotonically with ground-truth path length
and crosses over near 60--90 m: MASt3R-SLAM wins on short trajectories while ViSTA-SLAM performs better above 60--90m, and its
margin widens with length. The mechanism matches the robustness result above: MASt3R-SLAM's local
RPE is low on short scenes but rises sharply on the two longest Record3D scenes, while ViSTA-SLAM's
RPE stays flat across all lengths. This is the same fixed-keyframe-buffer mechanism identified in
the robustness result above, here showing up as an accuracy trend rather than an outright failure.
MASt3R-SLAM @murai2025mast3rslam tracks accurately while its buffer comfortably covers the scene,
then its local tracking quality collapses once a scene runs long enough to exhaust it. ViSTA-SLAM's
@zhang2026vistaslam fixed-size keyframe subsampling instead spreads a constant tracking budget
across arbitrarily long scenes, so its accuracy degrades gradually and stays bounded rather than
collapsing outright.
TUM RGB-D lies entirely below the crossover length, which is why ViSTA-SLAM never wins
there. ADVIO @cortes2018advio lies past it yet MASt3R-SLAM still wins, because ADVIO's failure is a
front-end tracking problem rather than a length-driven one.

The recovered scale $s$ reflects how well a method estimates absolute metric scale from monocular
input alone, without a calibrated baseline or external metric reference. $s approx 1$ indicates
correct recovery, while values far from 1 indicate systematic under- or over-scaling. Median
recovered $s$ is 0.94 for MASt3R-SLAM against 0.53 for ViSTA-SLAM on TUM RGB-D, 1.14 against 2.72 on Record3D, and 1.88
against 0.25 on ADVIO. MASt3R-SLAM stays within roughly 15% of correct metric scale on TUM RGB-D and
Record3D, consistent with its dense two-view prior, while ViSTA-SLAM's scale is dataset-dependent
and rarely close to one. On short, low-drift scenes, scale error accounts for most of the APE error,
so ViSTA-SLAM's under-scaling alone explains much of its TUM RGB-D accuracy gap; on long scenes
drift dominates over scale, so the correlation is weaker pooled across all three datasets.

The gravity-aware alignment #link(<sec:gravity-alignment>)[introduced above] is gated on the reference's target-frame name matching
`advio_*_world`; the `benchmark-18` ADVIO runs instead aligned to
`advio_fixedpoint_common_start_local`, so the gate did not fire and the unconstrained fit ran
instead. The persisted alignment metadata records elevated up-axis tilts for the affected runs,
consistent with the flipped-rotation failure mode motivated in the alignment section above. This is a partial explanation only: low-tilt runs still show approximately
84° APE rotation, so genuine long-walk drift dominates and the gate gap compounds rather
than causes the ADVIO rotation failure. <sec:advio-gate>

#figure(
  {
    set text(size: 7.4pt)
    table(
      columns: (0.75fr, 0.55fr, 0.55fr, 0.55fr, 0.55fr),
      align: (left, right, right, right, right),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.28em,
      toprule(),
      table.header([ADVIO source], [APE t (m)], [APE rot], [RPE t (m)], [RPE rot]),
      midrule(),
      [ARCore], [1.48], [13.0#sym.degree], [0.39], [1.0#sym.degree],
      [ARKit], [1.64], [10.5#sym.degree], [0.38], [0.36#sym.degree],
      [MASt3R-SLAM], [5.44], [88.1#sym.degree], [4.17], [7.0#sym.degree],
      [ViSTA-SLAM], [17.27], [111.9#sym.degree], [4.27], [13.5#sym.degree],
      bottomrule(),
    )
  },
  caption: [Local final-sweep summary of ADVIO registered provider baselines and monocular methods on the same matched scenes; raw metric files are not checked into the manuscript source tree.],
) <tab:advio-baselines>

ADVIO also provides registered ARCore and ARKit trajectories as candidates against the same ground
truth, evaluated on the same matched scenes as @tab:trajectory-results (@tab:advio-baselines)
@cortes2018advio. These mobile visual-inertial odometry (VIO) systems fuse the camera with the
phone's gyroscope and accelerometer, and outperform both monocular methods by roughly 3--12x in
translation and 8--10x in rotation. The IMU covers three weaknesses of monocular VSLAM methods.
The metric scale and the gravity direction lead to less estimation faults. Furthermore it is blur-robust through fast turns.
This does not make the vision-only methods worse in an absolute sense as they solve a strictly harder, uncalibrated and IMU-free problem.
ARCore and ARKit are themselves not ground truth, sitting roughly 1--2% of path length off the reference.
