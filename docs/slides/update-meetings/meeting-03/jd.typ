#import "../_shared/meeting-blocks.typ": meeting_detail_slide

#let pipeline_diagram(path) = image(
  path,
  width: 100%,
  height: 95%,
  fit: "contain",
)

#let done_table_row = (
  (
    [WP2],
    [JD],
    [Unified `StageRuntime` boundaries with cleaner DTOs for stage I/O, runtime status, live updates, payload refs, and artifacts.],
  ),
  ([WP2], [JD], [Implemented the Ray-backed pipeline path plus throughput / latency metrics.]),
  (
    [WP2],
    [JD],
    [Persisted streamlined artifacts, manifests, and stage output data for reproducibility and post-hoc inspection.],
  ),
  ([WP3], [JD], [Added TUM RGB-D support and real-time streaming adapters for ADVIO and TUM RGB-D.]),
  ([WP4], [JD], [Added RANSAC ground-plane detection and an offline-only Open3D TSDF reconstruction stage.]),
  ([WP3], [JD], [Fixed ViSTA pre-/post-processing and transform issues.]),
  ([WP7], [JD], [Extended Rerun live/output visualization and Streamlit artifact inspection.]),
)

#let challenges_table_row = (
  [WP2 / WP4 / WP9],
  [JD],
  [Making a typed multiprocessing pipeline agree with dataset frames, live streaming, Rerun, app state, and artifacts.],
)

#let next_steps_table_row = (
  [WP9 / WP10],
  [JD],
  [Finish clean stage APIs/configs, merge team changes, fix ADVIO references, and validate the final refactor.],
)

#let done_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: What Was Done?])[
    - Unified `StageRuntime` boundaries with cleaner DTOs for stage I/O, runtime status, live updates, payload refs, and artifacts.
    - Implemented the Ray-backed pipeline path plus throughput / latency metrics.
    - Persisted streamlined artifacts, manifests, and stage output data for reproducibility and post-hoc inspection.
    - Added TUM RGB-D support and real-time streaming adapters for ADVIO and TUM RGB-D.
    - Added RANSAC ground-plane detection and an offline-only Open3D TSDF reconstruction stage.
    - Fixed ViSTA pre-/post-processing and transform issues.
    - Extended Rerun live/output visualization and Streamlit artifact inspection.
  ]

  #meeting_detail_slide(items, title: [JD: Evidence])[
    #grid(
      columns: (1fr, 1.5fr),
      gutter: 0.0cm,
      [
        #figure(
          image("../../../figures/evidence/advio-20-vista-3d-scene.png", width: 100%),
          caption: [ADVIO 20 ViSTA Rerun scene.],
        ) <fig:advio-20-vista-3d-scene>
      ],
      [
        #figure(
          image("../../../figures/evidence/tum-freiburg-room-tsdf-mesh.png", height: 40%),
          caption: [TUM Freiburg room offline TSDF mesh.],
        ) <fig:tum-freiburg-room-tsdf-mesh>

        #figure(
          image("../../../figures/evidence/ransac.png", width: 60%),
          caption: [Ransac Ground Plane.],
        ) <fig:ransac>
      ],
    )
  ]

  #meeting_detail_slide(items, title: [JD: Run Artifacts])[
    #grid(
      columns: (0.72fr, 1.28fr),
      gutter: 0.55cm,
      [
        #set text(size: 0.62em)
        ```text
        .artifacts/<experiment>/<run>/
        ├── input/
        ├── benchmark/
        ├── slam/
        ├── native/
        ├── alignment/
        ├── reference/
        ├── visualization/
        └── summary/
        ```
      ],
      [
        #set text(size: 0.78em)
        == Folder contract
        - Input: normalized frames, timestamps, intrinsics.
        - Benchmark: reference trajectories, RGB-D/Tango references.
        - SLAM/native/alignment: method output plus derived metadata.
        - Reference/visualization/summary: TSDF outputs, Rerun, manifests, events.

        == Why it matters
        - Each run is a self-contained bundle for reproducibility and post-hoc inspection.
        - Stage manifests index completed stage outputs with config hashes and input fingerprints.
        - Inspect source inputs, references, SLAM, alignment, reconstruction, Rerun, and validation artifacts without rerunning.

        == Example: `vista-full-tuning/vista`
        - Total 4.2 GB; input 2.1 GB; visualization 2.0 GB.
        - SLAM 36 MB; native 63 MB; reference 29 MB.
      ],
    )
  ]


  #meeting_detail_slide(items, title: [JD: Run Config To Plan])[
    #figure(
      pipeline_diagram("../../../figures/mermaid/pipeline/03-run-config-stage-plan.png"),
      caption: [`RunConfig` compiles named stage sections into an ordered `RunPlan` before runtime construction starts.],
    ) <fig:pipeline-run-config-stage-plan>
  ]

  #meeting_detail_slide(items, title: [JD: Runtime Protocols])[
    #figure(
      pipeline_diagram("../../../figures/mermaid/pipeline/04-runtime-protocols.png"),
      caption: [`BaseStageRuntime`, `OfflineStageRuntime`, `LiveUpdateStageRuntime`, and `StreamingStageRuntime` separate capability from local/Ray deployment.],
    ) <fig:pipeline-runtime-protocols>
  ]

  #meeting_detail_slide(items, title: [JD: Stage Result])[
    #figure(
      pipeline_diagram("../../../figures/mermaid/pipeline/06-stage-result.png"),
      caption: [`StageResult` is the internal terminal handoff; durable events and manifests carry `StageOutcome`.],
    ) <fig:pipeline-stage-result>
  ]

  #meeting_detail_slide(items, title: [JD: Live Updates])[
    #figure(
      pipeline_diagram("../../../figures/mermaid/pipeline/07-runtime-updates-visualization.png"),
      caption: [`StageRuntimeUpdate` feeds live projection and Rerun through neutral `VisualizationItem`s, not SDK calls in DTOs.],
    ) <fig:pipeline-runtime-updates-visualization>
  ]

]

#let challenges_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: Challenges])[
    - Typed multiprocessing across Ray, stages, app state, Rerun, artifacts, and manifests.
    - Clear ownership for streaming packets, SLAM updates, transient payloads, viewer output, and durable artifacts.
    - ADVIO frame semantics across GT, ARCore, ARKit, Tango poses, point clouds, and benchmark estimates.
    - Normalizing TUM RGB-D, ADVIO, and ViSTA timestamps, intrinsics, rasters, and transforms.
  ]
]

#let next_steps_detail_body = items => [
  #meeting_detail_slide(items, title: [JD: Next Steps])[
    - Finalize clean stage APIs and config management.
    - Make stages easier to edit, add, and validate.
    - Merge team changes into the unified `StageRuntime` path.
    - Fix ADVIO frame/reference issues for unified trajectory benchmarking.
    - Expose ADVIO reference point clouds to later stages.
    - Validate stage tests, app/CLI smoke paths, ADVIO/TUM runs, Rerun output, and full CI.
  ]
]
