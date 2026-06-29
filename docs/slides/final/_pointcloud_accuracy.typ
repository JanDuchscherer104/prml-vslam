#import "../template.typ": *

#slide(title: [Point-Cloud Accuracy: Estimate → Reference])[
  #set text(size: 12.2pt)
  #grid(
    columns: (1.7fr, 0.65fr),
    gutter: 0.45cm,
    [
      #figure(
        image("../../figures/pointcloud/metric_schematics/pointcloud_accuracy.svg", width: 93%),
        caption: [Accuracy: each estimate queries its nearest reference point.],
      )
    ],
    [
      #block(fill: rgb("fff0e8"), stroke: 0.7pt + rgb("f0c0a8"), radius: 8pt, inset: 0.5em)[
        #text(weight: "semibold")[Metric]\
        #text(size: 10.5pt)[$ "accuracy" = "mean"(E arrow.r R) $]
      ]

      #v(0.35em)
      - Query points: estimate cloud $E$.
      - Target: reference cloud $R$.
      - Lower is better.
      - Catches off-surface predictions.

      #v(0.3em)
      #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: 0.45em)[
        Caveat: a small correct patch can still be incomplete.
      ]
    ],
  )
]
