#import "../template.typ": *
#import "../update-meetings/_shared/team.typ": team_entry

#let team_members = [
  Jan Duchscherer, Lukas Röß, Christopher Kirschner, \ Valentin Bumeder, Florian Beck
]

#let footer_members = [
  J. Duchscherer, V. Bumeder, L. Röß, C. Kirschner, F. Beck
]

#let compact_note(body) = block(
  fill: rgb("f4f6fb"),
  inset: (x: 0.7em, y: 0.55em),
  radius: 6pt,
  stroke: 0.6pt + rgb("d9dee8"),
)[#body]

#show: definitely-not-isec-theme.with(
  aspect-ratio: "16-9",
  slide-alignment: top,
  progress-bar: true,
  // font: "Noto Sans",
  institute: [Munich University of Applied Sciences, Department of Computer Science & Mathematics],
  logo: [#image("../../figures/hm-logo.svg", width: 2cm)],
  config-info(
    title: [Uncalibrated Monocular VSLAM],
    subtitle: [Final presentation],
    authors: team_members,
    extra: [
      Pattern Recognition & Machine Learning
    ],
    footer: [#project_footer(
      footer_authors: footer_members,
      footer_label: [PRML VSLAM],
      footer_date: [#datetime(year: 2026, month: 7, day: 02).display("[day padding:none]. [month repr:short] [year]")],
    )],
    download-qr: "",
  ),
  config-common(handout: false),
  config-colors(
    primary: theme_color_primary_hm,
    lite: theme_color_block,
  ),
)

#set text(size: 18pt)

#show figure.caption: set text(size: 12pt, weight: "medium", fill: theme_color_footer.darken(40%))
#show link: set text(fill: blue)
#show link: it => underline(it)
#show ref: set text(size: 12pt)

#title-slide()

#slide(title: [Team])[
  #align(center + horizon)[
    #team_entry
  ]
]

#slide(title: [Motivation: Uncalibrated Monocular VSLAM])[
  - Domain Introduction & Goals
  - _LUKAS_
]

// TODO: maybe one slide per method?
#slide(title: [Method Comparison])[
  - conceptual comparison of the three candidate methods (ViSTA, MASt3R, LingBot)
  - What are their main distinctive features?
  #grid(
    columns: (1fr, 1fr, 1fr),
    [
      *MASt3R*:\
      _Chirstopher_
      - traditional SLAM backend
      -
    ],
    [
      *ViSTA*:\
      - no priviledged reference frame,
      - traditional SLAM backend
      _Lukas_
    ],
    [
      *LingBot*:\
      - end-to-end learning-based SLAM,
      - Geometric Context Transformer
      _Jan_
    ],
  )
]

#section-slide(title: [Methodology], subtitle: [Intresting Implementation Details])

#slide(title: [JD])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.75cm,
    [
      *Seed material, not final ownership*

      - Standardized stage boundaries.
      - Pipeline framework and artifact contracts.
      - Source normalization for ADVIO, TUM RGB-D, Record3D.
      - Sim(3), gravity-aware alignment, ICP.
    ],
    [
      #quote-block[
        #lorem(5)
      ]
    ],
  )
]

// #slide(title: [Pipeline Framework])[
//   #grid(
//     columns: (1.05fr, 0.95fr),
//     [
//       - `RunConfig` compiles into a deterministic `RunPlan`.
//       - Runtime order: `source -> slam -> gravity.align -> evaluate.trajectory -> reconstruction -> evaluate.cloud -> summary`.
//       - `StageResult` is the typed terminal handoff.
//       - `StageRuntimeUpdate` carries live telemetry and neutral visualization items.
//       #good-note[Run artifacts, manifests, and summaries are the reproducibility contract.]
//     ],
//     [
//       #figure(
//         image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", height: 75%),
//         caption: [`RunConfig` to stage plan.],
//       )
//     ],
//   )
// ]

#slide(title: [Trajectory Evaluation])[
  - Problem: not same frame, not same scale, not same orientation.
  - Sim(3)
  - APE metric?
]

#slide(title: [Point Cloud Evaluation])[
  - ICP: Iterative Closest Point
  - Metrics used.
  -
]

#slide(title: [Image Metrics])[
  - Metrics used.
  - Brief performance comparison.
]

#slide(title: [Real-time Performances])[

  - FPS + latency?
  - own measurments and paper reported numbers.
  - nvidia-smi and perf stats.
]


#slide(title: [Future Work])[
  // Flo
  - Strong FPS dependence of ViSTA and MASt3R (limitation for streaming when FPS is low).
  - Real-time capability on consumer grade GPUs with loss of performance.
  -
]

#slide(title: [Retrospective: What went right, what went wrong?])[
  // Valentin
  -
]

#slide(title: [Retrospective: What went right, want went wrong?
])[
  - Mapping from work packages to owner
  -
]

#slide(title: [References])[
  #set text(size: 9pt)
  #set par(leading: 0.75em, spacing: 0.18em)
  #set list(spacing: 0.18em)
  #show list.item: it => block(breakable: false)[it]
  #columns(2, gutter: 0.9cm)[
    #bibliography("../../references.bib", title: none)
  ]
]
