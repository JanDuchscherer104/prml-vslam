#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Experimental Protocol

An experiment must be reconstructable from its configuration and artifact root. A run records the
source sequence, sampling policy, method backend, output policy, alignment mode, reference source,
point-cloud registration settings, hardware-relevant method configuration, and visualization
policy. Each terminal stage emits a typed result and durable artifact references, so later analysis
does not depend on app state, ad hoc paths, or viewer screenshots.

For quantitative reporting, the unit of evidence is a method-dataset run with a complete artifact
set. A trajectory result requires the normalized source manifest, method trajectory, reference
trajectory, association rule, alignment metadata, and metric manifest. A dense-geometry result
requires a method cloud, reference cloud, global placement, local registration metadata when used,
and the final dense metric table. Runtime and memory measurements require a separate efficiency
instrumentation path and are not inferred from ordinary command logs.

Artifact completeness is a reporting criterion. A run is excluded from a quantitative table if the
selected reference trajectory is missing, if candidate and reference target frames lack an explicit
transform, if timestamp association falls below the configured coverage threshold, if the dense
reference cloud is absent for a dense-geometry metric, or if sampling, resizing, or intrinsics
change without metadata. These exclusions prevent stale datastore entries and rendered previews from
becoming evidence.

The metric stages therefore consume normalized artifacts rather than dataset-native files or
preview outputs. Trajectory metrics are admissible only when the candidate and reference
trajectories share the selected target frame and pass timestamp association. Dense-geometry metrics
are admissible only after global placement and after the reference-cloud sampling policy,
intrinsics, pose provenance, ICP threshold, and inlier statistics are recorded with the artifact.

#figure(
  table(
    columns: (0.72fr, 1.45fr, 1.6fr),
    align: (left, left, left),
    inset: (x: 0.24em, y: 0.24em),
    column-gutter: 0.38em,
    toprule(),
    table.header([Dataset], [Evidence package], [Validation boundary]),
    midrule(),
    [ADVIO],
    [Smartphone trajectory benchmark with RGB frames, timestamps, intrinsics, and reference trajectories.],
    [Report trajectory metrics only after the reference source and alignment mode are frozen.],
    [TUM RGB-D],
    [Controlled trajectory and dense-reference benchmark with RGB replay, motion-capture trajectory, and registered-depth cloud.],
    [Use the same frame sampling policy for trajectory and cloud artifacts.],
    [Record3D],
    [Custom smartphone capture path with RGB-D archive or live stream, ARKit poses, and depth-derived cloud.],
    [Treat ARKit as a provider reference rather than laboratory ground truth.],
    bottomrule(),
  ),
  caption: [Protocol matrix for benchmark reporting. The table specifies evidence requirements rather than numerical results.],
) <tab:experiment-protocol>

The protocol separates validation of the measurement substrate from method ranking. Source
normalization, method execution, trajectory association, and transform visualization are necessary
but not sufficient for superiority claims. Such claims require a frozen matrix of datasets,
sequences, sampling policies, method configurations, and metric artifacts.

= Trajectory Evaluation Results

The final local evidence set is the `benchmark-18` sweep: MASt3R-SLAM and ViSTA-SLAM on 18 scenes (6
TUM RGB-D, 6 ADVIO, 6 Record3D); LingBot-Map is not part of this sweep. @tab:trajectory-results
reports matched-scene medians -- for ADVIO and Record3D only scenes both methods completed are
compared, so that one method's failed runs are not silently excluded from just its own column. All
values are Sim(3)-aligned RMSE and therefore measure trajectory-shape agreement rather than raw
metric-scale accuracy, which is reported separately below. Medians are used because a single
diverged sequence otherwise dominates the mean (e.g. ViSTA-SLAM on ADVIO: mean 15.3 m versus median
8.4 m); with only four to six sequences per dataset, these remain point estimates without confidence
intervals, and a superiority claim requires the full originally-planned matrix (@tab:experiment-protocol).

ViSTA-SLAM completed all 18 runs; MASt3R-SLAM completed 15 of 18, failing on the three longest
sequences (two ADVIO, one Record3D) with an identical out-of-bounds error. MASt3R-SLAM's keyframe
buffer is fixed in size, so runs executed without a frame cap can eventually overflow it -- an
architectural ceiling rather than a tuning fault @murai2025mast3rslam. ViSTA-SLAM instead subsamples
to a bounded number of keyframes, trading accuracy for robustness rather than failing outright
@zhang2026vistaslam. The same mechanism reappears in the length-crossover analysis below.

// TODO: confirm and cite the exact keyframe-buffer-size / max-view-num config values from `.configs/templates/mast3r-slam.toml` and `.configs/templates/vista-slam.toml` before finalizing.

// Figure: Trajectory Evaluation Results.

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

On TUM RGB-D both methods succeed, with MASt3R-SLAM roughly three times more accurate; the scenes
are short (6--16 m), slow, and richly textured, favoring MASt3R-SLAM's dense two-view matching and
global optimization. ViSTA-SLAM's specific weak point within TUM RGB-D is rotation-heavy motion
(`freiburg1_360`), where its APE rotation is an order of magnitude worse. On Record3D, global
accuracy (APE) is nearly tied, but MASt3R-SLAM's local drift (RPE) is roughly five times lower --
APE alone would hide this difference, which is why both metrics are reported jointly above. On
ADVIO both methods fail, dominated by rotation (88°--112° APE rotation) with RPE
translation near 4 m per metre traveled; part of this is attributable to the alignment issue below,
but low-tilt runs still show comparable rotation error, so genuine long-walk drift dominates and the
alignment issue only compounds it.

On Record3D, where capture style is held constant and path length is close to the only free
variable, the ViSTA-SLAM/MASt3R-SLAM APE ratio changes monotonically with ground-truth path length
and crosses over near 60--90 m: MASt3R-SLAM wins below this length, ViSTA-SLAM wins above it, and its
margin widens with length. The mechanism matches the robustness result above: MASt3R-SLAM's local
RPE is low on short scenes but rises sharply on the two longest Record3D scenes, while ViSTA-SLAM's
RPE stays flat across all lengths -- a fixed-buffer accuracy cliff versus graceful, bounded
degradation. TUM RGB-D lies entirely below the crossover length, which is why ViSTA-SLAM never wins
there; ADVIO lies past it yet MASt3R-SLAM still wins, because ADVIO's failure is a front-end tracking
problem rather than a length-driven one.

// TODO: with n=5 Record3D scenes this is a trend, not a significant result -- add the per-scene length/APE table or scatter figure (source: per-sequence APE and path length from `dataset_aggregation.py`/`trajectories.py`) if space allows.

Recovered Sim(3) scale $s$ is a first-class result for an uncalibrated pipeline. Median $s$ is 0.94
for MASt3R-SLAM against 0.53 for ViSTA-SLAM on TUM RGB-D, 1.14 against 2.72 on Record3D, and 1.88
against 0.25 on ADVIO. MASt3R-SLAM stays within roughly 15% of correct metric scale on TUM RGB-D and
Record3D, consistent with its dense two-view prior, while ViSTA-SLAM's scale is dataset-dependent
and rarely close to one. On short, low-drift scenes, scale error accounts for most of the APE error,
so ViSTA-SLAM's under-scaling alone explains much of its TUM RGB-D accuracy gap; on long scenes
drift dominates over scale, so the correlation is weaker pooled across all three datasets.

The gravity-aware alignment introduced above is gated on the reference's target-frame name matching
`advio_*_world`; the `benchmark-18` ADVIO runs instead aligned to
`advio_fixedpoint_common_start_local`, so the gate did not fire and the unconstrained fit ran
instead. The persisted alignment metadata records elevated up-axis tilts for the affected runs,
consistent with the flipped-rotation failure mode motivated in the alignment section above. This is a partial explanation only: low-tilt runs still show approximately
84° APE rotation, so genuine long-walk drift dominates and the gate gap compounds rather
than causes the ADVIO rotation failure.

// TODO: confirm and cite the exact recorded up-axis-tilt values (degrees) and affected sequence IDs from the frozen `benchmark-18` `trajectory_alignment.json` artifacts before finalizing this paragraph.

// Figure: ARCore & ARKit

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
translation and 8--10x in rotation. The IMU directly supplies three quantities that two-view vision
must otherwise infer from pixels alone: metric scale, the gravity/up direction -- exactly what the
gravity-aware alignment above must instead assume from frame metadata -- and blur-robust high-rate
rotation tracking through fast turns. This does not make the vision-only methods worse in an
absolute sense: they solve a strictly harder, uncalibrated and IMU-free problem, and ARCore/ARKit
are themselves not ground truth, sitting roughly 1--2% of path length off the reference.

// TODO: cite a dedicated VIO-mechanism source for the scale/gravity/blur-robustness claim above (see REPORT_PLAN_TRAJECTORY_EVALUATION.md Part C.4 -- unverified candidate: Mourikis & Roumeliotis, MSCKF 2007).

// ------------------------------------------- Point Cloud -----------------------------------------

= Point Cloud Evaluation Results

Dense-cloud evaluation is available only where a reference cloud exists. @tab:dense-cloud-results
therefore excludes ADVIO and reports local final-sweep summaries of completed post-ICP Sim(3) cloud
metrics for TUM RGB-D and Record3D. Chamfer is lower-is-better and F1 is computed at the 5 cm
tolerance defined in @tab:alignment-protocol and the metric equations above.

#figure(
  {
    set text(size: 7.4pt)
    table(
      columns: (0.72fr, 0.65fr, 0.34fr, 0.58fr, 0.48fr),
      align: (left, left, right, right, right),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.28em,
      toprule(),
      table.header([Dataset], [Method], [Runs], [Chamfer (m)], [$F_1$]),
      midrule(),
      [TUM RGB-D], [MASt3R], [6], [0.074], [0.850],
      [], [LingBot], [6], [0.124], [0.686],
      [], [ViSTA], [6], [0.143], [0.546],
      [Record3D], [MASt3R], [5], [1.876], [0.163],
      [], [ViSTA], [6], [2.203], [0.100],
      [ADVIO], [both], [0], [n/a], [n/a],
      bottomrule(),
    )
  },
  caption: [Median dense-cloud metrics from local final-sweep cloud summaries; raw metric files are not checked into the manuscript source tree.],
) <tab:dense-cloud-results>

The dense-cloud table reinforces the dataset distinction. TUM RGB-D gives the cleanest reference
surface and the strongest overlap scores, with MASt3R-SLAM highest at $F_1 = 0.850$. LingBot-Map is
included only for the six TUM RGB-D cloud runs, where its $F_1 = 0.686$ sits between MASt3R-SLAM
and ViSTA-SLAM; the table is therefore also the dense-geometry inclusion record. Record3D is
harder: both methods produce lower overlap against an ARKit/LiDAR-derived provider reference rather
than laboratory ground truth, and MASt3R-SLAM is better but still far from the TUM regime. ADVIO is
trajectory-only in this evidence set because no benchmark-store dense reference cloud is available.

The local evidence set also includes render-based image diagnostics on ADVIO `advio-15`. The raw
render metric files are not checked into the manuscript source tree. The renderer projects the dense
cloud from estimated poses into the image plane and scores only filled pixels, so the metrics in
@tab:render-diagnostics must be read with coverage. They are useful for comparing two methods on
the same sequence, but they are not a substitute for trajectory or dense-cloud geometry metrics.

#figure(
  {
    set text(size: 7.4pt)
    table(
      columns: (0.78fr, 0.42fr, 0.45fr, 0.5fr, 0.45fr, 0.42fr),
      align: (left, right, right, right, right, right),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.26em,
      toprule(),
      table.header([Method], [Pairs], [Coverage], [PSNR], [SSIM], [L1]),
      midrule(),
      [ViSTA-SLAM], [357], [0.79], [10.8], [0.10], [0.19],
      [MASt3R-SLAM], [154], [0.63], [11.2], [0.07], [0.18],
      bottomrule(),
    )
  },
  caption: [Local render-based image diagnostics on ADVIO `advio-15`; scores average over filled pixels and raw metric files are not checked into the manuscript source tree.],
) <tab:render-diagnostics>

Local telemetry in @tab:runtime-telemetry gives the efficiency context for the same implementation
family. The raw telemetry rows are not checked into the manuscript source tree. The streaming rates
were measured on a single NVIDIA RTX 3080 GPU, AMD Ryzen 7 5700X CPU, and 32 GB RAM. ViSTA-SLAM is
faster in streaming FPS, while MASt3R-SLAM has competitive stage latency on TUM but much lower
accepted-keyframe throughput there. In the table, key-FPS denotes accepted-keyframe throughput. For
MASt3R-SLAM on ADVIO, the local sweep retained latency and accepted-keyframe throughput but no
comparable streaming-FPS row, so stream FPS is reported as n/a. The table keeps these numbers
separate from accuracy because they come from runtime telemetry, not the trajectory metric record.

#figure(
  {
    set text(size: 7.4pt)
    table(
      columns: (0.65fr, 0.6fr, 0.55fr, 0.55fr, 0.55fr),
      align: (left, left, right, right, right),
      inset: (x: 0.18em, y: 0.18em),
      column-gutter: 0.26em,
      toprule(),
      table.header([Method], [Dataset], [stream FPS], [latency (ms)], [key-FPS]),
      midrule(),
      [ViSTA], [TUM RGB-D], [82.7], [115.5], [2.99],
      [ViSTA], [Record3D], [62.2], [12.6], [1.73],
      [MASt3R], [TUM RGB-D], [17.4], [52.7], [0.48],
      [MASt3R], [Record3D], [16.3], [59.3], [0.84],
      [MASt3R], [ADVIO], [n/a], [165.5], [2.78],
      bottomrule(),
    )
  },
  caption: [Local runtime telemetry for the final implementation on one workstation; raw telemetry rows are not checked into the manuscript source tree.],
) <tab:runtime-telemetry>
