
#import "@preview/booktabs:0.0.4": *

#let work_packages = (
  ([WP1], [Repository and environment scaffolding], [Jan]),
  ([WP2], [Data capture and ARCore logging workflow], [Christopher]),
  ([WP3], [Method integration], [Florian]),
  ([WP4], [Trajectory evaluation], [Lukas]),
  ([WP5], [Dense reconstruction evaluation], [Valentin]),
  ([WP6], [Reference reconstruction pipeline], [Jan]),
  ([WP7], [Benchmarking and reporting], [Florian]),
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
