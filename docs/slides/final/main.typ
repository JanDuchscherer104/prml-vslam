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
      *MASt3R* @murai2025mast3rslam:\
      _Christopher_
      - *Foundation Model Prior:* heavy pre-trained network → robust 3D geometry "in-the-wild".
      - *Direct 3D Matching:* matches in 3D ray-space, not 2D features.
      - *Generic Camera:* handles changing intrinsics mid-video (e.g. zoom).
      - Output: camera path + dense colored cloud → input for our metrics.
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

// ===========================================================================
// Christopher Kirschner — MASt3R
// ===========================================================================
#slide(title: [Render-based Image Metrics])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Idea:* Evaluate *in image space*.

      - Render the dense cloud from the *estimated poses* (Open3D
        projection @zhou2018open3d).
      - Compare each render to the nearest input frame, *pixel-wise*.
      - Score only *filled* pixels (mask $Omega$) — don't punish the
        cloud for holes it never covered.
    ],
    [
      *Metrics* — over the $N$ filled pixels $Omega$ ($I$ real, $hat(I)$ render):

      $ "L1" = 1/N sum_(p in Omega) abs(I_p - hat(I)_p) $
      #text(size: 13pt)[→ mean per-pixel error.]

      $ "PSNR" = 10 log_10 (L^2 \/ "MSE") $
      #text(size: 13pt)[→ higher = closer. MSE = mean sq. error, $L$ = max value (255).]

      - SSIM: local *structure*, 7×7 window @wang2004ssim.
      - Coverage: fraction of pixels the cloud fills.

      #note[
        Read every score *with coverage* — the absolute number means
        little on its own.
      ]
    ],
  )
]

#slide(title: [Results — what they say])[
  #grid(
    columns: (1.15fr, 0.85fr),
    gutter: 0.7cm,
    [
      #figure(
        table(
          columns: 6,
          align: (left, center, center, center, center, center, center),
          table.header(
            [Method], [Pairs], [Cov.], [PSNR], [SSIM], [L1],
          ),
          [ViSTA-SLAM], [357], [0.79], [10.8], [0.10], [0.19],
          [MASt3R-SLAM], [154], [0.63], [11.2], [0.07], [0.18],
        ),
        caption: [
          Render-based image-quality results on ADVIO
          advio-15 @cortes2018advio. PSNR/SSIM/L1 averaged over filled
          pixels.
        ],
      )

      *Takeaways:*
      - *Not an absolute quality score* — we use these to *compare the two
        methods* on the same sequence.
      - *Low SSIM could mean a sparse cloud, not bad geometry:* SSIM's sliding
        window also feels the holes, while PSNR/L1 mask pixels cleanly.
    ],
    [
      #figure(
        image("../../figures/render_eval/vista_advio15_sbs_a.png", width: 100%),
        caption: [
          Ground truth (left) vs. ViSTA's dense cloud rendered from the
          estimated camera pose (right).
        ],
      )
    ],
  )
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
