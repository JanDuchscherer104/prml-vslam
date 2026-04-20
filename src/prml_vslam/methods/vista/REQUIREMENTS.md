# ViSTA Wrapper Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.methods.vista`.

## Non-Negotiable Requirements

- consume canonical normalized manifests, not app-local inputs
- require canonical offline `rgb_dir` and normalized `timestamps_path` before ViSTA offline execution
- keep source-faithful ingest in pipeline code and ViSTA-specific workspace
  shaping inside this package
- keep exact upstream crop-and-resize preprocessing semantics inside this package instead of reimplementing them ad hoc
- preserve native outputs when useful, but normalize the repo contract back into
  `SlamArtifacts`
- fail clearly when the upstream repo or expected outputs are missing
