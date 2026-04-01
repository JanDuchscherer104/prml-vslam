# App Requirements

This document defines the intended responsibilities and UI constraints for the
packaged Streamlit workbench in `prml_vslam.app`.

## Scope

- The app is the repository-owned interactive surface for inspection and
  visualization.
- The app should stay lightweight and orchestration-focused; heavy lifting
  belongs in dedicated `io`, `pipeline`, or method-specific modules.

## Rendering Requirements

- The app should prefer Streamlit-native rendering primitives when they are a
  clean fit for the content.
- Mathematical matrices should be rendered as LaTeX via Markdown instead of as
  plain JSON or plain-text arrays.
- Browser-owned interactive widgets may still manage their own DOM when that
  avoids unnecessary Streamlit reruns.

