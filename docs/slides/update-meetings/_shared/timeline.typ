#import "@preview/booktabs:0.0.4": *

#let timeline = [
  #table(
    columns: (10%, 15%, 75%),
    inset: 8pt,
    align: (center, center, left),
    [*Weeks*], [*Target*], [*Milestones / Scope*],
    [1], [26.03], [Repo bootstrap, work package split, report and slide setup.],
    [2-6], [29.04], [
      Implement full-stack configurable pipeline:
      - captured mobile client & ADVIO dataset
      - implemented 2 VSLAM methods
      - implemented live-output
      - performance metrics
      - trajectory and dense reconstruction benchmarking.
    ],
    [6], [29.04], [_Refinement of further steps._],
    [7-12], [11.06], [_Open_],
    [13-15], [02.07], [Finalization, preparation of report & presentation.],
  )
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
