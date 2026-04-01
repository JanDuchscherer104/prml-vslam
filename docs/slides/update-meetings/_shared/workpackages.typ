
#import "@preview/booktabs:0.0.4": *

#let work_packages = (
  ([WP1], [Repository and environment scaffolding], [Ja ]),
  ([WP2], [Data capture and ARCore logging workflow], [?]),
  ([WP3], [Method integration], [?]),
  ([WP4], [Trajectory evaluation], [?]),
  ([WP5], [Dense reconstruction evaluation], [?]),
  ([WP6], [Reference reconstruction pipeline], [?]),
  ([WP7], [Benchmarking and reporting], [?]),
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
