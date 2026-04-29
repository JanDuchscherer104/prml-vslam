#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  ([WP4.2], [VB], [Trajectory Evaluation (evo)]),
  ([WP2], [VB], [Fixed trajectory scaling issues (compressed VISTA trajectory)]),
)

#let challenges_table_row = (
  ([WP4.2], [VB], [Pipeline Setup on WSL (memory issues) => implemented evo on static artifacts, issues fixed meanwhile])
)

#let next_steps_table_row = (
  ([WP4.3], [Point Cloud Evaluation], [VB / JD / FB])
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: What was done?])[
    - Implemented trajectory APE translation evaluation with evo
    - Trajectory Evaluation is configurable in Pipeline
    - Implemented stage alignment (trajectory scaling issues between ground truth and VISTA-SLAM 1/4.2)
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: Challenges])[
    - running the pipeline within WSL crashed multiple times
    - crashes were hard to trace
    - heavy changes of pipeline during implementation of evaluation led to multiple adaptions
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Valentin Bumeder: Next Steps])[
    - Implement further trajectory metrics
      - APE rotation
      - RPE translation
      - RPE rotation
    - Implement point cloud metrics
  ]
]
