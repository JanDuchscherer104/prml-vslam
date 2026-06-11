# Evaluation Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.eval`.

## Current State

- The package owns metric computation, metric result DTOs, and metric artifact persistence.
- `TrajectoryEvaluationService` computes metrics from prepared reference inputs
  and SLAM trajectories.
- `TrajectoryEvaluationRuntime` adapts metric computation to the bounded runtime API.
- The evaluator persists trajectory manifests, long-form metric rows, and
  error-series refs.
- `TrajectoryEvaluationQueryService` owns read-only app/post-run discovery and
  aggregation loading.

## Responsibilities

- own metric computation for trajectory APE/RPE
- own future dense-cloud metric artifacts (Chamfer, F-score)
- own typed estimated-vs-reference intrinsics comparison artifacts
- stay separate from pipeline stage policy and benchmark reference selection

## Non-Negotiable Requirements

- `TrajectoryEvaluationRuntime` must receive `PathConfig` explicitly instead of
  reconstructing it from the artifact root.
- evaluation must fail clearly if requested reference baselines are missing
- the package must not own benchmark reference identifiers or sequence preparation
- `summary` stage must not compute trajectory or cloud metrics; it is projection-only
- must implement [evo's Rerun integration](https://github.com/MichaelGrupp/evo/wiki/Rerun-integration)

## Validation

- translation APE matches expected residuals for known aligned sequences
- alignment modes include Sim(3) Umeyama and timestamp association
- terminal trajectory metrics are recorded in `TrajectoryEvaluationManifest`
  plus `metrics_long.csv`
