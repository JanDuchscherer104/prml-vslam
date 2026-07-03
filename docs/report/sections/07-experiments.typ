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
