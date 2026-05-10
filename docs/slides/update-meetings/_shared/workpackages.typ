
#import "@preview/booktabs:0.0.4": *

#let work_packages = (
  ([WP0], [Project organisation and issue tracking], [VB]),
  ([WP1], [Video source: ADVIO, Record3D, TUM, and own dataset], [JD / LR]),
  ([WP2.1], [Implementation of configurable Pipeline Framework], [FB / JD]),
  ([WP2.2], [ViSTA-SLAM], [LR / JD]),
  ([WP2.3], [MASt3R-SLAM], [CK]),
  ([WP3], [Incremental 3D reconstruction (TSDF #sym.arrow 3DGS)], [FB]),
  ([WP4.1], [Performance Metrics - Component Throughput], [FB]),
  ([WP4.2], [Trajectory Evaluation (evo)], [VB]),
  ([WP4.3], [Point Cloud Evaluation], [VB / JD / FB]),
  ([WP4.4], [Metrics: output-image quality], [CK]),
  ([WP5], [Benchmarking and reporting], [Shared]),
  ([WP6], [Optional ground-truth creation (uncalibrated & unposed sequences)], [Open]),
  ([WP7], [Optional ARCore baseline], [Open]),
)

#let work_packages_table() = [
  #show: booktabs-default-table-style
  #show table.cell: set text(size: 13pt)
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
