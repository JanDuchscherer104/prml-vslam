# Eval

`prml_vslam.eval` is intentionally a mock interface layer in this repository.

We are not responsible for owning real benchmark policy or a full trajectory
evaluation stack here. The package only provides the smallest local
implementation needed by the app and tests:

- discover locally available runs
- resolve reference and estimate paths
- compute a tiny deterministic trajectory-delta mock
- persist and reload that mock result

Use `BaseConfig` only for actual evaluation controls and `BaseData` for
persisted results, discovery payloads, and plotting contracts.

Do not grow this package into a full `evo` integration unless a later task
explicitly changes the project scope.
