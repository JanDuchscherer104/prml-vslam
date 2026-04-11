# Eval

This package remains the thin explicit evaluation layer for persisted run
artifacts.

## Current Scope

- discover normalized run artifacts
- resolve reference and estimate trajectories
- run explicit `evo` APE trajectory evaluation
- persist and reload evaluation results

## Boundary

`prml_vslam.eval` does not own benchmark-policy composition. Policy now lives in
`prml_vslam.benchmark`, while evaluation execution remains here.
