#import "../template.typ": *

#let team_members = [
  // Florian Beck, Valentin Bumeder, Lukas Röß, Christopher Kirschner, Jan Duchscherer
  Jan Duchscherer, Lukas Röß, Christopher Kirschner, Valentin Bumeder, Florian Beck
]

#let footer_members = [
  J. Duchscherer, L. Röß, C. Kirschner, V. Bumeder, F. Beck
]

#let final_slide(title, body) = slide(
  title: title,
  footer: project_footer(
    footer_authors: footer_members,
    footer_label: [Final Presentation],
    footer_date: [29 Jun 2026],
  ),
)[#body]

#let compact_note(body) = block(
  fill: rgb("f4f6fb"),
  inset: (x: 0.7em, y: 0.55em),
  radius: 6pt,
  stroke: 0.6pt + rgb("d9dee8"),
)[#body]

#project_deck(
  title: [Uncalibrated Monocular VSLAM],
  subtitle: [JD contribution seed for final report and presentation],
  authors: team_members,
  footer_authors: footer_members,
  extra: [Pattern Recognition & Machine Learning],
  footer_label: [Final Presentation],
  footer_date: [29 Jun 2026],
)[
  #title-slide()

  #final_slide([JD Evidence Cluster])[
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
        - LingBot planning-final integration.
      ],
      [
        #compact_note[
          The final deck remains a five-person presentation. These slides only collect the JD-first evidence that future agents can refine and rebalance.
        ]
      ],
    )
  ]

  #final_slide([Pipeline Framework])[
    #grid(
      columns: (1.05fr, 0.95fr),
      gutter: 0.65cm,
      [
        - `RunConfig` compiles into a deterministic `RunPlan`.
        - Runtime order: `source -> slam -> gravity.align -> evaluate.trajectory -> reconstruction -> evaluate.cloud -> summary`.
        - `StageResult` is the typed terminal handoff.
        - `StageRuntimeUpdate` carries live telemetry and neutral visualization items.
        - Run artifacts, manifests, and summaries are the reproducibility contract.
      ],
      [
        #figure(
          image("../../figures/mermaid/pipeline/03-run-config-stage-plan.png", width: 100%),
          caption: [`RunConfig` to stage plan.],
        )
      ],
    )
  ]

  #final_slide([Datasets And Normalization])[
    #grid(
      columns: (1fr, 1fr, 1fr),
      gutter: 0.45cm,
      [
        *ADVIO*
        - Smartphone VIO benchmark.
        - GT, ARKit, ARCore provider trajectories.
        - Trajectory-first in this repo.
        - Explicit provider-frame alignment.
      ],
      [
        *TUM RGB-D*
        - RGB, depth, and mocap GT.
        - RGB-D replay and deterministic reference clouds.
        - First-camera RDF normalization.
        - Strong alignment/debug dataset.
      ],
      [
        *Record3D*
        - iPhone RGB-D capture and streaming.
        - Live USB / Wi-Fi Preview on main.
        - PR 88 offline `.r3d` and normalized store.
        - Custom-scene evidence source.
      ],
    )
  ]

  #final_slide([Method Adapters])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.7cm,
      [
        *ViSTA-SLAM*
        - Preserves upstream crop/resize preprocessing.
        - Uses RDF camera geometry and `T_world_camera`.
        - SLAM world is local, not benchmark-global.
        - Normalizes `trajectory.tum` and dense point-cloud artifacts.
      ],
      [
        *LingBot / GCT*
        - Feed-forward streaming 3D reconstruction candidate.
        - Anchor context fixes coordinate/scale reference.
        - Pose-reference window carries dense recent geometry.
        - Trajectory memory limits long-range drift with compact state.
        - PR 91 still requires final artifact validation.
      ],
    )
  ]

  #final_slide([Frames, Transforms, Alignment])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        *Why this matters*
        - Source camera frame, SLAM-local world, benchmark world, and viewer world are separate.
        - Visual overlap in Rerun does not prove metric comparability.
        - Monocular outputs require explicit scale policy before reporting metrics.
      ],
      [
        *Current policy*
        - Trajectory: Sim(3) alignment for APE where appropriate.
        - ADVIO providers: gravity-locked yaw, scale, and translation when up is trusted.
        - Clouds: trajectory Sim(3) placement, then ICP as diagnostic refinement.
        - Report ICP threshold, fitness, and inlier RMSE.
      ],
    )
  ]

  #final_slide([Rerun Diagnostics])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        - Rerun is the viewer and debugging layer, not the metric source of truth.
        - Live/export logging is separated from stage DTOs through neutral visualization items.
        - `.rrd` recordings expose references, SLAM output, aligned trajectories, correspondence strips, and scalar series.
        - Frame placement bugs are easiest to catch visually, then validate from artifacts.
      ],
      [
        #figure(
          image("../../figures/evidence/advio-20-vista-3d-scene.png", width: 100%),
          caption: [Example ADVIO ViSTA Rerun scene.],
        )
      ],
    )
  ]

  #final_slide([Evidence To Carry Forward])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        *Report anchors*
        - `src/prml_vslam/pipeline/README.md`
        - `src/prml_vslam/sources/README.md`
        - `src/prml_vslam/methods/vista/README.md`
        - `src/prml_vslam/alignment/README.md`
        - `src/prml_vslam/eval/README.md`
        - `src/prml_vslam/visualization/README.md`
      ],
      [
        *Planning inputs*
        - `.agents/references/report-final-slides/`
        - `.omx/specs/report-final-slides/report-section-candidates.md`
        - PR 86 JD update slides.
        - PR 88 Record3D normalized-store work.
        - PR 91 LingBot method work.
        - Final metrics and artifacts before publication claims.
      ],
    )
  ]
]
