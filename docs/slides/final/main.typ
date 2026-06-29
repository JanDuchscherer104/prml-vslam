#import "../template.typ": *
#import "../update-meetings/_shared/team.typ": team_entry
#import "datastore-tree.typ": vslam-datastore-tree
#import "../../figures/fletcher/pipeline/pipeline_stage_order_flat_bus.typ": pipeline-stage-order-flat-bus

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

#let term_chip(body) = box(
  fill: rgb("f4f6fb"),
  inset: (x: 0.55em, y: 0.32em),
  radius: 4pt,
  stroke: 0.55pt + rgb("d9dee8"),
)[#text(size: 14.5pt)[#body]]

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
#show cite: set text(size: 10pt)
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
  // Lukas: include LingBot training signal here if needed:
  // depth + uncertainty, camera-to-world pose, local relative pose.
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
      _Christopher_
      - learned two-view priors
      - explicit SLAM backend @murai2025mast3rslam
    ],
    [
      *ViSTA*:\
      - intrinsics-free two-view association
      - Sim(3) pose graph @zhang2026vistaslam
      _Lukas_
    ],
    [
      *LingBot*:\
      - streaming reconstruction model
      - Geometric Context Transformer @chen2026gct
      _Jan_
    ],
  )
]

#slide(title: [LingBot-Map: Learned Geometric Context])[
  // Runtime-token slide. Training supervision belongs in Lukas' domain
  // introduction: depth + uncertainty, camera-to-world pose, local relative pose.
  // Speaker transcript, max 1 minute:
  // LingBot-Map is the learned streaming method in our comparison. Its key
  // idea is not just to predict depth and poses frame by frame, but to keep a
  // learned geometric memory. Each image first becomes DINOv2 image tokens.
  // The model appends a camera token, register tokens, and an anchor token.
  // Frame attention refines tokens only within one frame. Geometric Context
  // Attention then lets the current query read three structured sources:
  // anchors for scale and coordinate grounding, a recent window with full
  // image tokens for local pose cues, and compact memory tokens from older
  // frames for long-range context. This is why the method can stream: old
  // image tokens are evicted, but six context tokens per old frame remain.
  // Finally, the camera head reads the camera token to predict pose, while the
  // depth head reads image tokens to predict depth.
  #let stage_node(title, body) = block(
    fill: rgb("f4f6fb"),
    inset: (x: 0.7em, y: 0.42em),
    radius: 8pt,
    stroke: 0.7pt + rgb("cbd3df"),
  )[
    #text(fill: theme_color_footer.darken(42%))[#title]
    #parbreak()
    #align(center)[#body]
  ]

  #let state_fact(fill, title, body) = block(
    fill: fill,
    inset: (x: 0.55em, y: 0.36em),
    radius: 7pt,
    stroke: 0.65pt + fill.darken(25%),
  )[
    #text(weight: "bold")[#title]
    #parbreak()
    #body
  ]

  #let order_fact(fill, num, title, body) = block(
    fill: fill,
    inset: (x: 0.58em, y: 0.42em),
    radius: 7pt,
    height: 2.2cm,
    stroke: 0.65pt + fill.darken(25%),
  )[
    #grid(
      columns: (auto, 1fr),
      gutter: 0.18cm,
      align: horizon,
      box(
        fill: theme_color_primary_hm,
        inset: (x: 0.28em, y: 0.08em),
        radius: 2pt,
      )[#text(weight: "bold", fill: white)[#num]],
      text(weight: "bold")[#title],
    )
    #v(0.07cm)
    #body
  ]

  #let arrow = text(fill: theme_color_primary_hm)[#sym.arrow.r];

  #set text(size: 14pt)
  #set list(spacing: 0.14em, indent: 0.65em, body-indent: 0.35em)


  #grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 0.18cm,
    align: center + horizon,
    stage_node[unposed RGB][$I_(1:t)$],
    [#arrow],
    stage_node[DINOv2 image tokens][$X_t in RR^(M times C)$],
    [#arrow],
    stage_node[append learned tokens][$c_t, r_t^(1:4), a_t$],
    [#arrow],
    stage_node[camera head + depth head][$c_t -> hat(P)_t, quad X_t -> hat(D)_t$],
  )

  #v(0.24cm)

  #grid(
    columns: (0.92fr, 1.08fr),
    gutter: 0.46cm,
    [
      #color-block(title: [GCA = masked geometric memory], spacing: 0.22em)[
        #align(center)[
          $cal(C)_t = cal(A)_(1:n) union cal(W)_(t-k:t) union cal(M)_(n:t-k)$
        ]

        #grid(
          columns: (1fr, 1fr, 1fr),
          gutter: 0.16cm,
          state_fact(rgb("fff7eb"))[$cal(A)$ anchors][full tokens; scale + coordinates],
          state_fact(rgb("eef5ff"))[$cal(W)$ window][recent frames keep full image tokens],
          state_fact(rgb("eefaf4"))[$cal(M)$ memory][old frames keep context tokens only],
        )
      ]
    ],
    [
      #align(center)[
        #image(
          "../../figures/literature/lingbot-map-geometric-context-attention.pdf",
          width: 108%,
          fit: "contain",
        )
      ]
    ],
  )

  #v(0.18cm)

  #text(weight: "bold", fill: theme_color_footer.darken(40%))[Attention order and token ownership]
  #v(0.08cm)

  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    gutter: 0.18cm,
    order_fact(rgb("f4f6fb"))[1][token set][
      $bold(z)_t = {X_t, c_t, r_t^(1:4), a_t}$\
      $abs(bold(z)_t) = M + 6$
    ],
    order_fact(rgb("eef5ff"))[2][frame attention][
      self-attend inside $bold(z)_t$\
      no temporal reads
    ],
    order_fact(rgb("f4f0ff"))[3][GCA memory read][
      $q_t -> cal(A)_(1:n) union cal(W)_(t-k:t)\
      union cal(M)_(n:t-k)$
    ],
    order_fact(rgb("eefaf4"))[4][token budget][
      old $X_i$ drop; keep\
      $c_i, r_i^(1:4), a_i$ ($6$ / frame)
    ],
  )
]


#section-slide(title: [Methodology], subtitle: [Normalized boundaries, transforms, and evaluation])

// #slide(title: [Jan: What Is Worth Explaining?])[
//   #grid(
//     columns: (1.02fr, 0.98fr),
//     gutter: 0.75cm,
//     [
//       #color-block(title: [Ranked contribution candidates], spacing: 0.42em)[
//         #set text(size: 15.5pt)
//         1. Normalized datastore as a reusable benchmark boundary.
//         2. Typed stage handoffs: methods emit artifacts, metrics consume artifacts.
//         3. Frame and timestamp contracts before trajectory metrics.
//         4. SO(3) projection, Sim(3), timestamp alignment, depth sampling, ICP.
//       ]

//       #compact_note[
//         The presentation angle is not a LingBot-Map method slide. It is the
//         benchmark machinery that makes heterogeneous monocular SLAM outputs
//         comparable @bodin2018slambench2 @tancik2023nerfstudio.
//       ]
//     ],
//     [
//       #align(center)[#figure(
//         image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", width: 76%),
//         caption: [Deterministic stage plan.],
//       )]
//     ],
//   )
// ]

#slide(title: [Normalized vSLAM Datastore])[
  #grid(
    columns: (1fr, 1.05fr),

    [
      #color-block(title: [Why normalize first?], spacing: 0.34em)[
        - *File layouts* & *formats* (i.e.`png`, `mov`, `r3d`)
        - *Geometry*:
          + _resize_ RGB-D frames & intrinsics
          + depth units & _point cloud_ creation
          + _frame_ conventions & _SE(3) Frobenius projection_ + _fixedpoint_ transforms
        - *Temporal*:
          + _timestamp_ alignment & _frame_ selection
          + _trajectory_ placement & _Sim(3)_ alignment
        - *Metadata* and *scene statistics*
      ]
    ],
    [
      #figure(
        // vslam-datastore-tree(),
        image("../../figures/evidence/vslam-datastore.png", height: 100%),
        caption: [Normalized datastore layout.],
      )
    ],
  )
]

#slide(title: [Dataset Coverage])[
  #align(center)[
    #figure(
      image("../../figures/evidence/dataset-summary-bars.svg", width: 96%),
      caption: [Normalized datastore coverage across ADVIO, TUM RGB-D, and Record3D.],
    )
  ]
]

#slide(title: [Dataset Reference Signals])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.38cm,
    [
      #color-block(title: [ADVIO])[
        #figure(
          image("../../figures/evidence/dataset-gt-advio.png", width: 100%),
          caption: [Reference Trajectories. `advio-01`.],
        )

        #set text(size: 16pt)
        - Mobile-device indoor/outdoor scenes.
        - GT plus ARKit/ARCore provider trajectories.
      ]
    ],
    [
      #color-block(title: [TUM RGB-D])[
        #figure(
          image("../../figures/evidence/dataset-gt-tum-rgbd.png", width: 100%),
          caption: [GT cloud and trajectory. `fr1/room`.],
        )

        #set text(size: 16pt)
        - RGB-D benchmark scenes with ground-truth camera trajectory.
        - Metric reference geometry for reconstruction checks.
      ]
    ],
    [
      #color-block(title: [Custom Record3D])[
        #figure(
          image("../../figures/evidence/dataset-gt-record3d.png", width: 100%),
          caption: [LiDAR reference cloud and ARKit trajectory. `2026-06-03--18-29-08`.],
        )
        #set text(size: 16pt)
        - Local LiDAR/RGB-D captures from phone archives.
        - Dense reference geometry for reconstruction checks.
      ]
    ],
  )
]

#slide(title: [Pipeline Architecture: Runtime Boundary])[
  #grid(
    columns: (1fr,),
    rows: (auto, auto),
    gutter: 0.42cm,
    [
      #align(center)[
        #figure(
          box(width: 96%)[#pipeline-stage-order-flat-bus()],
          caption: text(size: 9.5pt)[Stage flow with observer fan-out.],
        )
      ]
    ],
    [
      // <do not edit contents>
      #grid(
        columns: (1fr, 1fr),
        gutter: 0.45cm,
        [
          #color-block(title: [Offline])[
            - stages persist & consume _artifacts_
            - _benchmark_ reproducibility
            - post-hoc analysis, export & visualization
          ]
        ],
        [
          #color-block(title: [Streaming])[
            - _concurrent_ execution of stages
            - backpressured streaming of _payload references_
            - live scene updates, online evaluation
            - evaluation of _real-time_ performance
          ]
        ],
      )
      // <do not edit contents>
    ],
  )
]

// TODO: include docs/figures/evidence/teddy-vista-loop-closure.mov here!

#slide(title: [Transform Hygiene at Stage Boundaries])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.72cm,
    [
      #color-block(title: [Frame contract], spacing: 0.34em)[
        #set text(size: 14.2pt)
        A pose is publishable only after its coordinate convention and temporal
        role are explicit:
        - dataset axes become RDF camera/world frames @rerun2026
        - RGB-D/provider trajectories may be rebased to the first pose
        - timestamp alignment happens before metrics or fusion

        $
          bold(p)^"rdf" = bold(B) bold(p)^"raw",
          quad
          bold(R)^"rdf" = bold(B) bold(R)^"raw" bold(B)^(-1)
        $

        $
          bold(T)'_k = bold(T)_0^(-1) bold(T)_k
        $
      ]
    ],
    [
      #color-block(title: [Frobenius projection], spacing: 0.34em)[
        #set text(size: 14.2pt)
        Upstream poses sometimes arrive as near-rotations. We project them onto
        $"SO"(3)$ before they cross a stage boundary @higham1986polar:

        $
          bold(Q)^* =
          arg min_(bold(Q) in "SO"(3)) norm(bold(A) - bold(Q))_"F"
        $

        $
          bold(A) = bold(U) bold(Sigma) bold(V)^T,
          quad
          bold(Q)^* =
          bold(U) op("diag")(1, 1, op("det")(bold(U) bold(V)^T)) bold(V)^T
        $

        #compact_note[
          The residual $epsilon_R = norm(bold(A) - bold(Q)^*)_"F"$ is a validity
          check. It prevents silently accepting matrices that are too far from a
          rotation, instead of correcting arbitrary bad poses.
        ]
      ]
    ],
  )
]

#slide(title: [Dense Geometry: Unprojection + ICP])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.75cm,
    [
      #color-block(title: [Depth to point cloud], spacing: 0.34em)[
        #set text(size: 14.0pt)
        Depth maps are not converted wholesale. The metric artifact records
        camera intrinsics, pose provenance, pixel stride, validity filtering,
        random seed, and maximum point count.

        $
          cal(Omega)_d = { (u, v) | u equiv 0 mod d, v equiv 0 mod d }
        $

        $
          cal(J)_d = { (u, v) in cal(Omega)_d | z(u,v) > 0, z(u,v) in RR }
        $

        $
          (u_j, v_j) in cal(J)_d,
          quad
          bold(q)_j =
          z_j bold(K)^(-1) mat(u_j; v_j; 1),
          quad
          bold(p)_j = bold(T)^"w"_"c" bold(q)_j
        $

        $
          cal(I) ~ op("sample")_"seed"({1, dots, N}, min(N, M)),
          quad
          P_M = { bold(p)_i | i in cal(I) }
        $
      ]
    ],
    [
      #color-block(title: [ICP placement diagnostic], spacing: 0.34em)[
        #set text(size: 14.2pt)
        After global trajectory placement, ICP estimates a local rigid
        correction. It is a dense-geometry diagnostic, not a substitute for
        trajectory APE/RPE @besl1992method @zhou2018open3d.

        $
          bold(T)^* =
          arg min_(bold(T) in "SE"(3)) sum_(bold(p) in P)
          norm(bold(T) bold(p) - op("NN")_Q(bold(T) bold(p)))^2
        $

        Fitness and inlier RMSE depend on the correspondence threshold, so the
        threshold belongs in the metric record.
      ]
    ],
  )

  #compact_note[
    Dense-cloud scores should be discussed only after the method, dataset,
    sampling, and artifact matrix are frozen; ICP alone is not a leaderboard.
  ]
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

#slide(title: [Work breakdown
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
