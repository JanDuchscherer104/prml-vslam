# Methods Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.methods`.

## Current State

- the package owns method ids, backend config, output policy, runtime updates,
  mock execution, and the first external-wrapper scaffolding
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
- method code must not own benchmark policy or viewer orchestration
