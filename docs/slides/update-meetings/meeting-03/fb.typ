#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP2],
  [Florian Beck],
  [Set up local pipeline, downloaded datasets, evaluated Open3D TSDF, and started viz component.],
)

#let challenges_table_row = (
  [WP2 / WP4],
  [Florian Beck],
  [#lorem(10)],
)

#let next_steps_table_row = (
  [WP3 / WP4],
  [Florian Beck],
  [#lorem(10)],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: What Was Done?])[
    - Familiarized with the underlying infrastructure (Rerun and Streamlit).
    - Set up the pipeline so it runs successfully locally.
    - Downloaded the necessary datasets.
    - Evaluated TSDF Integration from Open3D (targeting noise reduction and surface smoothing).
    - Started implementing the first pipeline component (data sink for visualization).
    #v(0.8em)
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.6cm,
      [*Input Surface* \ Raw video + ARCore baseline logs],
    )
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: Challenges])[
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: Next Steps])[
  ]
]
