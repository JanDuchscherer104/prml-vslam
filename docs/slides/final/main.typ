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
  - Domain Introduction, Goals & Non-Goals
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
      *MASt3R* @murai2025mast3rslam:\
      _Christopher_
      - *Foundation Model Prior:* heavy pre-trained network → robust 3D geometry "in-the-wild".
      - *Direct 3D Matching:* matches in 3D ray-space, not 2D features.
      - *Generic Camera:* handles changing intrinsics mid-video (e.g. zoom).
      - Output: camera path + dense colored cloud → input for our metrics.
    ],
    [
      *ViSTA*:\
      - intrinsics-free two-view association
      - Sim(3) pose graph @zhang2026vistaslam
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

#slide(title: [End-to-End Streaming Architecture])[
  // Flo
  #set text(size: 12.8pt)
  #let device_color = rgb("4f7dd6")
  #let model_color = rgb("7c5cc4")
  #let pc_color = rgb("2f9e6d")
  #let muted = rgb("5f6773")
  #let panel(title, body, color) = block(
    fill: color.lighten(75%),
    stroke: 0.75pt + color.lighten(30%),
    radius: 10pt,
    inset: 0.7em,
  )[
    #align(center)[#text(weight: "bold", fill: color.darken(25%))[#title]]
    #v(0.35em)
    #body
  ]
  #let flow_arrow(label) = block(width: 100%)[
    #align(center)[#text(size: 28pt, fill: theme_color_primary_hm)[$arrow.r$]]
    #align(center)[#text(size: 10.5pt, fill: muted)[#label]]
  ]
  #let phone_icon() = box(width: 100%, height: 2.3cm)[
    #align(center + horizon)[
      #rect(width: 1.15cm, height: 2.05cm, radius: 9pt, fill: rgb("f8fbff"), stroke: 1.2pt + device_color)[
        #align(center + horizon)[#circle(radius: 0.18cm, fill: device_color)]
      ]
    ]
  ]
  #let model_icon() = box(width: 100%, height: 2.3cm)[
    #align(center + horizon)[
      #grid(
        columns: (auto, auto, auto),
        rows: (auto, auto, auto),
        gutter: 0.25cm,
        circle(radius: 0.16cm, fill: model_color),
        circle(radius: 0.16cm, fill: model_color),
        circle(radius: 0.16cm, fill: model_color),

        circle(radius: 0.16cm, fill: model_color),
        rect(width: 0.9cm, height: 0.55cm, radius: 4pt, fill: model_color.lighten(25%), stroke: 0.6pt + model_color),
        circle(radius: 0.16cm, fill: model_color),

        circle(radius: 0.16cm, fill: model_color),
        circle(radius: 0.16cm, fill: model_color),
        circle(radius: 0.16cm, fill: model_color),
      )
    ]
  ]
  #let pc_icon() = box(width: 100%, height: 2.3cm)[
    #align(center + horizon)[
      #grid(
        columns: auto,
        rows: (auto, auto),
        gutter: 0.08cm,
        rect(width: 2.0cm, height: 1.25cm, radius: 4pt, fill: rgb("f8fbff"), stroke: 1.1pt + pc_color)[
          #align(center + horizon)[#text(size: 10pt, fill: pc_color.darken(20%))[viewer]]
        ],
        align(center)[#rect(width: 0.8cm, height: 0.12cm, radius: 2pt, fill: pc_color)],
      )
    ]
  ]

  #grid(
    columns: (1fr, 0.42fr, 1fr, 0.42fr, 1fr),
    align: horizon,
    gutter: 0.25cm,
    [
      #panel(
        [Phone],
        [
          #phone_icon()
          #v(0.25em)
          - RGB stream
          - timestamps
          - optional ARKit/ARCore pose
        ],
        device_color,
      )
    ],
    [#flow_arrow([network transport])],
    [
      #panel(
        [VSLAM Model],
        [
          #model_icon()
          #v(0.25em)
          - frame buffer
          - method adapter
          - trajectory + dense cloud
        ],
        model_color,
      )
    ],
    [#flow_arrow([artifacts + updates])],
    [
      #panel(
        [PC / Operator],
        [
          #pc_icon()
          #v(0.25em)
          - live visualization
          - persisted metrics
          - operator-facing map
        ],
        pc_color,
      )
    ],
  )

  // #v(0.45em)
  // #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: (x: 0.7em, y: 0.45em))[
  //   Future work is not only the model: the system needs a robust peripheral pipeline from capture to inference to display.
  // ]
]

// TODO: include docs/figures/evidence/teddy-vista-loop-closure.mov here!

// #slide(title: [Transform Hygiene at Stage Boundaries])[
//   #grid(
//     columns: (1fr, 1fr),
//     gutter: 0.72cm,
//     [
//       #color-block(title: [Frame contract], spacing: 0.34em)[
//         #set text(size: 14.2pt)
//         A pose is publishable only after its coordinate convention and temporal
//         role are explicit:
//         - dataset axes become RDF camera/world frames @rerun2026
//         - RGB-D/provider trajectories may be rebased to the first pose
//         - timestamp alignment happens before metrics or fusion

//         $
//           bold(p)^"rdf" = bold(B) bold(p)^"raw",
//           quad
//           bold(R)^"rdf" = bold(B) bold(R)^"raw" bold(B)^(-1)
//         $

//         $
//           bold(T)'_k = bold(T)_0^(-1) bold(T)_k
//         $
//       ]
//     ],
//     [
//       #color-block(title: [Frobenius projection], spacing: 0.34em)[
//         #set text(size: 14.2pt)
//         Upstream poses sometimes arrive as near-rotations. We project them onto
//         $"SO"(3)$ before they cross a stage boundary @higham1986polar:

//         $
//           bold(Q)^* =
//           arg min_(bold(Q) in "SO"(3)) norm(bold(A) - bold(Q))_"F"
//         $

//         $
//           bold(A) = bold(U) bold(Sigma) bold(V)^T,
//           quad
//           bold(Q)^* =
//           bold(U) op("diag")(1, 1, op("det")(bold(U) bold(V)^T)) bold(V)^T
//         $

//         #compact_note[
//           The residual $epsilon_R = norm(bold(A) - bold(Q)^*)_"F"$ is a validity
//           check. It prevents silently accepting matrices that are too far from a
//           rotation, instead of correcting arbitrary bad poses.
//         ]
//       ]
//     ],
//   )
// ]

// #slide(title: [Dense Geometry: Unprojection + ICP])[
//   #grid(
//     columns: (1fr, 1fr),
//     gutter: 0.75cm,
//     [
//       #color-block(title: [Depth to point cloud], spacing: 0.34em)[
//         #set text(size: 14.0pt)
//         Depth maps are not converted wholesale. The metric artifact records
//         camera intrinsics, pose provenance, pixel stride, validity filtering,
//         random seed, and maximum point count.

//         $
//           cal(Omega)_d = { (u, v) | u equiv 0 mod d, v equiv 0 mod d }
//         $

//         $
//           cal(J)_d = { (u, v) in cal(Omega)_d | z(u,v) > 0, z(u,v) in RR }
//         $

//         $
//           (u_j, v_j) in cal(J)_d,
//           quad
//           bold(q)_j =
//           z_j bold(K)^(-1) mat(u_j; v_j; 1),
//           quad
//           bold(p)_j = bold(T)^"w"_"c" bold(q)_j
//         $

//         $
//           cal(I) ~ op("sample")_"seed"({1, dots, N}, min(N, M)),
//           quad
//           P_M = { bold(p)_i | i in cal(I) }
//         $
//       ]
//     ],
//     [
//       #color-block(title: [ICP placement diagnostic], spacing: 0.34em)[
//         #set text(size: 14.2pt)
//         After global trajectory placement, ICP estimates a local rigid
//         correction. It is a dense-geometry diagnostic, not a substitute for
//         trajectory APE/RPE @besl1992method @zhou2018open3d.

//         $
//           bold(T)^* =
//           arg min_(bold(T) in "SE"(3)) sum_(bold(p) in P)
//           norm(bold(T) bold(p) - op("NN")_Q(bold(T) bold(p)))^2
//         $

//         Fitness and inlier RMSE depend on the correspondence threshold, so the
//         threshold belongs in the metric record.
//       ]
//     ],
//   )

//   #compact_note[
//     Dense-cloud scores should be discussed only after the method, dataset,
//     sampling, and artifact matrix are frozen; ICP alone is not a leaderboard.
//   ]
// ]
#slide(title: [Trajectory Evaluation — Metrics: APE & RPE])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Two questions × two quantities (m / deg):*

      #table(
        columns: (auto, 1fr),
        align: (left, left),
        inset: (x: 0.4em, y: 0.4em),
        table.header([], [*translation* / *rotation*]),
        [*APE* (global)], [_is the whole map right?_],
        [*RPE* (local)], [_is each step right?_],
      )

      $ bold(e)_i^"APE" = op("trans")(bold(T)_i^(-1) hat(bold(T))_i) $
      $ bold(E)_i^"RPE" = (bold(T)_i^(-1) bold(T)_(i+h))^(-1) (hat(bold(T))_i^(-1) hat(bold(T))_(i+h)) $

      #text(size: 13pt)[Headline = *RMSE* over all residuals;
        $Delta = 1"m"$ for RPE @grupp2017evo.]
    ],
    [
      *Interpretation* — the reason we report both:

      - *Low RPE + High APE* → good local tracking, *global
        drift* (weak/no loop closure).
      - *High RPE* → noisy, locally inconsistent odometry.
      - *APE* catches drift & loop-closure quality;
        *RPE* is robust to a single big error.
    ],
  )
]

#slide(title: [Trajectory Evaluation — First Results (pilot sweep)])[
  #set text(size: 14pt)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.7cm,
    [
      *Completion:* #h(0.3em)
      ViSTA *18/18*, MASt3R *9/18*.

      #warning-note[
        *All 6 ADVIO MASt3R runs failed* (+ Record3D 27-25, TUM
        floor/room) in the `align.trajectory` stage.
      ]

      *Why MASt3R fails — a chain:*
      + `max_frames = 50` (vs ViSTA's 512).
      + accepts only *1–5 keyframes* of those 50 (ViSTA: 138–417).
      + writes *1 trajectory pose per keyframe*.
      + $≤ 2$ poses ⇒ fails the $"Sim"(3)$ *spread check*.

      #text(size: 12pt)[Config-driven *and* a real robustness weakness:
        keyframing is intolerant of sparse/fast sampling.]
    ],
    [
      #figure(
        table(
          columns: 5,
          align: (left, center, center, center, center),
          inset: (x: 0.35em, y: 0.34em),
          table.header([Dataset], [APEt ViSTA], [done], [APEt MASt3R], [done]),
          [TUM f1 (×6)], [≈0.10 m], [6/6], [≈0.03 m], [4/6],
          [Record3D (×6)], [≈0.46 m], [6/6], [≈0.03 m], [5/6],
          [ADVIO (×6)], [≈1.95 m], [6/6], [—], [0/6],
        ),
        caption: [Mean APE-translation RMSE; "done" = runs with metrics.],
      )

      - *Scale recovery:* MASt3R $s approx 1.0$ (metric model) vs
        ViSTA $s = 0.4 dots 11$ (scale-free).
      - MASt3R's tiny APE rests on *3–5 pairs* (7-DoF fit ⇒
        near-overfit) and has *no RPE at all*.

      #note[
        *Caveats:* ADVIO is hard for both (ViSTA APE-rot 80–170°,
        under investigation); LingBot pending; full 50×3 matrix is
        future work.
      ]
    ],
  )
]

#include "_pointcloud_accuracy.typ"
#include "_pointcloud_completeness.typ"
#include "_pointcloud_chamfer.typ"
#include "_pointcloud_f1.typ"
#include "_pointcloud_results.typ"

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

      - SSIM: local *structure*, 7×7 window // @wang2004ssim.
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
          table.header([Method], [Pairs], [Cov.], [PSNR], [SSIM], [L1]),
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


// #slide(title: [Future Work: Performance Optimizations])[
//   // Flo
//   #set text(size: 13.2pt)
//   #let active_frame = rgb("4f7dd6")
//   #let skipped_frame = rgb("d9dee8")
//   #let frame(active: true) = rect(
//     width: 0.78cm,
//     height: 0.48cm,
//     radius: 3pt,
//     fill: if active { active_frame } else { skipped_frame },
//     stroke: 0.45pt + if active { active_frame.darken(20%) } else { skipped_frame.darken(18%) },
//   )
//   #let frame_row(label, frames) = grid(
//     columns: (1.0fr, auto, auto, auto, auto, auto, auto, auto, auto),
//     align: horizon,
//     gutter: 0.16cm,
//     [#text(weight: "semibold")[#label]],
//     ..frames,
//   )
//   #let image_box(width, height) = rect(
//     width: width,
//     height: height,
//     radius: 5pt,
//     fill: rgb("eef3ff"),
//     stroke: 0.7pt + rgb("9bb7e5"),
//   )

//   #grid(
//     columns: (1fr, 1fr),
//     gutter: 0.75cm,
//     [
//       #block(fill: rgb("fbfcff"), stroke: 0.7pt + rgb("d9dee8"), radius: 9pt, inset: 0.7em)[
//         #text(weight: "bold")[Option 1: reduce resolution]
//         #v(0.55em)
//         #align(center)[
//           #grid(
//             columns: (auto, auto, auto, auto, auto),
//             align: horizon,
//             gutter: 0.25cm,
//             image_box(2.45cm, 1.62cm),
//             [#text(size: 22pt, fill: theme_color_primary_hm)[$arrow.r$]],
//             image_box(1.85cm, 1.22cm),
//             [#text(size: 22pt, fill: theme_color_primary_hm)[$arrow.r$]],
//             image_box(1.25cm, 0.82cm),
//           )
//         ]
//         #v(0.55em)
//         - fewer pixels per frame
//         - lower GPU memory and compute
//         - risk: weaker feature/detail quality
//       ]
//     ],
//     [
//       #block(fill: rgb("fbfcff"), stroke: 0.7pt + rgb("d9dee8"), radius: 9pt, inset: 0.7em)[
//         #text(weight: "bold")[Option 2: increase frame stride]
//         #v(0.45em)
//         #frame_row([stride 1], (
//           frame(),
//           frame(),
//           frame(),
//           frame(),
//           frame(),
//           frame(),
//           frame(),
//           frame(),
//         ))
//         #v(0.28em)
//         #frame_row([stride 2], (
//           frame(),
//           frame(active: false),
//           frame(),
//           frame(active: false),
//           frame(),
//           frame(active: false),
//           frame(),
//           frame(active: false),
//         ))
//         #v(0.28em)
//         #frame_row([stride 4], (
//           frame(),
//           frame(active: false),
//           frame(active: false),
//           frame(active: false),
//           frame(),
//           frame(active: false),
//           frame(active: false),
//           frame(active: false),
//         ))
//         #v(0.55em)
//         - fewer frames through SLAM
//         - improves throughput directly
//         - risk: larger motion gaps and tracking failures
//       ]
//     ],
//   )

//   #v(0.55em)
//   #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: (x: 0.7em, y: 0.45em))[
//     Goal: measure quality/runtime tradeoffs instead of optimizing for speed blindly.
//   ]
// ]

#slide(title: [Future Work: Toward Complete 4D Reconstruction])[
  // Flo
  #set text(size: 12.6pt)
  #grid(
    columns: (1.35fr, 0.85fr),
    gutter: 0.65cm,
    [
      #figure(
        image("../../figures/papers/lift4d.jpg", width: 100%),
        caption: [Lift4D reconstructs complete dynamic objects from monocular in-the-wild video.],
      )
    ],
    [
      #block(fill: rgb("fbfcff"), stroke: 0.7pt + rgb("d9dee8"), radius: 9pt, inset: 0.75em)[
        *Lift4D* @litman2026lift4d

        #v(0.35em)
        - monocular video input
        - temporally consistent single-view 3D prior
        - deformable 3D Gaussian representation
        - occlusion-aware completion of unseen regions

        #v(0.45em)
        #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: 0.55em)[
          Long-term direction: move from sparse SLAM maps toward complete, dynamic scene reconstructions.
        ]
      ]
    ],
  )
]

#slide(title: [Retrospective: What went right, what went wrong?])[
  // Valentin
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      #good-note(width: 100%)[#align(center)[*What went right* ✓]]

      - *AI* enabled a quick project setup (pipeline, Streamlit app, Rerun).
      - Pipeline made integrating *multiple SLAM methods* easy
        (ViSTA, MASt3R, LingBot).
      - Supports *multiple datasets* (ADVIO, TUM, Record3D).
      - *Fully configurable:* method, source, VSLAM config (frames…),
        evaluation steps.
      - *Sweeper* runs all sources × all methods.
    ],
    [
      #warning-note(width: 100%)[#align(center)[*What went wrong* ✗]]

      - Fast POC — but *huge refactorings* from development with AI.
      - *Slow, intensive finalization:* running evaluation &
        getting comparable results across methods.
      - Hard to find the *best-fit parameters per method*.
      - First sweep had a *misconfiguration* — MASt3R/ViSTA config mismatch messed up the results.
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
