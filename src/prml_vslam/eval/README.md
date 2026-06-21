# Eval

This package remains the thin explicit evaluation layer for persisted run
artifacts.

## Current Scope

- resolve reference and estimate trajectories
- run explicit `evo` trajectory evaluation for translation/rotation APE and RPE
- persist trajectory evaluation manifests, long-form metric rows, and error-series refs
- provide the repository-owned trajectory-evaluation stage execution seam used by the pipeline

Persisted trajectory results now carry reference and candidate trajectory
provenance, long-form statistic rows with evo pose relations, and error-series
references. Error-series artifacts store APE geometry for trajectory overlays
and scalar RPE values without implying unavailable evo pair geometry.

## Boundary

`prml_vslam.eval` does not own persisted stage policy. Trajectory-evaluation
selection lives in `prml_vslam.eval.stage_trajectory`, reusable
reference identifiers live in `prml_vslam.sources.contracts`, and evaluation execution
remains here.

## Stage Integration

- Config: [`stage_trajectory/config.py`](./stage_trajectory/config.py) defines
  `TrajectoryEvaluationStageConfig` for `evaluate.trajectory`. It declares the
  trajectory metrics artifact, verifies backend support, selects the reference
  source, and stores evaluation policy.
- Input DTO: [`stage_trajectory/contracts.py`](./stage_trajectory/contracts.py)
  defines `TrajectoryEvaluationStageInput` with the artifact root, selected
  baseline, source manifest, prepared benchmark inputs, and normalized
  `SlamArtifacts`.
- Runtime spec: [`stage_trajectory/spec.py`](./stage_trajectory/spec.py) owns
  runtime construction, input building from completed source/SLAM results, and
  failure fingerprints.
- Runtime: [`stage_trajectory/runtime.py`](./stage_trajectory/runtime.py)
  adapts `TrajectoryEvaluationService` into `OfflineStageRuntime` and returns
  a `TrajectoryEvaluationManifest` inside `StageResult`.
- Diagnostic config: [`stage_cloud/config.py`](./stage_cloud/config.py) defines
  `CloudEvaluationStageConfig` for `evaluate.cloud`. It records planned dense
  cloud metrics and artifact selection, but no runtime is registered yet.

Evaluation consumes prepared references and normalized method outputs. It does
not discover app selections, prepare sources, execute SLAM backends, own Rerun
logging, or compute summary projections. App and post-run aggregation discovery
lives in [`query.py`](./query.py) and is read-only.
