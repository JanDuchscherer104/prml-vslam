# Methods

This package owns backend ids, backend-private config, output policy, runtime
update DTOs, and thin wrappers around external SLAM systems.

## Current Structure

- `contracts.py`
  - `MethodId`, `SlamBackendConfig`, `SlamOutputPolicy`
- `updates.py`
  - `SlamUpdate`
- `protocols.py`
  - `OfflineSlamBackend`, `StreamingSlamBackend`, `SlamSession`
- `mock_vslam.py`
  - repository-local mock backend used for `mstr` placeholder runs
- `vista/`
  - canonical ViSTA backend implementation (offline and streaming)

## Current Boundaries

- wrappers consume normalized repo-owned inputs and normalize outputs back into
  pipeline-owned `SlamArtifacts`
- benchmark policy does not live here
- viewer/export logic does not live here
- upstream-native artifacts may be preserved, but the canonical repo surface is
  still the normalized pipeline artifact contract
