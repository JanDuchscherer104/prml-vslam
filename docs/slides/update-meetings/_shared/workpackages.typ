
#import "@preview/booktabs:0.0.4": *

#let work_packages = (
  ([WP0], [Project organisation and issue tracking], [VB]),
  ([WP1], [Video source: ADVIO, Record3D, TUM, and own dataset], [JD / LR]),
  ([WP2], [Pipeline framework and shared interfaces], [FB / JD]),
  ([WP3], [VSLAM methods: ViSTA-SLAM, MASt3R-SLAM], [JD / LR / CK]),
  ([WP4], [Incremental 3D reconstruction (TSDF #sym.arrow 3DGS)], [FB]),
  ([WP5], [Metrics: component throughput], [FB]),
  ([WP6], [Metrics: point-cloud comparison], [VB / JD / FB]),
  ([WP7], [Metrics: trajectory comparison], [LR / VB]),
  ([WP8], [Metrics: output-image quality], [CK]),
  ([WP9], [3D viewer integration], [Open]),
  ([WP10], [Optional ground-truth creation (uncalibrated & unposed sequences)], [Open]),
  ([WP11], [Optional ARCore baseline], [Open]),
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
