#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP2],
  [Jan Duchscherer],
  [Refined custom dataset requirements and aligned capture outputs with evaluation surfaces.],
)

#let challenges_table_row = (
  [WP2 / WP4],
  [Jan Duchscherer],
  [Capture quality and output normalization remain the main benchmark risks.],
)

#let next_steps_table_row = (
  [WP3 / WP4],
  [Jan Duchscherer],
  [Produce normalized trajectory exports and benchmark the first ADVIO sequence.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: What Was Done?])[
    - Refined the custom dataset requirements around raw video and ARCore baseline logs.
    - Aligned the evaluation surfaces with trajectory and dense reconstruction outputs.
    - Kept the slide and report templates synchronized with the benchmark structure.

    #v(0.8em)
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.6cm,
      [*Input Surface* \ Raw video + ARCore baseline logs], image("../../../figures/hm-logo.svg"),
    )
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Challenges])[
    - Capture quality directly affects both ARCore baselines and later reconstruction fidelity.
    - Benchmark data must be reproducible enough for repeated method runs and alignment checks.
    - External tools differ in output conventions, so normalization remains a key risk.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Next Steps])[
    - Integrate the first method wrapper and produce normalized trajectory exports.
    - Benchmark the first sequence on ADVIO with `evo`.
    - Document the alignment policy for custom recordings and ARCore comparisons.
  ]
]
