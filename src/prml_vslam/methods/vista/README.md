# ViSTA-SLAM Wrapper

This package contains the canonical ViSTA-SLAM backend integration used by the pipeline.

## Current Scope

- run ViSTA through the upstream `OnlineSLAM` runtime for both offline and streaming pipeline modes
- preserve native output directories and native `.rrd` files when present
- import native outputs back into normalized `SlamArtifacts`
