#import "@preview/booktabs:0.0.4": toprule, midrule, bottomrule

= Experimental Protocol

The implementation is designed so that an experiment can be reconstructed from its configuration and
artifact root. A run records the source sequence, sampling policy, method backend, output policy,
alignment mode, reference source, point-cloud registration settings, hardware-relevant method
configuration, and visualization policy. Each terminal stage produces a typed result and durable
artifact references. This prevents later analysis from depending on app state, ad hoc paths, or
viewer screenshots.

For quantitative reporting, the unit of evidence is a method-dataset run with a complete artifact
set. A trajectory result requires the normalized source manifest, method trajectory, reference
trajectory, association rule, alignment metadata, and metric manifest. A dense-geometry result
requires a method cloud, reference cloud, global placement, local registration metadata when used,
and the final dense metric table. Runtime and memory measurements require a separate efficiency
instrumentation path and are not inferred from ordinary command logs.

Artifact completeness is a reporting criterion, not an implementation preference. A run is excluded
from a quantitative table if the selected reference trajectory is missing, if the candidate and
reference target frames cannot be matched through an explicitly recorded transform, if timestamp
association falls below the configured coverage threshold, if a dense reference cloud is absent for a
dense-geometry metric, or if the method backend changes image sampling, resizing, or intrinsics
without recording that change in the artifact metadata. These exclusions prevent partially rendered
viewer output or stale datastore entries from becoming scientific evidence.

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

This protocol intentionally separates framework validation from method ranking. It is already useful
to verify that a source can be normalized, a method can run on the normalized stream, a trajectory can
be associated with a prepared reference, and the resulting transforms can be visualized without
changing the scientific artifact. It is not sufficient to claim that one method is better than
another. Such claims require a frozen matrix of datasets, sequences, sampling policies, method
configurations, and metric artifacts.
