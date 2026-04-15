#import "../_shared/meeting-blocks.typ": meeting_detail_slide
#import "../../template.typ": *

#let proposal_detail_body = items => [
  #meeting_detail_slide(items, title: [What already works today])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.8cm,
      [
        *Benchmark & Streaming foundation* \
        - Typed `RunRequest`, `RunPlan`, `SequenceManifest`, and `RunSummary` define the pipeline flow.
        - Canonical artifacts resolve under `input`, `slam`, `dense`, `evaluation`, and `summary`.
        - TOML-based planning & streamlit overwrites.
        - Offline and streaming runner paths.
        - ViSTA-SLAM wrapper and mock-slam backend.
        - Protocols & DTOs for all stages are defined and partially implemented.
      ],
      [
        *User-facing surfaces* \
        - The workbench exposes `Record3D`, `ADVIO`, `Pipeline` edit and run interfaces.
        - Streaming demo from `Record3D` & `ADVIO`.
        - The CLI & App support dataset inspection, device discovery, pipeline stage configuration.
        - WIP rerun interface for live and offline visualization.
      ],
    )
  ]

  // #meeting_detail_slide(items, title: [What ViSTA changes])[
  //   #grid(
  //     columns: (1fr, 1fr),
  //     gutter: 0.8cm,
  //     [
  //       *Strategic pivot* \
  //       - ViSTA-SLAM already implements much of the benchmark and streaming pipeline we expected to build ourselves (webcam stream, benchmark pipeline)
  //       - ViSTA becomes the primary baseline and inspiration.

  //       #quote-block()[
  //         Build a more streamlined, modular evaluation and streaming framework.
  //       ]
  //     ],
  //     [
  //       *What actually remains* \
  //       - Integrate ViSTA-SLAM into the repo-owned artifact flow.

  //       #v(0.9em)
  //       *Priority rule* \
  //       - Remaining work should increase method readiness, benchmark readiness, or report readiness.
  //     ],
  //   )
  // ]
]
