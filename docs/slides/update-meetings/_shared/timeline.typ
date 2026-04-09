#import "@preview/booktabs:0.0.4": *

#let timeline = [
  #show: booktabs-default-table-style
  #show table.cell.where(y: 0): set text(weight: "bold")
  #table(
    columns: (1.45fr, 1.9fr, 4.65fr),
    align: (left, left, left),
    inset: (x: 0.4em, y: 0.28em),
    toprule(),
    table.header([Date], [Milestone], [What must be ready]),
    midrule(),

    [15 Apr 2026],
    [Proposal freeze],
    [Goals, work packages, ownership, interaces & mocks are fixed for parallel execution.],

    [29 Apr 2026], [Benchmark baseline], [Planning, artifacts, ADVIO, first VSLAM integration, pipeline clean up.],

    [22 May 2026],
    [Method integration],
    [ViSTA, MASt3R are fully integrated. TSDF reconstuction & 3D viewer are ready.],

    [12 Jun 2026],
    [First Comparison + Pipeline],
    [ADVIO plus custom-data evidence, multiprocessing support, maybe mps integration.],

    [29 Jun 2026],
    [Presentation freeze],
    [Final narrative, methodology, results, future work, retrospective, and presentation breakdown are frozen.],

    [30 Jun-2 Jul 2026],
    [Final challenge delivery],
    [Presentable demo, stable results, and the final slide deck are ready for presentation.],

    [3 Jul 2026],
    [Report and repo freeze],
    [Report, code, benchmark outputs, and the final repository state are frozen.],

    bottomrule(),
  )
]
