#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [LR],
  [ViSTA-SLAM integration and pipeline execution],
)
#let challenges_table_row = (
  [LR],
  [Streaming lifecycle and upstream runtime setup],
)
#let next_steps_table_row = (
  [LR],
  [Execution cleanup and ADVIO validation],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: What Was Done?])[
    - Integrated ViSTA-SLAM for offline and streaming pipeline execution.
    - Added repo-owned `plan-run-config` and `run-config` workflow around the shared pipeline services.
    - Stabilized streaming stop and failure handling so previews and artifacts remain visible at terminal states.
    - Built and linked DBoW3Py for loop-detection support in the ViSTA integration.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Challenges])[
    - Aligning upstream ViSTA runtime prerequisites and optional dependencies with the repo bootstrap.
    - Keeping backend-specific worker code separate from pipeline-owned streaming orchestration.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Next Steps])[
    - Move process orchestration and packet transport behind pipeline-owned execution seams.
    - Run end-to-end ADVIO streaming validation and capture remaining regressions.
    - Restore the pipeline docs so they match the final execution architecture.
  ]
]
