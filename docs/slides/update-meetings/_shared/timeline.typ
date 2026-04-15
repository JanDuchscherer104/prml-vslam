#import "@preview/booktabs:0.0.4": *

#let timeline = [
  #show: booktabs-default-table-style
  #table(
    columns: (auto, auto, auto),
    inset: 8pt,
    align: (center, center, left),
    [*Weeks*], [*Target*], [*Milestones / Scope*],
    toprule(), [1], [26.03],
    [Repo bootstrap, work package split, report and slide setup.],

    [2-6],
    [29.04],
    [
      Implement full-stack configurable pipeline:
      - Recod3D streaming & ADVIO dataset fully integrated
      - freeze pipeline framework & interfaces
      - implemented ViSTA SLAM & #link("https://rerun.io/")[rerun viewer]
      - performance metrics
      - trajectory and dense reconstruction benchmarking.
    ],

    [7-9], [25.04], [ViSTA, MASt3R are fully integrated. TSDF reconstuction & 3D viewer are ready.],

    [10-12], [11.06], [ADVIO plus custom-data evidence, multiprocessing (& distributed) pipeline, 3DGS integration.],

    [13-15], [02.07], [Finalization, preparation of report & presentation.],
    bottomrule(),
  )
]
