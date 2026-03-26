#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let proposal_detail_body = items => [
  #meeting_detail_slide(items, title: [Christopher Kirschner: Proposal Notes])[
    *Work Package* \
    - Read `@murai2025mast3rslam` and summarize the integration-relevant assumptions for the
      benchmark wrapper.

    *Challenges* \
    - #lorem(14)

    *Next Steps* \
    - #lorem(12)
  ]
]
