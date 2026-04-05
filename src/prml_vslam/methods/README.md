# Methods

`prml_vslam.methods` is intentionally a mock interface layer in this
repository.

We are not responsible for shipping real ViSTA-SLAM or MASt3R-SLAM execution
here. The package only owns the smallest local surface needed by the rest of
the codebase:

- typed method selection enums
- config objects that still build runtimes via `setup_target()`
- deterministic mock runtimes that materialize placeholder pipeline artifacts
- local path bookkeeping for mock installs

Use `BaseConfig` only for runtime setup/configuration objects. Prefer
pipeline-owned artifact contracts for normalized outputs instead of adding
parallel public method result shapes.

Do not add real upstream orchestration or repository-owned visualization logic
here unless a later task explicitly expands the scope.
