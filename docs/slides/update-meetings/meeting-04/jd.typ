#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP2],
  [JD],
  [
    Ray pipeline and Rerun stabilization & fixes.
  ],
  [WP2],
  [JD],
  [Rerun: sub-sampling of heavy 3D entities],
  [WP2.2],
  [JD],
  [Reviewed MASt3R SLAM branch],
)

#let challenges_table_row = (
  [WP2],
  [JD],
  [Identifying compute bottleneck as main issue.],
)

#let next_steps_table_row = (
  [WP2],
  [JD],
  [Review and merge `feature/pointcloud-evaluation-fix-orientation`.],
  [WP2],
  [JD, LR],
  [Run full evaluation run (ViSTA, MASt3R) on TUM],
  [WP1],
  [JD],
  [Keep ADVIO trajectory-only and fix Record3D frame issues.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: Rerun & Pipeline Fixes])[
    - Added point-cloud and mesh sub-sampling for Rerun logging.
    - Split Rerun logging into separate live and export actors.
    - Improved coordinator shutdown & live-stream flushing so exports can finish.
    - Fixed streaming latency and throughput reporting.
    - Made the live camera frustum visible in Rerun.
  ]
]

#let challenges_detail_body = none

#let next_steps_detail_body = none
