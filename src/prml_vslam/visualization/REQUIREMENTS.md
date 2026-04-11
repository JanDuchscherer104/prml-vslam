# Visualization Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.visualization`.

## Responsibilities

- accept stable artifacts and runtime updates
- export normalized viewer recordings
- preserve upstream-native viewer artifacts when requested

## Non-Negotiable Requirements

- the package stays thinner than pipeline and benchmark
- it must not own Streamlit widgets, app state, or orchestration
- repo-owned normalized `.rrd` exports must be generated from repo-owned
  artifacts rather than by transcoding upstream-native viewer layouts
