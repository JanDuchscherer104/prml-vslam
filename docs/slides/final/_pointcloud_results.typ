#import "../template.typ": *

#let pc_green = rgb("2f9e6d")
#let pc_orange = rgb("d98c24")
#let pc_red = rgb("c94f4f")
#let pc_gray = rgb("6f7785")
#let pc_light = rgb("f4f6fb")
#let pc_line = rgb("d9dee8")
#let vista_color = rgb("2f9e6d")
#let mast3r_color = rgb("6c63ff")
#let lingbot_color = rgb("d94e67")
#let tum_color = rgb("e8f1ff")
#let record3d_color = rgb("fff1dc")
#let advio_color = rgb("f1f2f6")

#let tag(body, fill, text-fill: black) = rect(
  fill: fill,
  stroke: 0.55pt + fill.darken(22%),
  radius: 4pt,
  inset: (x: 0.42em, y: 0.22em),
)[#text(size: 10.5pt, weight: "semibold", fill: text-fill)[#body]]

#let metric_bar(value, max, fill) = box(width: 100%, height: 0.26cm)[
  #place(left + horizon, rect(width: 100%, height: 0.12cm, fill: rgb("e8ecf3"), radius: 3pt))
  #place(left + horizon, rect(width: value / max * 100%, height: 0.12cm, fill: fill, radius: 3pt))
]

#let metric_card(title, subtitle, body, fill: pc_light, stroke: pc_line) = block(
  fill: fill,
  stroke: 0.7pt + stroke,
  radius: 7pt,
  inset: (x: 0.72em, y: 0.58em),
)[
  #text(size: 11pt, weight: "bold", fill: pc_gray)[#title]
  #v(0.22em)
  #text(size: 14pt, weight: "bold")[#subtitle]
  #v(0.18em)
  #text(size: 10pt)[#body]
]

#slide(title: [Point-Cloud Evaluation: Final Results])[
  #set text(size: 12.2pt)

  #grid(
    columns: (1.22fr, 0.78fr),
    gutter: 0.55cm,
    [
      #figure(
        table(
          columns: (0.78fr, 0.9fr, 0.52fr, 0.9fr, 0.75fr, 0.95fr),
          align: (left, center, center, left, center, left),
          inset: (x: 0.32em, y: 0.34em),
          table.header([Method], [Dataset], [Runs], [Chamfer lower], [F1 higher], [Visual scale]),
          [#tag([ViSTA], vista_color, text-fill: white)],
          [#tag([TUM RGB-D], tum_color)],
          [6],
          [0.143 m],
          [0.546],
          [#metric_bar(0.546, 1.0, pc_green)],

          [#tag([MASt3R], mast3r_color, text-fill: white)],
          [#tag([TUM RGB-D], tum_color)],
          [6],
          [0.074 m],
          [0.850],
          [#metric_bar(0.850, 1.0, pc_green)],

          [#tag([LingBot], lingbot_color, text-fill: white)],
          [#tag([TUM RGB-D], tum_color)],
          [6],
          [0.124 m],
          [0.686],
          [#metric_bar(0.686, 1.0, pc_green)],

          [#tag([ViSTA], vista_color, text-fill: white)],
          [#tag([Record3D], record3d_color)],
          [6],
          [2.203 m],
          [0.100],
          [#metric_bar(0.100, 1.0, pc_orange)],

          [#tag([MASt3R], mast3r_color, text-fill: white)],
          [#tag([Record3D], record3d_color)],
          [5],
          [1.876 m],
          [0.163],
          [#metric_bar(0.163, 1.0, pc_orange)],

          [#tag([Both], pc_gray, text-fill: white)],
          [#tag([ADVIO], advio_color)],
          [0],
          [not scored],
          [not scored],
          [no reference cloud],
        ),
        caption: [Median dense-cloud metrics from benchmark sweep `cloud_metrics.json` artifacts. Bars encode F1 at 5 cm; higher is better.],
      ) <tab:pointcloud-final-local>
    ],
    [
      #metric_card(
        [Best dense overlap],
        [MASt3R on TUM: F1 0.850],
        [Cleaner RGB-D reference clouds make TUM the strongest dense-geometry comparison.],
        fill: rgb("eef8f3"),
        stroke: rgb("bfe3d1"),
      )

      #v(0.35em)
      #metric_card(
        [Learned streaming baseline],
        [LingBot TUM: F1 0.686],
        [Good dense overlap on indoor RGB-D, but below MASt3R and above ViSTA on the same six scenes.],
        fill: rgb("fff7ec"),
        stroke: rgb("efd3a3"),
      )

      #v(0.35em)
      #metric_card(
        [ADVIO is not missing],
        [Trajectory-only here],
        [No benchmark-store reference clouds are available, so dense point-cloud metrics are intentionally not reported.],
        fill: rgb("f3f4f7"),
        stroke: rgb("d6d9e0"),
      )
    ],
  )

  #v(0.3em)
  #block(fill: pc_light, stroke: 0.6pt + pc_line, radius: 6pt, inset: (x: 0.65em, y: 0.45em))[
    #text(
      size: 10.5pt,
    )[Provenance/caveat: medians use completed benchmark sweep `sim3_icp` entries from `cloud_metrics.json`; LingBot values use the six TUM RGB-D `benchmark-18` runs.]
  ]
]

#slide(title: [Point-Cloud Evaluation: All Runs])[
  #set text(size: 7.2pt)

  #let run_table(dataset_tag, rows) = figure(
    table(
      columns: (0.88fr, 1.75fr, 0.8fr, 0.72fr, 0.58fr),
      align: (center, left, center, right, right),
      inset: (x: 0.22em, y: 0.20em),
      table.header([Dataset], [Scene], [Method], [Chamfer], [F1]),
      ..rows,
    ),
    caption: [#dataset_tag cloud metrics, post-ICP Sim(3) alignment.],
  )

  #grid(
    columns: (1fr, 1fr),
    gutter: 0.45cm,
    [
      #run_table([TUM RGB-D], (
        [TUM],
        [freiburg1-360],
        [MASt3R],
        [0.705],
        [0.059],
        [TUM],
        [freiburg1-desk],
        [MASt3R],
        [0.053],
        [0.888],
        [TUM],
        [freiburg1-desk2],
        [MASt3R],
        [0.058],
        [0.876],
        [TUM],
        [freiburg1-floor],
        [MASt3R],
        [0.024],
        [0.973],
        [TUM],
        [freiburg1-plant],
        [MASt3R],
        [0.089],
        [0.825],
        [TUM],
        [freiburg1-room],
        [MASt3R],
        [0.100],
        [0.754],
        [TUM],
        [freiburg1-360],
        [ViSTA],
        [0.870],
        [0.075],
        [TUM],
        [freiburg1-desk],
        [ViSTA],
        [0.051],
        [0.881],
        [TUM],
        [freiburg1-desk2],
        [ViSTA],
        [0.067],
        [0.824],
        [TUM],
        [freiburg1-floor],
        [ViSTA],
        [0.109],
        [0.559],
        [TUM],
        [freiburg1-plant],
        [ViSTA],
        [0.188],
        [0.533],
        [TUM],
        [freiburg1-room],
        [ViSTA],
        [0.177],
        [0.385],
      ))
    ],
    [
      #run_table([Record3D], (
        [R3D],
        [2026-06-03 18:20:22],
        [MASt3R],
        [7.816],
        [0.017],
        [R3D],
        [2026-06-03 18:24:27],
        [MASt3R],
        [1.228],
        [0.163],
        [R3D],
        [2026-06-03 18:26:32],
        [MASt3R],
        [1.833],
        [0.268],
        [R3D],
        [2026-06-03 18:27:25],
        [MASt3R],
        [1.876],
        [0.196],
        [R3D],
        [2026-06-03 18:29:08],
        [MASt3R],
        [11.659],
        [0.013],
        [R3D],
        [2026-06-03 18:17:10],
        [ViSTA],
        [2.776],
        [0.004],
        [R3D],
        [2026-06-03 18:20:22],
        [ViSTA],
        [2.147],
        [0.041],
        [R3D],
        [2026-06-03 18:24:27],
        [ViSTA],
        [0.809],
        [0.150],
        [R3D],
        [2026-06-03 18:26:32],
        [ViSTA],
        [2.381],
        [0.202],
        [R3D],
        [2026-06-03 18:27:25],
        [ViSTA],
        [2.043],
        [0.228],
        [R3D],
        [2026-06-03 18:29:08],
        [ViSTA],
        [2.259],
        [0.050],
      ))
    ],
  )

  #v(0.20em)
  #block(fill: pc_light, stroke: 0.6pt + pc_line, radius: 6pt, inset: (x: 0.55em, y: 0.32em))[
    #text(
      size: 8pt,
    )[Rows are completed runs with `evaluate.cloud` outputs. ADVIO is omitted because no benchmark reference clouds are available.]
  ]
]
