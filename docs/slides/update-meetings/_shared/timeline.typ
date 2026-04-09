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

    [29 Apr 2026],
    [Benchmark baseline],
    [Planning, artifacts, finalize ADVIO, first VSLAM integration, pipeline clean up.],

    [22 May 2026],
    [Method integration],
    [ViSTA, MASt3R are fully integrated. TSDF reconstuction & 3D viewer are ready.],

    [12 Jun 2026],
    [Eval + Pipeline],
    [ADVIO plus custom-data evidence, multiprocessing (& distributed) pipeline, 3DGS integration.],

    [29 Jun 2026],
    [Report and repo freeze],
    [Report, code, benchmark outputs, and the final repository state are frozen.],

    bottomrule(),
  )
]
