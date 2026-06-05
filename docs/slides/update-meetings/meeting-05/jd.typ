#import "../_shared/meeting-blocks.typ": meeting_detail_slide

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
    [*Record3D*: added *offline* dataset support, recorded 10 scenes],
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
    [Experimental #link("https://github.com/robbyant/lingbot-map")[lingbot-map] integration as 3rd method],
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
    [Source #sym.arrow.l.r vSLAM #sym.arrow.l.r Viewer frame convention & transform issues.],
  ),
)

#let next_steps_table_row = (
  [WP1],
  [JD],
  [Merge Record3D (opt. normalized dataset caches), upload Record3D scenes.],
  [WP5],
  [JD],
  [Run benchmarks on ViSTA and MASt3R-SLAM.],
  [WPX],
  [JD],
  [Merge streaming ground alignment.],
)

#let done_detail_body = items => [

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

          - #link("https://github.com/AaltoVision/ADVIO")[ADVIO] ARKit/ARCore were not frame convention / fixed-point-issues.
          - Provider worlds differ from GT by yaw and scale and required explicit Sim(3) alignment.
          - `to_benchmark_inputs` now emits GT-ALIGNED and LOCAL ARKit/ARCore trajectories.
          - Gravity-locked yaw+scale+translation fixes the up axis, so near-planar trajectories cannot flip upside down.
        ]
      ],
    )

    *Gravity-locked ADVIO variant*

    $
      bold(S)_"a"^"g*" =
      arg min_(s, theta, bold(t)) sum_i
      norm(bold(x)_i^"g" - (s bold(R)_"yaw" (theta) bold(x)_i^"a" + bold(t)))^2,
      quad
      bold(R)_"yaw" bold(u) = bold(u)
    $
  ]

  #meeting_detail_slide(items, title: [JD: TUM RGB-D & Dataset Prep])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.75cm,
      [
        *Benchmark frame*

        - #link("https://cvg.cit.tum.de/data/datasets/rgbd-dataset")[TUM RGB-D] RGB-D poses and depth-derived references normalize into the first-camera benchmark world.
        - Mocap/GT remains provenance; aligned artifacts target `tum_rgbd_world`.
        - Shared depth-to-world helpers produce reference clouds from method-observation-compatible inputs.
      ],
      [
        *Dataset preparation*

        - ADVIO and TUM RGB-D downloads now expose scene selection plus overwrite/reuse only.
        - Modality/package selection was removed from app and CLI surfaces.
        - Full-scene readiness keeps benchmark runs from mixing partial local payloads with complete-sequence assumptions.
      ],
    )
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

          - #link("https://github.com/zhangganlin/vista-slam")[ViSTA] keeps dense pointmaps camera-local before pose-lifting them.
          - `v` is the SLAM-local world; `w` is the benchmark world.

          *Shared anchor: the start camera*

          $ bold(T)'_k = (bold(T)_0^"r")^(-1) bold(T)_k^"r" $

          - vSLAM starts at identity in `v`; TUM GT is relativized by its own first pose into first-camera RDF `w`.
          - This is only a shared convention, not $bold(T)_0^"v" = bold(T)_0^"r"$; the Sim(3) still uses all timestamp-associated pairs.

          $
            bold(S)_"v"^"w" = (s, bold(R), bold(t)) in "Sim"(3)\
            "Sim"(3) = (bb(R)^+ times "SO"(3)) times.l bb(R)^3
          $
        ],
        [
          *Trajectory Sim(3), then ICP*

          $
            bold(S)_"v"^"w*" =
            arg min_(bold(S) in "Sim"(3)) sum_i norm(bold(x)_i^"r" - bold(S) bold(x)_i^"v")^2
          $

          $
            bold(p)^"w" = s bold(R) bold(p)^"v" + bold(t),
            quad
            bold(P)^"w" = bold(S)_"v"^"w"* bold(P)^"v"
          $

          $
            bold(T)_"icp"^* =
            arg min_(bold(T) in "SE"(3)) sum_(bold(p) in bold(P)^"w")
            norm(bold(T) bold(p) - op("NN")_Q (bold(T) bold(p)))^2
          $

          - Associate estimate/GT samples within $0.01 "s"$; $"NN"_Q$ = nearest point in `Q`.
          - `advio_*_world`: yaw-only about RDF gravity; `tum_rgbd_world`: full Umeyama unchanged.
          - ADVIO-20: ARKit/ARCore now turn CW like GT; vSLAM-to-GT up-axis tilt $25.33degree -> 0.00degree$.
          - TUM `freiburg3_large_cabinet` ($tau = 5 "cm"$): Sim(3) $s = 1.60$, 26 pairs; APE RMSE $17.6 "cm"$; ICP $"fitness"_("@"tau) = 0.44$, $"inlier RMSE"_("@"tau) = 2.7 "cm"$.
          - ADVIO-20 contrast ($tau = 5 "cm"$): Sim(3) RMSE $1.31 "m"$; $"fitness"_("@"tau) approx 0$ --- clouds barely overlap, so the $2.8 "cm"$ inlier RMSE is uninformative.
          - _Metrics:_ $"fitness"_("@"tau)$ = matched estimate fraction; $"inlier RMSE"_("@"tau)$ = inlier residual; APE RMSE = pose-pair error.
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
        - `.rrd` recordings now show source references, SLAM output, aligned trajectories, and aligned clouds together.
        - Rerun paths stay method-neutral through `world/slam/...` and stable source-reference entities.
        - Export diagnostics add APE trajectories, correspondence strips, and scalar series.
        - Live and export sinks own separate lifecycles, so export-only evidence can be added without changing live routing.

        #rect(
          width: 100%,
          height: 2.1cm,
          stroke: (paint: rgb("#bbbbbb"), dash: "dashed"),
          inset: 0.25cm,
        )[
          #align(center + horizon)[
            *Record3D offline evidence placeholder* \
            Expected: replay, SLAM output, Sim(3) trajectory/cloud alignment
          ]
        ]
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
          #stage_title[1. Input]
          #image("../../../figures/evidence/tum-cabinet-artifact-input.png")
          #note[Normalized source frames (VSLAM input).]
          #stage_title[2. Benchmark Artifacts]
          #align(center)[#image("../../../figures/evidence/vista-20-artifact-benchmark.png", width: 80%)]
          #note[Benchmark inputs (reference & GT data, ADVIO).]
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

  #meeting_detail_slide(items, title: [JD: Runtime & Method Cleanup])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.75cm,
      [
        *Runtime surfaces*

        - Streamlit live action buttons now use explicit stable keys across pipeline, #link("https://record3d.app/")[Record3D], and dataset pages.
        - Dead `ReferencePointCloudSequenceRef` surfaces were removed.
        - The source-stage boundary is now `ReferenceCloudRef` plus metadata.
      ],
      [
        *Method artifacts*

        - Offline ViSTA keyframe payloads can reach export visualization.
        - Confidence metadata is persisted beside the native ViSTA dense cloud.
        - Upstream confidence-filtered clouds remain unchanged; extra artifacts explain coverage and color/metric readiness.
      ],
    )
  ]
]

#let challenges_detail_body = none

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: Challenges & Roadmap])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.75cm,
      [
        *Technical challenges*

        - Dataset and method outputs expose different native coordinate assumptions.
        - Near-planar ADVIO walks made full Sim(3) underconstrained around horizontal axes; gravity-locking fixes trajectory overlay, but dense-cloud overlap still needs separate evidence.
        - Large initial cloud offsets make ICP refinement easy to over-trust.
        - Rerun evidence only helps when paths, metadata, and artifacts describe one transform chain.
      ],
      [
        *Roadmap*

        - Finish ViSTA-SLAM and MASt3R-SLAM benchmark runs.
        - Extend evo coverage and add cloud metrics over persisted PLY artifacts.
        - Validate offline Record3D replay and streaming `gravity.align` / `test-tumrgbd-align-rerun`.
        - Materialize normalized datasets for repeated runs.
        - Upgrade Rerun/dependency stack in a dedicated pass.
        - Feed colored SLAM point clouds into TSDF reconstruction on the CUDA path.
      ],
    )
  ]
]
