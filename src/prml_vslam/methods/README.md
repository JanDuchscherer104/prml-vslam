# Methods Guide

This package owns concrete SLAM wrapper execution: mock replay, ViSTA adapter
bootstrap, backend-native live updates, and normalized `SlamArtifacts`
production. Persisted backend selection and backend config muxing belong to
`prml_vslam.pipeline.stages.slam.config`.

## Current Implementation

The pipeline constructs stage-owned backend configs, then the SLAM stage runtime
calls the selected config's `setup_target(...)` inside the execution process.
The resulting method wrapper consumes normalized repository inputs and returns
normalized artifacts. There is no central method factory in this package.

The method package keeps these concerns local:

- `contracts.py`: backend-native `SlamUpdate` telemetry.
- `descriptors.py`: backend capability/resource DTOs consumed by stage configs.
- `protocols.py`: offline and streaming backend/session behavior seams.
- `options.py`: structural option protocols for wrapper implementations only.
- `mock_vslam.py`: repository-local mock backend.
- `vista/`: canonical ViSTA-SLAM wrapper, runtime bootstrap, preprocessing,
  session stepping, and native artifact import.

## Boundaries

Methods must not own stage order, persisted run config, resource placement,
pipeline events, app state, viewer orchestration, or evaluation policy. They may
resolve backend prerequisites, instantiate upstream runtimes, preserve selected
native outputs, emit backend-native live updates, and normalize outputs into the
shared artifact contracts consumed by the pipeline.

When adding a backend, add the persisted config variant and planning metadata in
`prml_vslam.pipeline.stages.slam.config`, then implement the wrapper here
against `protocols.py`. Keep heavy upstream imports and allocations in wrapper
construction or runtime startup, not in import-time package code.
