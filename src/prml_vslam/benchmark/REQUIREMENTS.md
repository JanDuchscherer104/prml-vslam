# Benchmark Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.benchmark`.

## Responsibilities

- own policy-only benchmark config
- stay independent from runner orchestration details
- compose stage enablement without reimplementing evaluation logic

## Non-Negotiable Requirements

- the package stays thin
- actual metric execution stays in `prml_vslam.eval`
- the package must not grow app or viewer concerns
