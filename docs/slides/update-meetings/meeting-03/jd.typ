#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP2],
  [Jan Duchscherer],
  [#lorem(10)],
)

#let challenges_table_row = (
  [WP2 / WP4],
  [Jan Duchscherer],
  [#lorem(10)],
)

#let next_steps_table_row = (
  [WP3 / WP4],
  [Jan Duchscherer],
  [#lorem(10)],
)

#let done_detail_body = items => [
  // #meeting_detail_slide(items, title: [Jan Duchscherer: What Was Done?])[
  //   - Refined the custom dataset requirements around raw video and ARCore baseline logs.
  //   - Aligned the evaluation surfaces with trajectory and dense reconstruction outputs.
  //   - Kept the slide and report templates synchronized with the benchmark structure.

  //   #v(0.8em)
  //   #grid(
  //     columns: (1fr, 1fr),
  //     gutter: 0.6cm,
  //     [*Input Surface* \ Raw video + ARCore baseline logs], image("../../../figures/hm-logo.svg"),
  //   )
  // ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Challenges])[
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Jan Duchscherer: Next Steps])[
  ]
]
