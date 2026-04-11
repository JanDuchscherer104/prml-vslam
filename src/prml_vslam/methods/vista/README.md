# ViSTA-SLAM Wrapper

This package contains the offline-first ViSTA-SLAM wrapper scaffolding.

## Current Scope

- bridge canonical `SequenceManifest` inputs into ViSTA CLI arguments
- preserve native output directories and native `.rrd` files when present
- import native outputs back into normalized `SlamArtifacts`

Live ViSTA integration is intentionally out of scope for this series.
