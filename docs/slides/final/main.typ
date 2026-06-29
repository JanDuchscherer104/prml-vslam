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
  #let stage_node(title, body) = block(
    fill: rgb("f4f6fb"),
    inset: (x: 0.7em, y: 0.42em),
    radius: 8pt,
    stroke: 0.7pt + rgb("cbd3df"),
  )[
    #text(size: 16pt, fill: theme_color_footer.darken(42%))[#title]
    #parbreak()
    #align(center)[#text(size: 20pt)[#body]]
  ]

  #let fact(fill, title, body) = block(
    fill: fill,
    inset: (x: 0.55em, y: 0.36em),
    radius: 7pt,
    stroke: 0.65pt + fill.darken(25%),
  )[
    #text(size: 18pt, weight: "bold")[#title]
    #parbreak()
    #text(size: 16pt)[#body]
  ]

  #let arrow = text(size: 30pt, fill: theme_color_primary_hm)[#sym.arrow.r];



  #grid(
    columns: (1fr, auto, 1fr, auto, 1fr, auto, 1fr),
    gutter: 0.18cm,
    align: center + horizon,
    stage_node[Unposed RGB Frames][$I_(1:t)$],
    [#arrow],
    stage_node[DINOv2 tokens][$X_t in RR^(M times C)$],
    [#arrow],
    stage_node[learned context][$cal(A), cal(W), cal(M)$],
    [#arrow],
    stage_node[heads][$hat(P)_t, hat(D)_t$],
  )

  #v(0.24cm)

  #grid(
    columns: (0.92fr, 1.08fr),
    gutter: 0.46cm,
    [
      #color-block(title: [GCA state = learned SLAM memory], spacing: 0.22em)[
        #align(center)[
          #text(size: 20pt)[$cal(C)_t = cal(A)_(1:n) union cal(W)_(t-k:t) union cal(M)_(n:t-k)$]
        ]

        - *$cal(A)$ anchors* scale + coordinates
        - *$cal(W)$ sliding window* full image tokens
        - *$cal(M)$ memory* compact old-frame tokens
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

  #v(0.22cm)

  #grid(
    columns: (1fr, 1fr, 1fr, 1fr),
    gutter: 0.42cm,
    fact(rgb("fff7eb"))[Anchor scale][First $n$ frames fix scale; depth and translation are normalized.],
    fact(rgb("eefaf4"))[Token budget][Old frames keep $6$ tokens; about $80 times$ lower growth.],
    fact(rgb("fef3f3"))[Training signal][Depth + uncertainty, camera-to-world pose, local relative pose.],
    fact(rgb("eef5ff"))[Inference][Direct persistent state; VO uses Sim(3) window stitching.],
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
          + _frame_ conventions & _SE(3) corrections_ + _fixedpoint_ transforms
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

#slide(title: [Trajectory Evaluation: Frame + Time + Scale])[
  #grid(
    columns: (1.05fr, 0.95fr),
    gutter: 0.72cm,
    [
      #color-block(title: [Admissible pose pairs], spacing: 0.38em)[
        #set text(size: 14.5pt)
        - First associate timestamps with a declared tolerance.
        - Then check pose relation and target-frame metadata.
        - Only then estimate placement and compute APE/RPE @zhang2018trajectory @grupp2017evo.
      ]

      #text(size: 14.2pt)[
        $
          cal(A)_tau = { (i, j) | abs(t_i^"ref" - t_j^"est") <= tau }
        $

        $
          bold(S)^* =
          arg min_(bold(S) in "Sim"(3)) sum_((i,j) in cal(A)_tau)
          norm(bold(x)_i^"ref" - bold(S) bold(x)_j^"est")^2
        $

        $
          bold(S) bold(x) = s bold(R) bold(x) + bold(t)
        $
      ]
    ],
    [
      #color-block(title: [What the alignment model means], spacing: 0.38em)[
        #set text(size: 14.2pt)
        - Timestamp-only APE asks whether metric scale and placement were recovered.
        - Sim(3)-aligned APE asks whether the trajectory shape agrees after monocular scale ambiguity is removed @umeyama1991least.
        - Gravity-aware alignment estimates scale, yaw, and translation when vertical is meaningful.
      ]

      #text(size: 14.2pt)[
        $
          bold(S)^* =
          arg min_(s, theta, bold(t)) sum_i
          norm(bold(x)_i^"ref" - (s bold(R)_"yaw"(theta) bold(x)_i^"est" + bold(t)))^2
        $

        $
          bold(R)_"yaw" bold(u) = bold(u)
        $
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
