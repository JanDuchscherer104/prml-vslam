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
