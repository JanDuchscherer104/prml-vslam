#import "../template.typ": *

#slide(title: [Point-Cloud Completeness: Reference → Estimate])[
  #set text(size: 12.2pt)
  #grid(
    columns: (1.7fr, 0.65fr),
    gutter: 0.45cm,
    [
      #figure(
        image("../../figures/pointcloud/metric_schematics/pointcloud_completeness.svg", width: 93%),
        caption: [Completeness: each reference point queries its nearest estimate.],
      )
    ],
    [
      #block(fill: rgb("eaf2ff"), stroke: 0.7pt + rgb("bfd2f0"), radius: 8pt, inset: 0.5em)[
        #text(weight: "semibold")[Metric]\
        #text(size: 10.5pt)[$ "completeness" = "mean"(R arrow.r E) $]
      ]

      #v(0.35em)
      - Query points: reference cloud $R$.
      - Target: estimate cloud $E$.
      - Lower is better.
      - Catches missing scene regions.

      #v(0.3em)
      #block(fill: rgb("fff1f1"), stroke: 0.6pt + rgb("ecc4c4"), radius: 6pt, inset: 0.45em)[
        Long distances mean missing surface coverage.
      ]
    ],
  )
]
