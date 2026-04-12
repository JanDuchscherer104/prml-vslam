# Visualization

This package owns thin viewer/export policy plus the repo-owned Rerun
integration layer.

## Current Scope

- visualization policy through `VisualizationConfig`
- repo-owned normalized `.rrd` export helpers
- preserved native upstream `.rrd` handling

Rerun recordings are viewer artifacts. TUM trajectories, PLY clouds, manifests,
and stage summaries remain the scientific/provenance source of truth.
