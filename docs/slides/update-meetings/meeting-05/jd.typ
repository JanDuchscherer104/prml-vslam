#import "../_shared/meeting-blocks.typ": meeting_detail_slide
#import "@preview/booktabs:0.0.4": *

#let alignment_results_table() = [
  #show: booktabs-default-table-style
  #show table.cell.where(y: 0): set text(weight: "bold")
  #table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    inset: (x: 0.34em, y: 0.24em),
    toprule(),
    table.header([Sequence], [Sim(3) $s$], [ICP fitness], [ICP inlier RMSE]),
    midrule(), [TUM `cabinet`], [$1.60$], [$0.44$],
    [$2.7 "cm"$], [R3D `29-08`], [$3.79$], [$0.015$],
    [$3.7 "cm"$], [Lingbot `cabinet`], [$4.44$], [$0.47$],
    [$5.4 "cm"$], bottomrule(),
  )
  - for inlier threshold #text(fill: color.red)[$tau$=5cm].
  - Choice of #text(fill: color.red)[$tau$]?
]

#let done_table_row = (
  (
    [WP2.3],
    [JD],
    [MASt3R-SLAM: merged branch, added missing artifact, `pyproject` integration.],
  ),
  (
    [WP1],
    [JD],
    [ADVIO: GT-aligned ARKit/ARCore references. Debug #sym.arrow.squiggly prune TANGO data.],
  ),
  (
    [WP1],
    [JD],
    [*Record3D*: added *offline* dataset support, recorded 9 scenes - #link("https://zenodo.org/records/20591352?preview=1&token=eyJhbGciOiJIUzUxMiJ9.eyJpZCI6ImRmYTc3N2U0LWMyY2ItNDRmNy1hYTYxLWRmMTc2YmQ5YjMyYSIsImRhdGEiOnt9LCJyYW5kb20iOiJlNzc2YmNmN2YyN2NiOGMwMWVhZTM4YWIxY2E0MGUwNyJ9._9NhvbXgkwR6PxjXyn6rbbx_tTUtb0wFnQt6bXBIfbIaNZIHeW6B8YDoug_Li6NoE3H5-GrzfLnNDwPXae8hDg")[Zenodo]],
  ),
  (
    [WP1],
    [JD],
    [Added *normalized datset store* to unify dataset prep and run-time ],
  ),
  (
    [WP4.3],
    [JD],
    [Added *ICP* and fixed *Sim(3) point-cloud alignment*.],
  ),
  (
    [WP4.3],
    [JD],
    [Streamlined `*.ply` (*PC*) artifact generation from dense depth and point maps.],
  ),
  (
    [WP8],
    [JD],
    [Streamlined Rerun logging: Added new diagnostics and fixed streaming rerun logs.],
  ),
  (
    [WP2.4],
    [JD],
    [Implemented #link("https://github.com/robbyant/lingbot-map")[*lingbot-map*] integration as 3rd method],
  ),
  (
    [WP2.1],
    [JD],
    [Benchmark sweep orchestration and automation.],
  ),
)

#let challenges_table_row = (
  ([WP1], [JD], [ADVIO Tango PCs (various frames conventions, noisy, not interpretable)]),
  (
    [WP1],
    [JD],
    [ADVIO ARKit/ARCore references could *not* be normalized without explicit SIM(3) alignment. No *frame* convention issue was present.],
  ),
  (
    [WP1/2/8],
    [JD],
    [Source #sym.arrow.l.r vSLAM #sym.arrow.l.r Viewer frame convention & transform issues #sym.arrow.l.r  edge cases.],
  ),
)

#let next_steps_table_row = (
  [WP1],
  [JD],
  [Finalize normalized datastore - some clean-up needed.],
  [WP5],
  [JD],
  [Complete and merge benchmark sweep framework.],
)

#let done_detail_body = items => [
  #show bibliography: none
  #bibliography("../../../references.bib")

  #meeting_detail_slide(items, title: [JD: ADVIO/Tango Semantics])[
    #grid(
      columns: (1.15fr, 0.85fr),
      gutter: 0.65cm,
      [
        #figure(
          grid(
            columns: (1fr, 1fr),
            gutter: 0.18cm,
            image(
              "../../../figures/evidence/advio-20-jagged-vista-traj-discontinuities.png",
              width: 100%,
            ),
            [#image(
                "../../../figures/evidence/advio-20-all-traj-arkit+arcore+ccw-vs-vista+gt+cw.png",
                width: 100%,
              )
              #image(
                "../../../figures/evidence/advio-20-all-traj-aligned-to-gt.png",
                width: 100%,
              )
            ],
          ),
          caption: [ADVIO-20 trajectories: ViSTA discontinuities, source-native AR references, and GT-aligned ARKit/ARCore overlays.],
        )
      ],
      [
        #text(size: 15pt)[
          *Diagnosis and fix*

          - ADVIO ARKit/ARCore were not frame convention / fixed-point-issues.
          - Provider worlds differ from GT by yaw and scale and required explicit Sim(3) alignment.
          - `to_benchmark_inputs` now emits GT-ALIGNED and LOCAL ARKit/ARCore trajectories.
          - #text(fill: color.red)[*Gravity-locked*] yaw+scale+translation fixes the up axis, so near-planar trajectories cannot flip upside down.
        ]
      ],
    )

    *Gravity-locked ADVIO variant*

    $
      bold(S)_"a"^"g*" =
      arg min_(s, theta, bold(t)) sum_i
      norm(bold(x)_i^"g" - (s bold(R)_"yaw" (theta) bold(x)_i^"a" + bold(t)))^2,
      quad
      #text(fill: color.red)[$bold(R)_"yaw" bold(u) = bold(u)$]
    $
  ]

  #meeting_detail_slide(items, title: [JD: ViSTA-Style Alignment Geometry])[
    #text(size: 13.4pt)[
      #grid(
        columns: (1fr, 1fr),
        gutter: 0.7cm,
        [
          *Depth to SLAM-local world*

          $
            bold(q)_j = z_j hat(bold(K))_j^(-1) mat(u_j; v_j; 1),
            quad
            bold(p)_j^"v" = hat(bold(T))_"c"^"v" bold(q)_j
          $

          - Backprojection of dense point-maps via predicted _intrinsics_ and _extrinsics_.
          - Backprojection with _uniform stride_ #sym.arrow _random subsampling_ to fixed number of points per frame.

          *1. Shared origin (optional):*

          $ bold(tilde(T))^bullet_k = (bold(T)_0^bullet)^(-1) bold(T)_k^bullet $

          - $bold(tilde(T))^v_k$ and $bold(tilde(T))^r_k$ should now be aligned, but differ by an unknown scale:

          $
            bold(S)_"v"^"w" = (s, bold(R), bold(t)) in "Sim"(3)\
            "Sim"(3) = (bb(R)^+ times "SO"(3)) times.l bb(R)^3
          $
        ],
        [
          *2. Trajectory Sim(3)* \@Valentin

          $
            bold(S)_"v"^"w*" =
            arg min_(bold(S) in "Sim"(3)) sum_(bold(x)_i, bold(x)_j in cal(T)) norm(bold(x)_i - bold(S) bold(x)_j^"v")^2
          $
          $
            bold(P)^"w" = bold(S)_"v"^"w"* bold(P)^"v"
          $
          @grupp2017evo@umeyama1991least

          *3. Point-cloud ICP*

          $
            bold(T)_"icp"^*(bold(P), bold(Q)) =
            arg min_(bold(T) in "SE"(3)) sum_(bold(p) in bold(P)^"w")
            norm(bold(T) bold(p) - op("NN")_Q (bold(T) bold(p)))^2
          $
          $
            cal(C)_tau (bold(T)) =
            { (bold(p), op("NN")_Q (bold(T) bold(p))) |
              bold(p) in bold(P)^"w",
              norm(bold(T) bold(p) - op("NN")_Q (bold(T) bold(p))) <= #text(fill: color.red)[$tau$] }
          $
          @zhang2026vistaslam@zhou2018open3d

          #v(0.15em)
          #alignment_results_table()
        ],
      )
    ]
  ]

  #meeting_detail_slide(items, title: [JD: Rerun Diagnostics & Evidence])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.75cm,
      [
        #figure(
          image(
            "../../../figures/evidence/tumrgbd-freiburg3_large_cabinet-vista-sim3-pc+traj-assoiciations.png",
            width: 100%,
          ),
          caption: [TUM RGB-D ViSTA Sim(3) point-cloud and trajectory associations.],
        )
      ],
      [
        - `.rrd` recordings show: references, SLAM output, aligned trajectories & clouds, APE trajectories, correspondence strips, and scalar series.

          #figure(
            image(
              "../../../figures/evidence/record3d-29-08-pc+traj.png",
              width: 100%,
            ),
            caption: [Record3D 29-08 point-cloud and trajectory associations. GT point cloud is mint green.],
          )
      ],
    )
  ]

  #meeting_detail_slide(items, title: [JD: Offline Artifacts])[
    #let stage_title(body) = text(size: 12pt, weight: "bold")[#align(horizon + center)[#body]]
    #let note(body) = text(size: 9.5pt)[#align(horizon + center)[#body]]
    #text(size: 7.4pt)[
      #grid(
        columns: (1.05fr, 1.12fr, 0.9fr, 0.93fr),
        rows: (auto, auto),
        gutter: 0.22cm,
        [
          #stage_title[1. Normalized Inputs]
          #align(center)[#image("../../../figures/evidence/record3d-entry.png", width: 95%)]
          #note[Normalized Record3D dataset entry.]
          #image("../../../figures/evidence/tum-cabinet-artifact-input-benchmark.png")
          #note[Source frames & Benchmark inputs.]
        ],
        [
          #stage_title[4. SLAM]
          #image("../../../figures/evidence/tum-cabinet-artifact-vista-native.png", width: 100%)
          #note[Native ViSTA outputs.]
          #image("../../../figures/evidence/tum-cabinet-artifact-slam.png", width: 100%)
          #note[Standardized SLAM artifacts.]
        ],
        [
          #stage_title[3. Gravity Alignment]
          #image("../../../figures/evidence/tum-cabinet-artifact-ground-alignment.png", width: 100%)
          #note[RANSAC based gravity alignment]

          #stage_title[4. Reconstruction]
          #image("../../../figures/evidence/tum-cabinet-artifact-reconstruction.png", width: 100%)
          #note[TSDF reconstruction.]
        ],
        [
          #stage_title[5. Evaluation]
          #image("../../../figures/evidence/tum-cabinet-artifact-evaluation.png", width: 100%)
          #note[
            Sim(3)/ICP-aligned PLY artifacts, trajectory and point-cloud metrics and diagnostics.
          ]
          #stage_title[6. Summary + visualization]
          #image("../../../figures/evidence/tum-cabinet-artifact-summary+visualization.png", width: 100%)
          #note[Run metadata, artifact manifests, run events, and persisted Rerun recording.]
        ],
      )
    ]
  ]
]

#let challenges_detail_body = none

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: Challenges & Roadmap])[
    - ViSTA-SLAM, MASt3R-SLAM & LingBot-Map benchmark runs.
    - Validate offline Record3D replay and streaming `gravity.align` / `test-tumrgbd-align-rerun`.
    - Materialize normalized datasets for repeated runs.
  ]
]
