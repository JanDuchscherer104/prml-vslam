# Methods Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.methods`.

## Current State

- the package owns method ids, backend config, output policy, runtime updates,
  the mock placeholder backend, and the canonical ViSTA backend integration
- `SlamUpdate` is method-owned
- method protocols no longer depend on pipeline-owned config models

## Responsibilities

- define backend-private config and output policy
- define runtime session/update seams
- implement thin wrappers that consume normalized repo-owned inputs and produce
  normalized pipeline-owned artifacts

## Non-Negotiable Requirements

- missing repos, configs, checkpoints, or expected native outputs must fail
  clearly
- wrappers must stay thin and importer-oriented
- upstream-native outputs may be preserved, but normalized artifacts remain the
  repo contract
- method code must not own stage policy or viewer orchestration

### Mock Slam Backend
- The [Mock Slam Backend](mock_vslam.py) must forward the selected reference trajectory from the dataset (i.e. ARKit, ARCore, GT), as well as the point cloud or point map from the dataset (i.e. tango point clouds in case of advio dataset).
- It should allow to superimpose AWGN on the reference trajectory and point cloud with user-configurable parameters (e.g. mean, variance).
- It must implement the same interface as the ViSTA backend (i.e. full offline and streaming support).
- In streaming mode, the mock backend should keep the live `SlamUpdate.pointmap`
  surface camera-local and derive it from the step-wise reference geometry
  rather than exposing a separate world-space live cloud contract.
