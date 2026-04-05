# Methods

`prml_vslam.methods` is intentionally a mock interface layer in this
repository.

We are not responsible for shipping real ViSTA-SLAM or MASt3R-SLAM execution
here. The package only owns the smallest local surface needed by the rest of
the codebase:

- typed method selection enums and request/result contracts
- config objects that still build runtimes via `setup_target()`
- deterministic mock runtimes that materialize placeholder artifacts
- local path bookkeeping for mock installs

Use `BaseConfig` only for runtime setup/configuration objects and `BaseData`
for method requests, commands, artifact manifests, and run results.

Do not add real upstream orchestration or repository-owned visualization logic
here unless a later task explicitly expands the scope.
