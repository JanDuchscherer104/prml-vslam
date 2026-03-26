#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let proposal_detail_body = items => [
  #meeting_detail_slide(items, title: [Florian Beck: Proposal Notes])[
    #grid(
      columns: (1.2fr, 0.8fr),
      gutter: 0.8cm,
      [
        #text(weight: "medium")[Template Content]
        #v(0.5em)
        #lorem(55)
      ],
      [
        #stack(
          dir: ttb,
          spacing: 0.6cm,
          figure(
            image("../../../figures/hm-logo.svg", width: 82%),
            caption: [Example image placeholder for a contributor-owned draft slide.],
          ),
          figure(
            image("../../../figures/hm-logo.svg", width: 52%),
            caption: [Second placeholder visual to exercise slide merging with figures.],
          ),
        )
      ],
    )
  ]
]

