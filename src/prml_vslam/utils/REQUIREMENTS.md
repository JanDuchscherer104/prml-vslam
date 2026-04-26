# Utils Requirements

## Purpose

This document is the concise source of truth for the shared utility package in `src/prml_vslam/utils/`.

## Current State

- `prml_vslam.utils` currently provides the shared low-level infrastructure used by the CLI, Streamlit workbench, pipeline planner, and runtime helpers.
- The package currently includes `BaseConfig`, `PathConfig`, and `Console` as the most important repo-owned shared surfaces.
- The package is already used as the common home for deterministic TOML IO, repo-owned path handling, and structured logging helpers.

## Target State

- Keep the package small, predictable, and free of hidden side effects.
- Keep repo-owned config, path, and logging helpers centralized here instead of reimplemented elsewhere.
- Keep the utilities reusable across CLI, tests, notebooks, and UI surfaces.

## Responsibilities

- The package owns shared low-level infrastructure such as config-as-factory helpers, TOML serialization, path-resolution helpers, logging utilities, and other stable generic runtime helpers.
- The package does not own package-specific workflow policy, benchmark logic, or orchestration semantics.

## Non-Negotiable Requirements

- Utility interfaces must remain explicit and typed.
- Utilities must not silently change process-wide behavior.
- `BaseConfig` must remain the common base for typed config objects and support deterministic TOML serialization and deserialization.
- Runtime object construction may follow the config-as-factory pattern through
  `target_type` and `setup_target()` for concrete domain, source, or backend
  variants that own their implementation target.
- Pipeline stage policy configs are declarative planning contracts. They must
  not use the utility config-as-factory pattern to construct stage runtimes,
  proxies, Ray actors, sink sidecars, or payload stores.
- `BaseConfig` must not own repository-specific path-resolution policy.
- `PathConfig` remains the single owner of repo-owned path semantics.
- Path resolution rules must remain deterministic and easy to test.
- Path helpers must not create directories unless the caller opts in explicitly.
- Services that depend on path semantics must accept an injected `PathConfig`.
- Logging helpers must remain structured and readable for both humans and tests.
- Utilities must never fail silently.

## Explicit Non-Goals

- `utils` is not a workspace manager.
- `utils` is not a persistence layer for experiment metadata beyond generic TOML helpers.
- `utils` should not introduce global registries or hidden caches unless there is a concrete performance need and correctness is unaffected.
- `utils` should not absorb feature-specific workflow logic that belongs in
  `pipeline`, `sources`, `methods`, `reconstruction`, or `eval`.

## Validation

- `BaseConfig`, `PathConfig`, and `Console` remain the primary shared surfaces.
- `FactoryConfig.setup_target()` remains available for concrete variant
  construction without becoming the stage runtime construction pattern.
- Path-aware code continues to accept injected `PathConfig` instances instead of capturing path globals at import time.
- The package stays small and generic instead of absorbing package-specific policy.
- The file stays aligned with the shared section structure used by the other existing `REQUIREMENTS.md` files.
