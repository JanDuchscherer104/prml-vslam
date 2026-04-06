# Eval

`prml_vslam.eval` is intentionally a thin interface layer in this repository.

We are not responsible for owning real benchmark policy or a full trajectory
evaluation stack here. The package only provides the smallest local
implementation needed by the app and tests:

- discover locally available runs
- resolve reference and estimate paths
- run explicit `evo` APE trajectory evaluation
- persist and reload the resulting trajectory metrics
- define package-local evaluation protocols for trajectory, dense-cloud, and
  efficiency stages

Use `BaseConfig` only for actual evaluation controls and `BaseData` for
persisted results, discovery payloads, and plotting contracts.

Do not grow this package into benchmark-policy ownership or a full metrics
framework unless a later task explicitly changes project scope.
