# Eval

This package remains the thin explicit evaluation layer for persisted run
artifacts.

## Current Scope

- discover normalized run artifacts
- resolve reference and estimate trajectories
- run explicit `evo` trajectory evaluation, currently centered on translation APE
- persist and reload evaluation results
- provide the repository-owned trajectory-evaluation stage execution seam used by the pipeline

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
- Diagnostic config: [`stage_cloud/config.py`](./stage_cloud/config.py) defines
  `CloudEvaluationStageConfig` for `evaluate.cloud`. It records planned dense
  cloud metrics and artifact selection, but no runtime is registered yet.

Evaluation consumes prepared references and normalized method outputs. It does
not prepare sources, execute SLAM backends, own Rerun logging, or compute
summary projections.

## Image Quality

[`image_metrics.py`](./image_metrics.py) is a standalone, IO-free module that
scores one `(reference, generated)` image pair: L1 (MAE), L2 (RMSE), MSE, PSNR,
and SSIM, on a `[0, 1]` normalized scale, with an optional boolean mask so
sparse renders are only scored on covered pixels. It assumes the two images are
already raster-aligned; it does not resample, warp, or render.

[`image_service.py`](./image_service.py) is the retrieval seam:
`ImageQualityEvaluationService` loads images, computes per-pair metrics, and
aggregates them into an `ImageQualitySummary` (per-metric `MetricStats`), which
it persists to and reloads from `<run_root>/evaluation/image_metrics.json` —
the same `evaluation/` layout as trajectory and cloud metrics. The CLI command
`prml-vslam eval-image <reference> <generated>` runs it over single files or
matched directories. Result DTOs (`ImageQualityMetricId`, `ImageQualityMetrics`,
`ImageQualitySummary`) live in [`contracts.py`](./contracts.py).

[`render_eval.py`](./render_eval.py) is the run-level engine that joins
rendering and metrics: given a run's dense cloud, estimated trajectory, source
intrinsics, and input frames, it renders one view per estimated pose (via
[`prml_vslam.rendering`](../rendering/README.md)), pairs each with the input
frame nearest in time, scores masked metrics, and persists
`image_metrics.json` plus an optional side-by-side gallery. It is the shared
core behind three surfaces:

- **CLI**: `prml-vslam render-run <artifact_root>` (post-hoc on a finished run);
  `prml-vslam eval-image` for an already-paired image set; `prml-vslam render-cloud`
  for low-level rendering only.
- **Pipeline stage**: [`stage_image/`](./stage_image/) defines `evaluate.image`,
  a full runtime stage that runs `render_eval` automatically per run when enabled
  in the TOML (`[stages.evaluate_image] enabled = true`).
- **App**: the Streamlit review page consumes the persisted JSON + gallery.

The renderer compares the *raw* cloud at *source* intrinsics — the fair,
reproducible cross-method comparison (ViSTA vs. MASt3R). Source↔model raster
reconciliation and cloud cleanup are explicit follow-ups, not silent behavior.
