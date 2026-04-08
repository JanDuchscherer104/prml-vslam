# Utils Requirements

This document defines the intended responsibilities and design constraints for
`prml_vslam.utils` during the early scaffold stage of the project.

## Scope

The `utils` package provides shared low-level infrastructure that is reused by
the CLI, Streamlit workbench, pipeline planner, and future runtime components.

It currently includes:

- `BaseConfig`: typed config model, TOML serialization, and config-as-factory helpers
- `PathConfig`: repository and workspace path resolution
- `Console`: structured logging helpers

The package must stay small, predictable, and free of hidden side effects.

## General Requirements

- Utilities must expose explicit, typed interfaces.
- Utilities must not silently change process-wide behavior.
- Utilities must remain reusable across CLI, tests, notebooks, and UI surfaces.
- Utilities must not encode feature-specific workflow logic that belongs in
  `pipeline`, `io`, or method-specific modules.

## BaseConfig Requirements

- `BaseConfig` must remain the common base class for typed config objects.
- Runtime object construction must follow the config-as-factory pattern via
  `target_type` and `setup_target()`.
- `BaseConfig` must not own repository-specific or workspace-specific path
  resolution policy.
- TOML serialization and deserialization must be deterministic.
- File-based TOML IO must use explicit path context rather than hidden global
  state.
- `BaseConfig` must support pure text and bytes TOML parsing without requiring a
  repository checkout.

## PathConfig Requirements

- `PathConfig` is the single owner of repo-owned path semantics.
- Relative repository paths must resolve against one explicit root.
- Path resolution rules must be deterministic and easy to test with `tmp_path`.
- `PathConfig` instances should be treated as immutable value objects after
  construction.
- Derived directories such as `artifacts_dir` and `captures_dir` must never
  drift out of sync with the configured root.
- Path helpers must not create directories unless the caller opts in via an
  explicit flag.
- `plan_run_paths()` must return the canonical artifact layout for one planned
  run and must not perform writes.
- Domain-specific path rules are allowed only when they are stable and shared,
  such as resolving bare capture filenames into `captures/`.

## Integration Requirements

- Services that depend on path semantics must accept an injected `PathConfig`.
- Long-lived module globals must not capture path configuration at import time.
- CLI commands should construct path-aware services per invocation unless there
  is a proven need for cached process-wide state.
- Tests should prefer explicit `PathConfig(root=tmp_path)` injection over
  monkeypatching global helpers.

## Console Requirements

- Logging helpers must provide structured, readable output for both humans and
  tests.
- Utilities must never fail silently; unexpected states should raise or log a
  clear error.

## Non-Goals

- `utils` is not a workspace manager.
- `utils` is not a persistence layer for experiment metadata beyond generic TOML
  helpers.
- `utils` should not introduce global registries or hidden caches unless there
  is a concrete performance need and the cache does not affect correctness.
