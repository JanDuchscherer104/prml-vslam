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

#slide(title: [Challenge Introduction])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Background*
      - Professional Visual SLAM pipelines demand rigid factory calibration.
      - Consumer frameworks utilize real-time sensor fusion but fail on retrospective, uncalibrated video streams.
      - Global metric consistency and high-fidelity dense mapping deteriorate when intrinsics remain unknown.
    ],
    [
      *The Challenge*
      - Develop an off-device VSLAM pipeline utilizing state-of-the-art monocular dense methods.
      - Input: Smartphone monocular video stream.
      - Execution: Autonomously handle unknown intrinsics.
      - Output: High-precision trajectory and dense 3D point cloud.
    ],
  )
]

#slide(title: [Motivation & Domain Introduction])[
  *Why Visual SLAM over Structure from Motion?*

  - *Structure from Motion (SfM)* processes uncalibrated data effectively but operates strictly offline via batch processing, prohibiting real-time execution.
  - *Visual SLAM (VSLAM)* incrementally processes video streams, fulfilling the real-time constraints required for emergency response and live stream analysis.
  - *Methodological Overlap:* Modern learning-based VSLAM integrates robust SfM-like global optimization into its backend while maintaining a low-latency tracking frontend.
]

#slide(title: [Goals & Non-Goals])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      #good-note(width: 100%)[#align(center)[*Project Goals*]]
      - Benchmark state-of-the-art uncalibrated VSLAM methods (ViSTA-SLAM, MASt3R-SLAM, LingBot).
      - Establish robust evaluation metrics for trajectory drift and reconstruction fidelity.
      - Develop a custom pipeline for high-quality test data acquisition.
      - Analyze system latency and memory consumption.
    ],
    [
      #warning-note(width: 100%)[#align(center)[*Explicit Non-Goals*]]
      - Develop a novel SLAM algorithm from scratch.
      - Perform real-time model inference directly on mobile edge devices.
      - Deliver a production-ready graphical user interface for operators.
      - Integrate ARCore as a fundamental pipeline component; it serves solely as an external baseline.
    ],
  )
]
//       - intrinsics-free two-view association
//       - Sim(3) pose graph @zhang2026vistaslam

#slide(title: [ViSTA SLAM: Method & Architecture])[
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.8cm,
    [
      *Symmetric Two-View Frontend*
      - Predicts local point maps and relative poses symmetrically to reduce parameter count.
      - *Frontend Loss:* Jointly optimizes pointmap consistency, geometric alignment, and the relative pose along the $op("SE")(3)$ manifold via cycle-consistency:

      $
        L_("pose") & = w_(i j) ( L_R (bold(R)_(i j), hat(bold(R))_(i j)) \
                   & quad + L_t (bold(t)_(i j), hat(bold(t))_(i j)) + L_("id") ) \
                   & quad - alpha log(w_(i j))
      $
    ],
    [
      *Backend: $op("Sim")(3)$ Pose Graph*
      - Nodes hold absolute camera poses with an independent scale factor.
      - Minimizes residual error in the $frak(s)frak(i)frak(m)(3)$ Lie algebra via Levenberg-Marquardt:

      $
        min_({bold(v)_i^j}) sum_(bold(e)_(i j)) norm(log_("Sim"(3)) (bold(e)_(i j) dot (bold(v)_i^j)^(-1) dot bold(v)_j^i))_(bold(Omega)_(i j))^2
      $
    ],
  )

  #v(0.2cm)
  #align(center)[
    #figure(
      image("../../figures/papers/figure-2-vista-architecture.png", width: 95%),
      caption: [ViSTA SLAM Pipeline Architecture @zhang2026vistaslam],
    )
  ]
]

#slide(title: [ViSTA SLAM: Scene Reconstruction (Record3D)])[
  - *Reference (iPhone ARKit)*: Trajectory and LiDAR points in *Green*.
  - *ViSTA SLAM*: Predicted trajectory in *Purple* with dense colored point cloud.

  #align(center)[
    #figure(
      image("../../figures/evidence/record3d-29-08-pc+traj.png", height: 75%),
      caption: [ViSTA SLAM vs. Ground Truth on Custom Record3D Capture],
    )
  ]
]

/*
#slide(title: [MASt3R-SLAM])[
  - *Foundation Model Prior:* heavy pre-trained network → robust 3D geometry "in-the-wild".
  - *Direct 3D Matching:* matches in 3D ray-space, not 2D features.
  - *Generic Camera:* handles changing intrinsics mid-video (e.g. zoom).
  - Output: camera path + dense colored cloud → input for our metrics.
  #h(29pt) @murai2025mast3rslam
]
*/
#slide(title: [MASt3R-SLAM: System Overview])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.8cm,
    [
      *3D-Prior front-end*
      - MASt3R (ViT-Large): a learned 3D foundation model — geometry straight from an image pair, no keypoints, no triangulation.
      - Dense by construction: a 3D point for *every* pixel, fused across keyframes into the map.
    ],
    [
      *Pixel → ray → depth*
      - For every pixel the network predicts a *viewing ray* and a *depth* along it → one dense 3D point per pixel.
      - Two frames are aligned directly in this ray/point space (point-to-ray error) — no 2D feature descriptors.
    ],
    [
      *Uncalibrated & real-time*
      - No calibration needed: generic central-camera model, focal estimated *per keyframe* → raw smartphone video.
      - Intrinsics may even change mid-sequence (e.g. the camera *zooms*); still real-time (\~15 FPS) with loop closure.
    ],
  )

  #v(0.35cm)
  #good-note[
    *Why $op("Sim")(3)$?* Monocular + uncalibrated → the scene scale is unknown and drifts, so every keyframe carries a *similarity* transform (rotation, translation *and* scale) to absorb it.
  ]

  #align(center)[
    #figure(
      image("../../literature/tex-src/arXiv-MASt3R-SLAM/figs/system-diagram.pdf", width: 95%),
      caption: [MASt3R-SLAM Pipeline @murai2025mast3rslam],
    )
  ]
]

#slide(title: [LingBot-Map: Learned Geometric Context])[
  #let stage_node(title, body) = block(
    fill: rgb("f4f6fb"),
    inset: (x: 0.7em, y: 0.42em),
    radius: 8pt,
    stroke: 0.7pt + rgb("cbd3df"),
  )[
    #text(fill: theme_color_footer.darken(42%), size: 18pt)[#title]
    #parbreak()
    #align(center)[#body]
  ]

  #let state_fact(fill, title, body) = block(
    fill: fill,
    inset: (x: 0.55em, y: 0.36em),
    radius: 7pt,
    stroke: 0.65pt + fill.darken(25%),
  )[
    #align(center)[
      #text(weight: "bold")[#title]
      #parbreak()
      #body
    ]
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
      text(weight: "bold", size: 14pt)[#title],
    )
    #v(0.07cm)
    #body
  ]

  #let arrow = text(fill: theme_color_primary_hm)[#sym.arrow.r];

  #set text(size: 16pt)
  #set list(spacing: 0.14em, indent: 0.65em, body-indent: 0.35em)


  #grid(
    columns: (1fr, auto, 1fr, auto, 1.2fr, auto, 1fr, auto, 1fr),
    gutter: 0.18cm,
    align: center + horizon,
    stage_node[RGB Frames][$I_(1:t)$],
    [#arrow],
    stage_node[DINOv2 tokens][$X_t in RR^(M times C)$],
    [#arrow],
    stage_node[append learned tokens][$bold(z)_t = {X_t, c_t, r_t^(1:4), a_t}$],
    [#arrow],
    stage_node[Geometric Context Attention][],
    [#arrow],
    stage_node[camera head + depth head][$c_t -> hat(P)_t, quad X_t -> hat(D)_t$],
  )

  #v(0.24cm)

  #grid(
    columns: (1.4fr, 1.0fr),
    gutter: 0.6cm,
    [
      #color-block(title: [GCA = masked geometric memory])[
        #set align(center)

        $cal(C)_t = cal(A)_(1:n) union cal(W)_(t-k:t) union cal(M)_(n:t-k)$

        #grid(
          columns: (auto, auto, auto),
          gutter: 0.6cm,
          state_fact(rgb("edebff"))[$cal(A)$ anchors][full tokens \ Sim(3) grounding],
          state_fact(rgb("#ffe397c0"))[$cal(W)$ window][recent frames \ all tokens],
          state_fact(rgb("eefaf4"))[$cal(M)$  memory][old frames \ register tokens $r_t^(1:4)$],
        )
      ]
      #quote-block[
        $c_t$: camera pose token\
        $a_t$: anchor / scale-context token
      ]
    ],
    [
      #align(center)[
        #image(
          "../../figures/literature/lingbot-map-geometric-context-attention.pdf",
          width: 65%,
          fit: "contain",
        )
        @chen2026gct
      ]
    ],
  )
]

#slide(title: [LingBot-Map: Why Excluded From Sweeps])[
  // The exact Record3D LingBot loop-closure-failure screenshot is not present
  // in this worktree. Keep the second panel reserved for the predicted-cloud
  // view when that screenshot is copied into docs/figures/evidence/.
  #grid(
    columns: (1.0fr, 1.0fr),
    gutter: 0.52cm,
    [
      #figure(
        image("../../figures/evidence/tum-cabinet-lingbot.png", width: 100%, fit: "cover"),
        caption: [LingBot trajectory and point cloud, TUM-RGB-D fr3/large-cabinet.],
      )
    ],
    [
      #figure(
        image("../../figures/evidence/record3d-29-08-lingbot-loop-closure-fail.png", width: 100%),
        caption: [LingBot & ARKit trajectory, Record3D 2026-06-03--18-29-08.],
      )
    ],
  )
]



#section-slide(title: [Methodology], subtitle: [Normalized boundaries, transforms, and evaluation])

#slide(title: [Datasets for vSLAM Benchmarking])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.38cm,
    [
      #color-block(title: [ADVIO])[
        #figure(
          image("../../figures/evidence/dataset-gt-advio.png", width: 90%),
          caption: [Reference Trajectories. `advio-01`.],
        )
        #set text(size: 17pt)
        - Pedestrian smartphone VIO
        - GT + ARKit/ARCore for _trajectory benchmarking_
        - _Deployment realism_ @cortes2018advio
      ]
    ],
    [
      #color-block(title: [TUM RGB-D])[
        #figure(
          image("../../figures/evidence/dataset-gt-tum-rgbd.png", width: 90%),
          caption: [GT cloud and trajectory. `fr1/room`.],
        )

        #set text(size: 17pt)
        - High quality _stereo RGB-D_ + _MoCap_ trajectoroes
        - _Research standard_ for indoor SLAM benchmarking @newcombe2011kinectfusion
      ]
    ],
    [
      #color-block(title: [Custom Record3D])[
        #figure(
          image("../../figures/evidence/dataset-gt-record3d.png", width: 90%),
          caption: [LiDAR reference cloud and ARKit trajectory. `2026-06-03--18-29-08`.],
        )
        - LiDAR depth-maps & ARKit trajectories.
        - Realistic smartphone capture of outdoor scenes.
        - Target-domain E2E validation.
      ]
    ],
  )
]

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
    ],
  )
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

#slide(title: [Trajectory Evaluation — Results: APE & RPE])[
  #set text(size: 14pt)
  #align(center)[#text(size: 11.5pt, fill: theme_color_footer.darken(30%))[
    Sim(3)-aligned *RMSE*, matched-scene *medians* (15 scenes both methods finished);
    RPE at $Delta = 1$ m. Bold = clear winner.
  ]]
  #v(0.18em)
  #align(center)[#table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, center, center, center, center),
    inset: (x: 0.5em, y: 0.4em),
    table.header([Dataset], [Method], [APE t (m)], [APE rot (°)], [RPE t (m)], [RPE rot (°)]),
    [TUM (6–14 m)], [MASt3R], [*0.05*], [*2.3*], [*0.09*], [*2.0*],
    [], [ViSTA], [0.14], [6.1], [0.17], [3.9],
    [Record3D (43–211 m)], [MASt3R], [1.97], [6.0], [0.41], [1.2],
    [], [ViSTA], [2.02], [7.9], [2.03], [4.6],
    [ADVIO (138–217 m)], [MASt3R], [*5.4*], [*88*], [*4.2*], [*7.0*],
    [], [ViSTA], [17.3], [112], [4.3], [13.5],
  )]
  #v(0.2em)
  #grid(
    columns: (1fr, 1fr),
    gutter: 0.6cm,
    [
      *APE* = global error (whole map); *RPE* = local drift per 1 m.
      - *TUM:* both work — MASt3R *cm-level*, ~3× better. Small APE *and*
        RPE → consistent locally *and* globally.
      - *Record3D:* near-tie on global APE, but MASt3R ~5× steadier locally.
    ],
    [
      - *ADVIO:* both *fail*, and it is *rotational* — APE-rot 88–112°
        (orientation ≈ decorrelated); RPE-trans ≈ 4 m/1m → broken locally too.
      #note[Numbers are Sim(3)-aligned (shape, not metric scale); ADVIO
        rotation is *inflated by a known gravity-lock gate issue* — partly
        pipeline, not only method.]
    ],
  )
]

#slide(title: [Trajectory Evaluation — Findings & AR Baselines])[
  #set text(size: 13.5pt)
  #grid(
    columns: (1.05fr, 0.95fr),
    gutter: 0.7cm,
    [
      #color-block(title: [What drives the difference])[
        #set text(size: 12.8pt)
        - *Robustness:* ViSTA *18/18*, MASt3R *15/18* — crashes on the 3
          longest scenes (fixed *512-keyframe buffer*).
        - *Length crossover* (Record3D): ViSTA/MASt3R APE ratio
          *4.0 → 0.65* across *43 → 211 m* → MASt3R wins short,
          *ViSTA wins long* (≈ 60–90 m).
        - *Why:* MASt3R's local RPE *cliffs* 0.3 → 3.7 on the longest scenes;
          ViSTA stays flat (~1–2). Same 512 limit: _fine → cliff → crash_.
        - *Metric scale* $s$ (ideal 1.0): MASt3R *≈ 0.9–1.1*; ViSTA wild
          (*0.25 / 0.53 / 2.7*).
      ]
    ],
    [
      #figure(
        table(
          columns: 4,
          align: (left, center, center, center),
          inset: (x: 0.4em, y: 0.34em),
          table.header([ADVIO vs GT], [APE t (m)], [APE rot (°)], [RPE t (m)]),
          [*ARCore*], [*1.5*], [13], [*0.39*],
          [*ARKit*], [1.8], [*11*], [0.41],
          [MASt3R], [5.4], [88], [4.2],
          [ViSTA], [17.3], [112], [4.3],
        ),
        caption: [Phone AR tracking vs our SLAM — same VIO ground truth.],
      )
      #set text(size: 12.2pt)
      - AR = *visual-inertial odometry* (camera *+ IMU*), recorded with ADVIO.
      - Beats our methods *~3–12×* (position), *~10×* (rotation & local drift).
      - The *IMU* gives *metric scale + gravity + blur-robust rotation* —
        exactly what monocular vision can't recover on long walks.
    ],
  )
  #v(0.3em)
  #note[
    *Takeaway:* on phone data sensor fusion beats backbone — ours solves the
    harder *uncalibrated, vision-only* problem, so AR is the *ceiling/context*,
    not a rival (and *not GT* either: 1.5–1.8 m ≈ 1–2 % off).
    #h(0.4em) *MASt3R = accuracy but brittle; ViSTA = robustness but drifts.*
  ]
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
  #let vista_color = rgb("3f7de0")
  #let mast3r_color = rgb("f28e2b")
  #let paper_color = rgb("6f7785")
  #let bar_row(label, value, max, fill, value-label) = grid(
    columns: (3.15cm, 1fr, 1.15cm),
    column-gutter: 0.28cm,
    align: (left, horizon, right),
    [
      #label
    ],
    [
      #box(width: 100%, height: 0.34cm)[
        #place(left + horizon, rect(width: 100%, height: 0.15cm, fill: rgb("e8ecf3"), radius: 3pt))
        #place(left + horizon, rect(width: value / max * 100%, height: 0.15cm, fill: fill, radius: 3pt))
      ]
    ],
    [
      #value-label
    ],
  )

  #grid(
    columns: (1.04fr, 0.96fr),
    gutter: 0.5cm,
    [
      #color-block(title: [Streaming FPS])[
        #bar_row([ViSTA TUM], 82.7, 90, vista_color, [82.7])
        #bar_row([ViSTA R3D], 62.2, 90, vista_color, [62.2])
        #bar_row([ViSTA\*], 78.0, 90, paper_color, [78.0])
        #bar_row([MASt3R TUM], 17.4, 90, mast3r_color, [17.4])
        #bar_row([MASt3R R3D], 16.3, 90, mast3r_color, [16.3])
        #bar_row([MASt3R\*], 15.1, 90, paper_color, [15.1])

        #v(0.35em)
        #compact_note[
          \* Paper bars: ViSTA 7Scenes redkitchen @zhang2026vistaslam; MASt3R-SLAM matching-system setting @murai2025mast3rslam.
        ]
      ]
    ],
    [
      #color-block(title: [Pipeline telemetry])[
        #table(
          columns: (1.15fr, 0.85fr, 0.85fr),
          align: (left, right, right),
          table.header([run], [lat. ms], [key-FPS]),
          [V TUM], [115.5], [2.99],
          [M TUM], [52.7], [0.48],
          [V R3D], [12.6], [1.73],
          [M R3D], [59.3], [0.84],
          [M ADVIO], [165.5], [2.78],
        )

        #v(0.35em)
        #compact_note[
          Local telemetry: SLAM-stage latency and accepted-keyframe throughput. M = MASt3R, V = ViSTA.
        ]
      ]
      #quote-block[
        Evaluated on a single NVIDIA RTX 3080 GPU, AMD Ryzen 7 5700X CPU, 32GB RAM
      ]
    ],
  )
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

// #slide(title: [Future Work: End-to-End Streaming Architecture])[
//   // Flo
//   #set text(size: 12.8pt)
//   #let device_color = rgb("4f7dd6")
//   #let model_color = rgb("7c5cc4")
//   #let pc_color = rgb("2f9e6d")
//   #let muted = rgb("5f6773")
//   #let panel(title, body, color) = block(
//     fill: color.lighten(75%),
//     stroke: 0.75pt + color.lighten(30%),
//     radius: 10pt,
//     inset: 0.7em,
//   )[
//     #align(center)[#text(weight: "bold", fill: color.darken(25%))[#title]]
//     #v(0.35em)
//     #body
//   ]
//   #let flow_arrow(label) = block(width: 100%)[
//     #align(center)[#text(size: 28pt, fill: theme_color_primary_hm)[$arrow.r$]]
//     #align(center)[#text(size: 10.5pt, fill: muted)[#label]]
//   ]
//   #let phone_icon() = box(width: 100%, height: 2.3cm)[
//     #align(center + horizon)[
//       #rect(width: 1.15cm, height: 2.05cm, radius: 9pt, fill: rgb("f8fbff"), stroke: 1.2pt + device_color)[
//         #align(center + horizon)[#circle(radius: 0.18cm, fill: device_color)]
//       ]
//     ]
//   ]
//   #let model_icon() = box(width: 100%, height: 2.3cm)[
//     #align(center + horizon)[
//       #grid(
//         columns: (auto, auto, auto),
//         rows: (auto, auto, auto),
//         gutter: 0.25cm,
//         circle(radius: 0.16cm, fill: model_color),
//         circle(radius: 0.16cm, fill: model_color),
//         circle(radius: 0.16cm, fill: model_color),

//         circle(radius: 0.16cm, fill: model_color),
//         rect(width: 0.9cm, height: 0.55cm, radius: 4pt, fill: model_color.lighten(25%), stroke: 0.6pt + model_color),
//         circle(radius: 0.16cm, fill: model_color),

//         circle(radius: 0.16cm, fill: model_color),
//         circle(radius: 0.16cm, fill: model_color),
//         circle(radius: 0.16cm, fill: model_color),
//       )
//     ]
//   ]
//   #let pc_icon() = box(width: 100%, height: 2.3cm)[
//     #align(center + horizon)[
//       #grid(
//         columns: auto,
//         rows: (auto, auto),
//         gutter: 0.08cm,
//         rect(width: 2.0cm, height: 1.25cm, radius: 4pt, fill: rgb("f8fbff"), stroke: 1.1pt + pc_color)[
//           #align(center + horizon)[#text(size: 10pt, fill: pc_color.darken(20%))[viewer]]
//         ],
//         align(center)[#rect(width: 0.8cm, height: 0.12cm, radius: 2pt, fill: pc_color)],
//       )
//     ]
//   ]

//   #grid(
//     columns: (1fr, 0.42fr, 1fr, 0.42fr, 1fr),
//     align: horizon,
//     gutter: 0.25cm,
//     [
//       #panel(
//         [Phone],
//         [
//           #phone_icon()
//           #v(0.25em)
//           - RGB stream
//           - timestamps
//           - optional ARKit/ARCore pose
//         ],
//         device_color,
//       )
//     ],
//     [#flow_arrow([network transport])],
//     [
//       #panel(
//         [VSLAM Model],
//         [
//           #model_icon()
//           #v(0.25em)
//           - frame buffer
//           - method adapter
//           - trajectory + dense cloud
//         ],
//         model_color,
//       )
//     ],
//     [#flow_arrow([artifacts + updates])],
//     [
//       #panel(
//         [PC / Operator],
//         [
//           #pc_icon()
//           #v(0.25em)
//           - live visualization
//           - persisted metrics
//           - operator-facing map
//         ],
//         pc_color,
//       )
//     ],
//   )
// ]

//   #v(0.45em)
//   #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: (x: 0.7em, y: 0.45em))[
//     Future work is not only the model: the system needs a robust peripheral pipeline from capture to inference to display.
//   ]
// ]

#slide(title: [Future Work])[
  - Benchmark vSLAM methods against SfM pipelines like COLMAP
  - Quantify the dependence of vSLAM methods on frame rate, image resolution, and other potential domain shifts.
  - Evaluate gains in point-cloud quality from subsequent reconstruction stages like TSDF, Gaussian Splatting or Poisson Surface Reconstruction.
  - Improve standardization of pre- & post-processing steps for vSLAM evaluation, i.e. spatial downsampling before ICP @zhang2026vistaslam.
]

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
      - *Hard to run the methods on limited hardware* — heavy
        tweaking of per-method parameters to fit constrained GPUs.
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

#slide(title: [Method Comparison])[
  #grid(
    columns: (1fr, 1fr, 1fr),
    gutter: 0.6cm,
    [
      *ViSTA-SLAM* @zhang2026vistaslam
      - *Strategy:* Fast, lightweight processing.
      - *Matching:* Symmetric two-view geometry.
      - *Memory:* Traditional $op("Sim")(3)$ pose graph.
    ],
    [
      *MASt3R-SLAM* @murai2025mast3rslam
      - *Strategy:* Robust "in-the-wild" accuracy.
      - *Matching:* Ray-space Foundation Model.
      - *Memory:* Adapts to dynamic intrinsics.
    ],
    [
      *LingBot-Map* @chen2026gct
      - *Strategy:* Continuous long-range streaming.
      - *Matching:* Transformer token attention.
      - *Memory:* Learned geometric buffer.
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
]

#slide(title: [Future Work: Performance Optimizations])[
  // Flo
  #set text(size: 13.2pt)
  #let active_frame = rgb("4f7dd6")
  #let skipped_frame = rgb("d9dee8")
  #let frame(active: true) = rect(
    width: 0.78cm,
    height: 0.48cm,
    radius: 3pt,
    fill: if active { active_frame } else { skipped_frame },
    stroke: 0.45pt + if active { active_frame.darken(20%) } else { skipped_frame.darken(18%) },
  )
  #let frame_row(label, frames) = grid(
    columns: (1.0fr, auto, auto, auto, auto, auto, auto, auto, auto),
    align: horizon,
    gutter: 0.16cm,
    [#text(weight: "semibold")[#label]],
    ..frames,
  )
  #let image_box(width, height) = rect(
    width: width,
    height: height,
    radius: 5pt,
    fill: rgb("eef3ff"),
    stroke: 0.7pt + rgb("9bb7e5"),
  )

  #grid(
    columns: (1fr, 1fr),
    gutter: 0.75cm,
    [
      #block(fill: rgb("fbfcff"), stroke: 0.7pt + rgb("d9dee8"), radius: 9pt, inset: 0.7em)[
        #text(weight: "bold")[Option 1: reduce resolution]
        #v(0.55em)
        #align(center)[
          #grid(
            columns: (auto, auto, auto, auto, auto),
            align: horizon,
            gutter: 0.25cm,
            image_box(2.45cm, 1.62cm),
            [#text(size: 22pt, fill: theme_color_primary_hm)[$arrow.r$]],
            image_box(1.85cm, 1.22cm),
            [#text(size: 22pt, fill: theme_color_primary_hm)[$arrow.r$]],
            image_box(1.25cm, 0.82cm),
          )
        ]
        #v(0.55em)
        - fewer pixels per frame
        - lower GPU memory and compute
        - risk: weaker feature/detail quality
      ]
    ],
    [
      #block(fill: rgb("fbfcff"), stroke: 0.7pt + rgb("d9dee8"), radius: 9pt, inset: 0.7em)[
        #text(weight: "bold")[Option 2: increase frame stride]
        #v(0.45em)
        #frame_row([stride 1], (
          frame(),
          frame(),
          frame(),
          frame(),
          frame(),
          frame(),
          frame(),
          frame(),
        ))
        #v(0.28em)
        #frame_row([stride 2], (
          frame(),
          frame(active: false),
          frame(),
          frame(active: false),
          frame(),
          frame(active: false),
          frame(),
          frame(active: false),
        ))
        #v(0.28em)
        #frame_row([stride 4], (
          frame(),
          frame(active: false),
          frame(active: false),
          frame(active: false),
          frame(),
          frame(active: false),
          frame(active: false),
          frame(active: false),
        ))
        #v(0.55em)
        - fewer frames through SLAM
        - improves throughput directly
        - risk: larger motion gaps and tracking failures
      ]
    ],
  )

  #v(0.55em)
  #block(fill: rgb("f4f6fb"), stroke: 0.6pt + rgb("d9dee8"), radius: 6pt, inset: (x: 0.7em, y: 0.45em))[
    Goal: measure quality/runtime tradeoffs instead of optimizing for speed blindly.
  ]
]
