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

#slide(title: [JD Evidence Cluster])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.75cm,
    [
      *Seed material, not final ownership*

      - Pipeline framework and artifact contracts.
      - Source normalization for ADVIO, TUM RGB-D, Record3D.
      - ViSTA frame and transform debugging.
      - Sim(3), gravity-aware alignment, ICP diagnostics.
      - Rerun live/export logging and validation surfaces.
      - LingBot integration.
    ],
    [
      #quote-block[
        The final deck remains a five-person presentation. These slides collect the JD-first evidence that future agents can refine and rebalance.
      ]
    ],
  )
]

#section-slide(title: [System And Data Pipeline])

#slide(title: [Pipeline Framework])[
  #grid(
    columns: (1.05fr, 0.95fr),
    [
      - `RunConfig` compiles into a deterministic `RunPlan`.
      - Runtime order: `source -> slam -> gravity.align -> evaluate.trajectory -> reconstruction -> evaluate.cloud -> summary`.
      - `StageResult` is the typed terminal handoff.
      - `StageRuntimeUpdate` carries live telemetry and neutral visualization items.
      #good-note[Run artifacts, manifests, and summaries are the reproducibility contract.]
    ],
    [
      #figure(
        image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", height: 75%),
        caption: [`RunConfig` to stage plan.],
      )
    ],
  )
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
