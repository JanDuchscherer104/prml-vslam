# Visualization Issue Notes

This file is intentionally short. The authoritative Rerun behavior lives in
[`REQUIREMENTS.md`](./REQUIREMENTS.md), [`README.md`](./README.md), and
[`RERUN_SEMANTICS.md`](./RERUN_SEMANTICS.md).

## Resolved Rerun Pointmap Regression

The repo-owned ViSTA viewer path now has regression coverage that compares a
minimal ViSTA-style recording with the repo-owned recording for the same
camera-local pointmap and pose payload. The current policy is:

- declare `world` with a neutral `Transform3D(axis_length=1.0)` and static
  `ViewCoordinates.RDF`;
- keep ViSTA world orientation unchanged instead of applying a viewer-only basis
  transform;
- log ViSTA live/model and keyed-history geometry under
  `world/slam/...`;
- keep camera-local pointmaps camera-local until Rerun composes them through the
  posed parent entity;
- render keyed-history points as the accumulated map and keep
  `live/model/points` as latest/debug geometry.

Historical debugging context can be recovered from the repo-local MemPalace with
queries around `rerun pointmap`, `ViewCoordinates RDF`, and `ViSTA-style
reference recording`.
