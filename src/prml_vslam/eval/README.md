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

`prml_vslam.eval` does not own benchmark-policy composition. Policy now lives in
`prml_vslam.benchmark`, while evaluation execution remains here.
