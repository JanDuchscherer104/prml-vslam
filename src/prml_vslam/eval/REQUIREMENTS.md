# Evaluation Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.eval`.

## Current State

- The package owns metric computation, metric result DTOs, and metric artifact loading.
- `TrajectoryEvaluationService` computes metrics from prepared reference inputs
  and SLAM trajectories.
- `TrajectoryEvaluationRuntime` adapts metric computation to the bounded runtime API.
- `DenseCloudEvaluationService` computes Open3D nearest-neighbor metrics from
  reference and estimated PLY point clouds.
- `CloudEvaluationRuntime` adapts dense-cloud metric computation to the bounded
  runtime API.
- The evaluator persists explicit semantics: metric ID, pose relation, alignment
  mode, and sync tolerance.

## Responsibilities

- own metric computation for trajectory APE/RPE
- own dense-cloud metric artifacts (Chamfer-style distance, precision, recall, F-score)
- own typed estimated-vs-reference intrinsics comparison artifacts
- stay separate from pipeline stage policy and benchmark reference selection

## Non-Negotiable Requirements

- `TrajectoryEvaluationRuntime` must receive `PathConfig` explicitly instead of
  reconstructing it from the artifact root.
- evaluation must fail clearly if requested reference baselines are missing
- dense-cloud evaluation must fail clearly if requested point-cloud artifacts are
  missing, empty, non-finite, or not already in one metric comparison frame
- the package must not own benchmark reference identifiers or sequence preparation
- `summary` stage must not compute trajectory or cloud metrics; it is projection-only
- must implement [evo's Rerun integration](https://github.com/MichaelGrupp/evo/wiki/Rerun-integration)

## Validation

- translation APE matches expected residuals for known aligned sequences
- alignment modes include Sim(3) Umeyama and timestamp association
- terminal metrics are recorded in the `EvaluationArtifact`
- dense-cloud metrics match Open3D nearest-neighbor distances for simple known point sets
