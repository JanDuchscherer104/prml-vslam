#import "../template.typ": *

#slide(title: [Point-Cloud Chamfer: Two Directions, One Number])[
  #set text(size: 12.2pt)
  #grid(
    columns: (1.7fr, 0.65fr),
    gutter: 0.45cm,
    [
      #figure(
        image("../../figures/pointcloud/metric_schematics/pointcloud_chamfer.svg", width: 93%),
        caption: [Chamfer adds both nearest-neighbor directions.],
      )
    ],
    [
      #block(fill: theme_color_block, stroke: 0.7pt + theme_color_block.darken(15%), radius: 8pt, inset: 0.5em)[
        #text(weight: "semibold")[Metric]\
        #text(size: 10.5pt)[$ "Chamfer" = "accuracy" + "completeness" $]
      ]

      #v(0.35em)
      - Lower is better.
      - Summarizes both nearest-neighbor directions.
      - Useful as a compact score.
      - Can hide failure mode.

      #v(0.3em)
      #warning-note(width: 100%)[
        Same total can mean noisy geometry or missing coverage.
      ]
    ],
  )
]
