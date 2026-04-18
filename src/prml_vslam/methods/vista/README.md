# ViSTA-SLAM Wrapper

This package contains the canonical ViSTA-SLAM backend integration used by the pipeline.

## Current Scope

- run ViSTA through the upstream `OnlineSLAM` runtime for both offline and streaming pipeline modes
- preserve native output directories and native `.rrd` files when present
- import native outputs back into normalized `SlamArtifacts`
- require `DBoW3Py` to be importable from the declared `vista` extra and load `vista_slam` from the checked-out upstream repo explicitly, without mutating global `sys.path`
