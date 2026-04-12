# Eval Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.eval`.

## Current State

- the package is still a thin explicit evaluation surface around persisted
  artifacts and `evo`
- benchmark-policy composition is no longer a pipeline-core concern, but it
  still does not belong here

## Responsibilities

- discover normalized artifacts
- execute explicit evaluation
- persist and reload deterministic evaluation results

## Non-Negotiable Requirements

- evaluation remains explicit and separate from orchestration
- trajectory metrics remain a thin `evo` adapter
- the package does not own source normalization, method execution, or policy
  composition
