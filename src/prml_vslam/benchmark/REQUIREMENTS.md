# Benchmark Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.benchmark`.

## Responsibilities

- own reusable benchmark reference identifiers
- stay independent from runner orchestration and persisted stage policy
- provide stable identifiers consumed by datasets, methods, source preparation,
  and evaluation

## Non-Negotiable Requirements

- the package stays thin
- persisted stage enablement and baseline-selection config stays in
  `prml_vslam.pipeline.stages.*`
- actual metric execution stays in `prml_vslam.eval`
- the package must not grow app or viewer concerns
