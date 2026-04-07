# Work Packages

This note groups the project into planning slices for the team. It should be read together with the repository overview in [README.md](../README.md), the challenge clarifications in [Questions.md](Questions.md), the ownership model in [interfaces-and-contracts.md](architecture/interfaces-and-contracts.md), the pipeline architecture docs in [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md), and the active backlog in [.agents/issues.toml](../.agents/issues.toml) plus [.agents/todos.toml](../.agents/todos.toml).

The current codebase already has stable package boundaries:

- [`src/prml_vslam/io`](../src/prml_vslam/io/README.md) owns transport and replay adapters
- [`src/prml_vslam/datasets`](../src/prml_vslam/datasets/README.md) owns dataset normalization
- [`src/prml_vslam/pipeline`](../src/prml_vslam/pipeline/README.md) owns run planning and bounded runtime orchestration
- [`src/prml_vslam/methods`](../src/prml_vslam/methods/REQUIREMENTS.md) owns backend seams and future wrappers
- [`src/prml_vslam/eval`](../src/prml_vslam/eval/REQUIREMENTS.md) owns the thin evaluation surface
- [`src/prml_vslam/app`](../src/prml_vslam/app/REQUIREMENTS.md) owns the Streamlit workbench

The work packages below should therefore be read as execution groupings over those existing code owners, not as a replacement for the package architecture.

## WP1: Repository and Environment Scaffolding

- Purpose: keep the repo installable, testable, and easy to onboard into.
- Inputs: challenge brief, package requirements, CI expectations.
- Outputs: `uv` environment, package skeleton, tests, CI, contributor guidance.
- Dependencies: none.
- Current code anchors:
  - [README.md](../README.md)
  - [src/prml_vslam/utils/REQUIREMENTS.md](../src/prml_vslam/utils/REQUIREMENTS.md)
  - [src/prml_vslam/AGENTS.md](../src/prml_vslam/AGENTS.md)
- Suggested issue split:
  - maintain `pyproject.toml`
  - maintain system dependencies via conda or docker.
  - keep lint/test CI green
  - maintain README, AGENTS, and repo hygiene rules

## WP2: Data Capture and Logging App

- Purpose: record raw monocular video together with ARCore baseline logs for custom evaluation data.
- Inputs: smartphone capture requirements, ARCore logging needs, target export schema.
- Outputs: recording workflow or app, sample sessions, capture documentation.
- Dependencies: WP1.
- Current code anchors:
  - [src/prml_vslam/io/README.md](../src/prml_vslam/io/README.md)
  - [src/prml_vslam/io/RECORD3D_PROTOCOL.md](../src/prml_vslam/io/RECORD3D_PROTOCOL.md)
  - [src/prml_vslam/app/REQUIREMENTS.md](../src/prml_vslam/app/REQUIREMENTS.md)
- Suggested issue split:
  - define capture format and file naming
  - implement or select the logging app path
  - validate export completeness and timestamp alignment

## WP3: Method Integration

- Purpose: integrate at least two external monocular VSLAM methods into a common benchmark workflow.
- Inputs: external method repos, input/output conventions, custom dataset recordings.
- Outputs: reproducible method wrappers, run configs, documented assumptions.
- Dependencies: WP1, WP2.
- Current code anchors:
  - [src/prml_vslam/methods/REQUIREMENTS.md](../src/prml_vslam/methods/REQUIREMENTS.md)
  - [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md)
  - [src/prml_vslam/pipeline/contracts.py](../src/prml_vslam/pipeline/contracts.py)
- Suggested issue split:
  - integrate candidate method A
  - integrate candidate method B
  - normalize outputs to shared trajectory and point-cloud formats through `SequenceManifest` and `SlamArtifacts`

## WP4: Trajectory Evaluation

- Purpose: evaluate global and local camera trajectory quality.
- Inputs: method trajectories, ARCore baselines, ADVIO data, custom recordings.
- Outputs: trajectory metrics, comparison plots, evaluation scripts based on `evo`.
- Dependencies: WP2, WP3.
- Current code anchors:
  - [src/prml_vslam/eval/REQUIREMENTS.md](../src/prml_vslam/eval/REQUIREMENTS.md)
  - [src/prml_vslam/eval/README.md](../src/prml_vslam/eval/README.md)
  - [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md)
- Suggested issue split:
  - define metric suite and reference alignment policy
  - benchmark on ADVIO
  - benchmark on the custom dataset against ARCore

## WP5: Dense Reconstruction Evaluation

- Purpose: compare dense point-cloud quality across methods and against ARCore mapping.
- Inputs: dense outputs, ARCore maps, comparison tooling.
- Outputs: point-cloud quality metrics, qualitative views, reproducible comparison scripts.
- Dependencies: WP2, WP3.
- Current code anchors:
  - [src/prml_vslam/eval/REQUIREMENTS.md](../src/prml_vslam/eval/REQUIREMENTS.md)
  - [README.md](../README.md)
  - [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md)
- Suggested issue split:
  - define point-cloud alignment and filtering pipeline
  - quantitative comparison with Open3D or CloudCompare metrics
  - qualitative visualization and failure-case review

## WP6: Ground-Truth or Reference Reconstruction Pipeline

- Purpose: create high-quality reference reconstructions for custom recordings.
- Inputs: raw capture data, reconstruction tools such as COLMAP, Meshroom, or 3DGS.
- Outputs: reference point clouds or meshes used for comparison.
- Dependencies: WP2.
- Current code anchors:
  - [docs/Questions.md](Questions.md)
  - [README.md](../README.md)
  - [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md)
- Suggested issue split:
  - select the reconstruction toolchain
  - document calibration and export assumptions
  - generate reference artifacts for benchmark sequences

## WP7: Benchmarking and Reporting

- Purpose: consolidate benchmark runs, summarize findings, and keep reporting assets current.
- Inputs: trajectory metrics, dense-reconstruction comparisons, efficiency measurements, and reference artifacts.
- Outputs: benchmark tables and figures, update-meeting materials, and the final evaluation narrative.
- Dependencies: WP4, WP5, WP6.
- Current code anchors:
  - [docs/report/main.typ](report/main.typ)
  - [docs/slides/update-meetings/](slides/update-meetings/)
  - [src/prml_vslam/pipeline/README.md](../src/prml_vslam/pipeline/README.md)
  - [.agents/issues.toml](../.agents/issues.toml)
  - [.agents/todos.toml](../.agents/todos.toml)
- Suggested issue split:
  - define the final reporting slice and benchmark comparison matrix
  - keep work package status and update-meeting artifacts in sync
  - assemble the final report figures, tables, and recommendation

## Current Cross-Cutting Gaps

Across these work packages, the main remaining backend gap is not a lack of contracts. The repo already has typed planning, typed artifacts, and a bounded runtime slice. The main missing steps are:

- complete the real offline and streaming runner layer described in [src/prml_vslam/pipeline/REQUIREMENTS.md](../src/prml_vslam/pipeline/REQUIREMENTS.md)
- replace mock-only execution with thin real method wrappers under [src/prml_vslam/methods](../src/prml_vslam/methods/REQUIREMENTS.md)
- keep the app thin and orchestration-focused while the pipeline package owns actual backend semantics
- make the work-package plan and the `.agents` backlog move together instead of acting like separate project plans
