#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  ([WP4.2], [VB], [Extended Trajectory Evaluation Metrics (evo)]),
  ([WP4.2], [VB], [Implemented Trajectory Metrics for multiple ground truths])
)

#let challenges_table_row = (
)

#let next_steps_table_row = (
  ([WP5], [All], [Benchmarking and Evaluation])
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: What was done?])[
    - extended trajectory evaluation with further metrics from evo
      - APE rotation variant
      - RPE translation
      - RPE rotation
    - Fixed Trajectory Metrics for multiple ground truths
    - Implemented Plots for Trajectory Metrics
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: Challenges])[
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: Next Steps])[
    - Benchmarking and Evaluation
  ]
]
