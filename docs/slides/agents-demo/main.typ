#import "../template.typ": *

#let deck_title = [#text(size: 35pt)[PRML VSLAM Agent Demo]]
#let deck_subtitle = [Design decisions, design patterns, and package choices]
#let deck_authors = [PRML VSLAM Team]
#let deck_extra = [Pattern Recognition & Machine Learning \ Architecture Demo]

#let stage_chip(fill, title, body) = color-block(title: title, color-body: fill)[#body]

#project_deck(
  title: deck_title,
  subtitle: deck_subtitle,
  authors: deck_authors,
  footer_label: [Agent Demo],
  extra: deck_extra,
)[
  #title-slide()

  #slide(title: [Why this architecture?])[
    #grid(
      columns: (1.1fr, 0.9fr),
      gutter: 0.7cm,
      [
        #color-block(title: [Challenge constraints])[
          - Unknown intrinsics and mixed device metadata are first-class constraints.
          - We must support both offline benchmarking and a future streaming operator workflow.
          - External SLAM systems are heavy, volatile, and should not define our repo boundary.
          - Evaluation must stay reproducible even when wrappers, hardware, or backends change.
        ]
      ],
      [
        #color-block(title: [Primary design goal])[
          Build a benchmark scaffold that is:

          - easy to test before any real SLAM backend runs
          - explicit about frames, units, and timestamps
          - stable enough to feed both CLI workflows and the Streamlit workbench
          - ready for batch now and streaming later
        ]

      ],
    )
  ]

  #slide(title: [Architectural guardrails])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.8cm,
      [
        #good-note[
          The repo should own *contracts, artifacts, evaluation, and interpretation*.
          External methods should own only their own inference internals.
        ]
      ],
      [
        #warning-note[
          We deliberately avoid hiding alignment, evaluation, or fallback logic inside method wrappers.
        ]
      ],
    )
  ]

  #slide(title: [Core design decisions])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        #color-block(title: [Ownership boundary])[
          - `prml_vslam` owns planning, artifact layout, normalization, evaluation, plotting, and reporting.
          - ViSTA-SLAM, MASt3R-SLAM, ARCore, COLMAP, and Nerfstudio stay external systems.
        ]
      ],
      [
        #color-block(title: [Artifact contract first])[
          - We write repo-owned manifests, sidecars, and normalized outputs before real wrappers.
          - This makes downstream evaluation and visualization independent of upstream folder layouts.
        ]

        #color-block(title: [Interpretation built in])[
          - Planning is not only about generating paths.
          - The app should explain *why* a stage exists and what its outputs mean.
        ]
      ],
    )
  ]

  #slide(title: [Core design decisions: execution order])[
    #color-block(title: [Batch first])[
      - The first implemented path is batch / offline.
      - Streaming remains a planned mode, but not the first integration target.
      - This gives short TDD loops and deterministic artifacts under `tmp_path`.
      - The same contract remains ready for later streaming-specific stage subsets.
    ]
  ]

  #slide(title: [Config as Factory Pattern])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.75cm,
      [
        #color-block(title: [Two config layers])[
          - `BaseSettings` for machine-local state:
            external repos, dataset roots, checkpoint caches, environment roots.
          - `BaseConfig` for experiment state:
            run requests, stage configs, method configs, evaluation configs, plotting configs.
        ]

        #io-formulation(
          [
            - machine-local environment state
            - experiment request
            - validated nested configs
          ],
          [
            - runtime object via `.setup_target()`
            - serialized TOML / JSON-friendly config snapshots
            - deterministic CLI and UI behavior
          ],
        )
      ],
    )
  ]

  #slide(title: [Config as Factory Pattern: code])[
    #figure(
      code-block(size: 12pt)[
        ```python
        class MethodRunnerConfig(BaseConfig):
            name: str

            @property
            def target_type(self) -> type["MethodRunner"]:
                return MethodRunner


        class MethodRunner:
            def __init__(self, config: MethodRunnerConfig) -> None:
                self.config = config
        ```
      ],
      caption: [Typed config-as-factory pattern],
    )
  ]

  #slide(title: [Stage model: batch now, streaming later])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.6cm,
      [
        #stage_chip(rgb("#dbeafe"), [Batch / offline path], [
          1. `capture_manifest`
          2. `video_decode`
          3. `method_prepare`
          4. `slam_run`
          5. `trajectory_normalization`
          6. `dense_normalization`
          7. `arcore_alignment`
          8. `reference_reconstruction`
          9. `visualization_export`
        ])
      ],
      [
        #stage_chip(rgb("#dcfce7"), [Streaming path (planned)], [
          1. `capture_manifest`
          2. `stream_source_open`
          3. `method_prepare`
          4. `online_tracking`
          5. `chunk_persist`
          6. `stream_finalize`
          7. later normalization and evaluation
        ])
      ],
    )

  ]

  #slide(title: [Stage model: important consequence])[
    #color-block(title: [Important consequence])[
      Each stage should declare whether it supports `batch`, `streaming`, or both.
      The repo-owned stage graph stays the source of truth; any future orchestrator should adapt to
      it, not replace it.
    ]
  ]

  #slide(title: [Normalized artifact contract])[
    #grid(
      columns: (1.05fr, 0.95fr),
      gutter: 0.75cm,
      [
        #color-block(title: [Repo-owned outputs])[
          - `input/capture_manifest.json`
          - `planning/run_request.toml`
          - `planning/run_plan.toml`
          - `slam/trajectory.tum`
          - `slam/trajectory.metadata.json`
          - `dense/dense_points.ply`
          - `dense/dense_points.metadata.json`
          - `evaluation/arcore_alignment.json`
        ]
      ],
      [
        #color-block(title: [Why the sidecars matter])[
          - explicit `T_world_camera` transform naming
          - explicit units in meters and time in seconds
          - explicit timestamp provenance
          - explicit alignment policy such as `none`, `SE(3)`, or `Sim(3)`
          - explicit preprocessing and upstream config snapshots
        ]
      ],
    )

    #v(0.5cm)
    #good-note[
      We never compare raw backend outputs across methods. We normalize first, then evaluate.
    ]
  ]

  #slide(title: [Streamlit workbench pattern])[
    #grid(
      columns: (0.95fr, 1.05fr),
      gutter: 0.75cm,
      [
        #color-block(title: [UI responsibilities])[
          - collect a typed run request
          - build and interpret the plan
          - materialize the workspace deterministically
          - visualize stage flow and artifact mix with Plotly
          - expose raw contracts for inspection
        ]

        #warning-note[
          The app should not contain planning logic that cannot also run through the CLI.
        ]
      ],
      [
        #color-block(title: [Why this UI is intentionally simple])[
          - one control rail
          - one clean hero section
          - tabs for plan, interpretation, artifacts, and raw contracts
          - no page-router framework unless the app really needs it
          - the visuals should clarify the artifact contract, not distract from it
        ]
      ],
    )
  ]

  #slide(title: [Libraries and packages])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        #color-block(title: [Core Python layer])[
          - #link("https://docs.pydantic.dev/latest/")[Pydantic] and
            #link("https://docs.pydantic.dev/latest/concepts/pydantic_settings/")[pydantic-settings]
            for typed validation and settings
          - #link("https://typer.tiangolo.com/")[Typer] for CLI entrypoints
          - #link("https://rich.readthedocs.io/")[Rich] for structured console output
          - `pytest`, `ruff`, and `mypy` for TDD and hygiene
        ]

        #color-block(title: [Visualization and UI])[
          - #link("https://streamlit.io/")[Streamlit] for the operator and developer workbench
          - #link("https://plotly.com/python/")[Plotly] for deterministic interactive figures
          - Typst for report and slide deliverables
        ]
      ],
      [
        #color-block(title: [Why this split works])[
          - core packages stay lightweight and testable
          - geometry packages stay explicit about frames and metrics
          - heavy systems remain replaceable external adapters
        ]
      ],
    )
  ]

  #slide(title: [Libraries and packages: geometry and systems])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.65cm,
      [
        #color-block(title: [Geometry and evaluation])[
          - `numpy` and `opencv-python` for basic image and array handling
          - #link("https://dfki-ric.github.io/pytransform3d/")[pytransform3d] for frame and transform discipline
          - #link("https://www.open3d.org/")[Open3D] and
            #link("https://github.com/MichaelGrupp/evo")[evo] for geometry and trajectory evaluation
        ]
      ],
      [
        #color-block(title: [External systems])[
          - #link("https://github.com/zhangganlin/vista-slam")[ViSTA-SLAM]
          - #link("https://github.com/rmurai0610/MASt3R-SLAM")[MASt3R-SLAM]
          - #link("https://colmap.github.io/index.html")[COLMAP]
          - #link("https://docs.nerf.studio/")[Nerfstudio]
          - optional research utilities such as PyTorch3D
        ]
      ],
    )
  ]

  #slide(title: [Library decisions: what we are not doing])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.7cm,
      [
        #color-block(title: [Not core dependencies])[
          - Nerfstudio is a downstream reference-reconstruction path, not a core runtime dependency.
          - PyTorch3D stays optional unless we really need differentiable geometry in-repo.
          - External SLAM repos stay outside the base `uv` environment.
        ]
      ],
      [
        #color-block(title: [Not locking into one orchestrator yet])[
          - ZenML, Dagster, Prefect, or Beam may become useful adapters later.
          - For now, the repo-owned stage graph stays primary.
          - This preserves flexibility for both batch benchmarks and future streaming execution.
        ]
      ],
    )
  ]

  #slide(title: [Implementation roadmap from here])[
    #grid(
      columns: (1fr, 1fr),
      gutter: 0.7cm,
      [
        #color-block(title: [Already in place])[
          - typed batch contract
          - workspace materialization
          - CLI planning and materialization
          - Streamlit interpretation and artifact preview
        ]
      ],
      [
        #color-block(title: [Next steps])[
          - add `BaseSettings` tool-path settings
          - implement `method_prepare` preflight for ViSTA-SLAM and MASt3R-SLAM
          - keep wrapper execution thin
          - normalize real outputs before adding metric adapters
        ]
      ],
    )

    #v(0.45cm)
    #good-note[
      The easiest defensible path is still: *contract first, wrappers second, normalization third,
      evaluation fourth, streaming later*.
    ]
  ]
]
