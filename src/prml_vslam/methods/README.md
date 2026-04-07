# Methods

This README explains the current implementation in `prml_vslam.methods`.

Use [REQUIREMENTS.md](./REQUIREMENTS.md) for the concise package contract. Use this file for the currently implemented local method surfaces.

## Current Implementation

`prml_vslam.methods` is intentionally a mock interface layer in this repository.

The package currently owns the smallest local surface needed by the rest of the codebase:

- typed method selection enums
- SLAM backend and session protocols in `methods/protocols.py`
- one typed mock SLAM backend config that builds the repository-local runtime via `setup_target()`
- deterministic offline and streaming mock runtimes that materialize pipeline-owned artifacts
- local path bookkeeping for mock installs

## Current Boundaries

- Real ViSTA-SLAM or MASt3R-SLAM orchestration is not implemented in the current codebase.
- Future real wrappers should stay thin, call upstream entry points, and normalize outputs into pipeline-owned artifacts rather than inventing parallel public result shapes.
- The package should not grow repository-owned visualization logic or benchmark policy unless a later task changes scope explicitly.

Use `BaseConfig` only for runtime setup and configuration objects.
