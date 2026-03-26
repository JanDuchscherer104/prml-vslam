#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP3 / WP4 / WP5],
  [Jan Duchscherer],
  [Consolidated benchmark surfaces for trajectories, dense clouds, and runtime metrics.],
)

#let challenges_table_row = (
  [Benchmark Integration],
  [Jan Duchscherer],
  [External method repos, dense alignment assumptions, and runtime comparability still dominate risk.],
)

#let next_steps_table_row = (
  [WP6 / WP7],
  [Jan Duchscherer],
  [Build the reference pipeline and turn benchmark findings into report and presentation material.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: What Was Done?])[
    - Consolidated the benchmark surfaces for trajectories, dense point clouds, and runtime metrics.
    - Structured the reporting surfaces so final benchmarking results can flow directly into slides
      and the final report.
    - Locked the initial issue-ready work package split for execution.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Challenges])[
    - The benchmark still depends on external method repos that are not installed by default.
    - Dense evaluation requires careful reference reconstruction and alignment assumptions.
    - Runtime comparisons remain sensitive to hardware, preprocessing, and export conventions.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Next Steps])[
    - Build the first reference reconstruction pipeline for custom recordings.
    - Run side-by-side trajectory and point-cloud comparisons for the first integrated methods.
    - Convert benchmark findings into the final presentation and report.
  ]
]
