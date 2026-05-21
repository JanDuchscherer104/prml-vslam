#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP4],
  [Florian Beck],
  [Implemented point cloud evaluation with Open3D overlap/RMSE, Chamfer distance, and percentage-based F-score.],
)

#let challenges_table_row = (
  [WP2 / WP4],
  [Florian Beck],
  [Mixed SE(3) and Sim(3) point cloud poses cause a scaling mismatch.],
)

#let next_steps_table_row = (
  [WP2 / WP4],
  [Florian Beck],
  [Fix pose scaling and continue streaming-mode reconstruction beyond ground-truth input.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: What Was Done?])[
    - Implemented point cloud evaluation: Open3D thresholded nearest-neighbor overlap + RMSE, Chamfer distance, and percentage-based F-score.
    - Tested the metrics on synthetic point clouds and explored an early stochastic comparison approach.
    - Started streaming-mode reconstruction; current pipeline still uses ground-truth data.

    #v(0.6em)
    #grid(
      columns: (1fr, 1fr, 1fr),
      gutter: 0.35cm,
      [
        #figure(
          image("../../../figures/pointcloud/pointcloud_comparison.png", width: 100%),
          caption: [Open3D overlap + RMSE],
        ) <m04-fb-open3d>
      ],
      [
        #figure(
          image("../../../figures/pointcloud/chamfer_distance.png", width: 100%),
          caption: [Chamfer distance],
        ) <m04-fb-chamfer>
      ],
      [
        #figure(
          image("../../../figures/pointcloud/fscore.png", width: 100%),
          caption: [F-score],
        ) <m04-fb-fscore>
      ],
    )
  ]
]

#let challenges_detail_body = none

#let next_steps_detail_body = none
