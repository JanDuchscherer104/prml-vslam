#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP2.2],
  [LR],
  [ViSTA-SLAM implementation in Streamlit runtime],
)
#let challenges_table_row = (
  [WP2.{1,2}],
  [LR],
  [Runtime orchestration and environment setup],
)
#let next_steps_table_row = (
  [WP1 / WP2.1],
  [LR, JD],
  [Async stability and streaming validation],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: What Was Done?])[
    - Integrated ViSTA-SLAM into the Streamlit pipeline page as the active backend path.
    - Implemented async execution flow so long-running steps do not block the app UI.
    - Added rerun-safe state handling so results persist correctly across Streamlit reruns.
    - Wired the CLI `run` command and Streamlit pipeline flow to share the same runtime behavior.
    - Built and linked DBoW3Py for loop-detection support in the integrated pipeline.
  ]
]


#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Challenges])[
    - Main effort was coordinating async task lifecycle with Streamlit rerun semantics.
    - Environment was standardized via Conda to keep builds and runtime behavior consistent.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Lukas Röß: Next Steps])[
    - Harden async + rerun behavior under repeated user interactions.
    - Run full streaming validation on ADVIO sequences and capture regressions.
    - Finalize reproducible Conda setup notes for smoother team onboarding.
  ]
]

