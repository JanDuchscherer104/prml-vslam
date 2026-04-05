# Work Packages

## Issues and TODOs

- [ ] Survey ARCore functionalities
- [ ] Read VSLAM papers
- [ ] Define initial benchmark scope and success criteria

## WP1: Repository and Environment Scaffolding

- Purpose: keep the repo installable, testable, and easy to onboard into.
- Inputs: challenge brief, package requirements, CI expectations.
- Outputs: `uv` environment, package skeleton, tests, CI, contributor guidance.
- Dependencies: none.
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
- Suggested issue split:
  - define capture format and file naming
  - implement or select the logging app path
  - validate export completeness and timestamp alignment

## WP3: Method Integration

- Purpose: integrate at least two external monocular VSLAM methods into a common benchmark workflow.
- Inputs: external method repos, input/output conventions, custom dataset recordings.
- Outputs: reproducible method wrappers, run configs, documented assumptions.
- Dependencies: WP1, WP2.
- Suggested issue split:
  - integrate candidate method A
  - integrate candidate method B
  - normalize outputs to shared trajectory and point-cloud formats

## WP4: Trajectory Evaluation

- Purpose: evaluate global and local camera trajectory quality.
- Inputs: method trajectories, ARCore baselines, ADVIO data, custom recordings.
- Outputs: trajectory metrics, comparison plots, evaluation scripts based on `evo`.
- Dependencies: WP2, WP3.
- Suggested issue split:
  - define metric suite and reference alignment policy
  - benchmark on ADVIO
  - benchmark on the custom dataset against ARCore

## WP5: Dense Reconstruction Evaluation

- Purpose: compare dense point-cloud quality across methods and against ARCore mapping.
- Inputs: dense outputs, ARCore maps, comparison tooling.
- Outputs: point-cloud quality metrics, qualitative views, reproducible comparison scripts.
- Dependencies: WP2, WP3.
- Suggested issue split:
  - define point-cloud alignment and filtering pipeline
  - quantitative comparison with Open3D or CloudCompare metrics
  - qualitative visualization and failure-case review

## WP6: Ground-Truth or Reference Reconstruction Pipeline

- Purpose: create high-quality reference reconstructions for custom recordings.
- Inputs: raw capture data, reconstruction tools such as COLMAP, Meshroom, or 3DGS.
- Outputs: reference point clouds or meshes used for comparison.
- Dependencies: WP2.
- Suggested issue split:
  - select the reconstruction toolchain
  - document calibration and export assumptions
  - generate reference artifacts for benchmark sequences

## WP7: Benchmarking and Reporting

- Purpose: consolidate benchmark runs, summarize findings, and keep reporting assets current.
- Inputs: trajectory metrics, dense-reconstruction comparisons, efficiency measurements, and reference artifacts.
- Outputs: benchmark tables and figures, update-meeting materials, and the final evaluation narrative.
- Dependencies: WP4, WP5, WP6.
- Suggested issue split:
  - define the final reporting slice and benchmark comparison matrix
  - keep work package status and update-meeting artifacts in sync
  - assemble the final report figures, tables, and recommendation
