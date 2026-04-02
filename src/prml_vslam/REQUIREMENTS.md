# App Requirements

This document defines the intended responsibilities and UI constraints for the
packaged Streamlit workbench in `prml_vslam.app`.

## Scope

- The app is the repository-owned interactive surface for inspection and
  visualization.
- The app should stay lightweight and orchestration-focused; heavy lifting
  belongs in dedicated `io`, `pipeline`, or method-specific modules.
- Live Record3D capture is part of scope, but transport capture and frame
  decoding still belong to `prml_vslam.io`.

## Rendering Requirements

- The app should prefer Streamlit-native rendering primitives when they are a
  clean fit for the content.
- The Record3D page must use pure Streamlit only.
- The app must not embed raw HTML, CSS, or JavaScript custom components for the
  Record3D workflow.
- Mathematical matrices should be rendered as LaTeX via Markdown instead of as
  plain JSON or plain-text arrays.
