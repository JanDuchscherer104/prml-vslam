#import "../template.typ": *

#slide(title: [Point-Cloud Evaluation: F1 at 5 cm])[
  #set text(size: 12.2pt)
  #grid(
    columns: (1.7fr, 0.65fr),
    gutter: 0.45cm,
    [
      #figure(
        image("../../figures/pointcloud/metric_schematics/pointcloud_f1.svg", width: 93%),
        caption: [F1 turns distances into overlap at a 5 cm tolerance.],
      )
    ],
    [
      #block(fill: rgb("eef8f3"), stroke: 0.7pt + rgb("bfe3d1"), radius: 8pt, inset: 0.5em)[
        #text(weight: "semibold")[Metric]\
        #text(size: 12pt)[$ F_1 = (2 P R) / (P + R) $]
      ]

      #v(0.35em)
      - *Precision* $P$: estimate points within 5 cm of the reference.
      - *Recall* $R$: reference points within 5 cm of the estimate.
      - Higher is better.
      - Needs accuracy and coverage.

      #v(0.3em)
      #block(fill: rgb("fff7ec"), stroke: 0.6pt + rgb("efd3a3"), radius: 6pt, inset: 0.45em)[
        Easier to read than Chamfer for surface overlap.
      ]
    ],
  )
]
