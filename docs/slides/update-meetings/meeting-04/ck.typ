#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let done_table_row = (
  [WP3],
  [CK],
  [MASt3R-SLAM-Adapter auf neue Repo-Architektur portiert;],
)
#let challenges_table_row = (

)
#let next_steps_table_row = (
  [WP3 / WP7],
  [CK],
  [Output Images Vergleich; ViSTA-Vergleich;],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: MASt3R-SLAM — Stand der Integration])[
    == Adapter auf neue Architektur portiert
    - Adapter musste auf das neue `SlamBackend`-Protokoll
      umgeschrieben werden — strukturell analog zur ViSTA-Integration.
  ]
]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Challenges])[

  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Next Steps])[
    == Metrics Output Images
    - PSNR
    - Andere Metriken (SSIM, L1)

  ]
]

#let proposal_detail_body = none
