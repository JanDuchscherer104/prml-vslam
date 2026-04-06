# Methods

`prml_vslam.methods` is intentionally a mock interface layer in this
repository.

We are not responsible for shipping real ViSTA-SLAM or MASt3R-SLAM execution
here. The package only owns the smallest local surface needed by the rest of
the codebase:

- typed method selection enums
- SLAM backend and session protocols in `methods/protocols.py`
- one typed mock SLAM backend config that builds the repository-local runtime
  via `setup_target()`
- deterministic offline and streaming mock runtimes that materialize
  pipeline-owned artifacts
- local path bookkeeping for mock installs

Use `BaseConfig` only for runtime setup/configuration objects. Prefer
pipeline-owned artifact contracts for normalized outputs instead of adding
parallel public method result shapes.

Do not add real upstream orchestration or repository-owned visualization logic
here unless a later task explicitly expands the scope.
