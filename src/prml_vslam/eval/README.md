# Eval

This package remains the thin explicit evaluation layer for persisted run
artifacts.

## Current Scope

- discover normalized run artifacts
- resolve reference and estimate trajectories
- run explicit `evo` trajectory evaluation, currently centered on translation APE
- compare metric-frame dense point clouds with Open3D nearest-neighbor distances
- persist and reload evaluation results
- provide repository-owned trajectory and dense-cloud stage execution seams used by the pipeline

Persisted trajectory results now carry explicit metric semantics such as metric
id, pose relation, alignment mode, and sync tolerance. The current evaluator
still computes translation APE only, but the contract now provides a typed
place to extend into drift-oriented RPE work without redesigning the payload
again.

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
  an `EvaluationArtifact` inside `StageResult`.
- Dense-cloud config: [`stage_cloud/config.py`](./stage_cloud/config.py)
  defines `CloudEvaluationStageConfig` for `evaluate.cloud`. The first
  executable path compares the reference reconstruction cloud against the
  Sim(3)-aligned SLAM cloud from trajectory evaluation using Open3D
  `compute_point_cloud_distance`, then persists Chamfer-style distance,
  directional distances, precision, recall, and F-score metrics.

Evaluation consumes prepared references and normalized method outputs. It does
not prepare sources, execute SLAM backends, own Rerun logging, or compute
summary projections.
