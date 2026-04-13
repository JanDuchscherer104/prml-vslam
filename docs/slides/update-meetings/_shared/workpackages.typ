
#import "@preview/booktabs:0.0.4": *

#let work_packages = (
  ([WP1], [Dataset Acquisition (ADVIO & Client)], [Jan, Lukas]),
  ([WP2.1], [Implementation of configuraable Pipeline Framework], [Jan]),
  ([WP2.2], [ViSTA-SLAM], [Lukas]),
  ([WP2.3], [MASt3R-SLAM], [Christoph]),
  ([WP3], [Incremental Streaming (3DGS)], [Florian]),
  ([WP4.1], [Performance Metrics - Component Throughput], [Florian]),
  ([WP4.2], [Trajectory Evaluation (evo)], [Valentin]),
  ([WP4.3], [Point Cloud Evaluation], [Valentin]),
  ([WP5], [Benchmarking and reporting], [Shared]),
)

#let work_packages_table() = [
  #show: booktabs-default-table-style
  #table(
    columns: (1fr, 4fr, 1.8fr),
    align: (left, left, left),
    inset: (x: 0.4em, y: 0.28em),
    toprule(),
    table.header([ID], [Description], [Owner]),
    midrule(),
    ..work_packages.flatten(),
    bottomrule(),
  )
]
