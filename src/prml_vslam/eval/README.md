# Eval

This README explains the current implementation in `prml_vslam.eval`.

Use [REQUIREMENTS.md](./REQUIREMENTS.md) for the concise package contract. Use this file for the currently implemented local evaluation surface.

## Current Implementation

`prml_vslam.eval` is intentionally a thin interface layer in this repository. The current end-to-end flow is explicit `evo` APE trajectory evaluation over persisted run artifacts.

The package currently provides the smallest local implementation needed by the app and tests:

- discover locally available runs
- resolve reference and estimate trajectory paths
- run explicit `evo` APE trajectory evaluation
- persist and reload the resulting trajectory metrics
- define package-local typed protocols and payloads for trajectory, dense-cloud, and efficiency evaluation surfaces

## Current Boundaries

- The package does not own benchmark policy or a full metrics framework.
- Evaluation remains explicit; app surfaces should call it intentionally rather than triggering it as a selection side effect.
- Missing references, malformed trajectories, and unsupported cases should fail clearly.

Use `BaseConfig` only for actual evaluation controls and `BaseData` for persisted results, discovery payloads, and plotting contracts.
