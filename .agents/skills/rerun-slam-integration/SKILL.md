---
name: rerun-slam-integration
description: Use when creating, reviewing, or fixing Python Rerun integrations for SLAM, RGB-D, reconstruction, and spatial-vision workflows, especially when work involves transforms and frame conventions, pinhole cameras, depth images, point clouds, timelines, blueprints, or comparing a local integration against official Rerun examples or the repo-local ViSTA-SLAM reference.
---

# Rerun SLAM Integration

Use this skill for Python-first Rerun work where spatial semantics matter more
than generic visualization advice.

Start from the official Rerun docs and official examples. Use the repo-local
ViSTA-SLAM files as a concrete integration case study, not as the universal
source of truth.

## Workflow

1. Start with the Context7 library ID `/rerun-io/rerun`.
2. Classify the task before loading more context:
   - API lookup or query planning: read `references/context7-queries.md`
   - entity layout, transforms, pinhole, depth, or logging best practices: read
     `references/python-sdk-patterns.md`
   - example selection: read `references/official-examples-map.md`
   - local ViSTA comparison: read `references/vista-slam-patterns.md`
3. Query the smallest relevant Rerun surface first.
4. Verify any non-trivial assumption against current official docs or an official
   example before recommending a pattern.
5. If the task is repo-local and symptoms look integration-specific, compare the
   local wrapper against the ViSTA reference after grounding in official Rerun
   patterns.
6. For repo-local regressions, inspect every touched `rr.` call site across the
   full logging path, not just the most obvious sink module.
7. Compare against both the upstream ViSTA reference and the last known good
   repo-local commit before recommending basis flips, root-world declarations,
   or other frame-normalization changes.
8. Keep coordinate normalization and method-specific basis handling at explicit
   method or stage boundaries; do not move viewer-only fixes into the
   coordinator hot path.
9. If a Context7 MCP server is available in the session, use the
   `/rerun-io/rerun` queries from the reference files. If no Context7 MCP is
   configured, open the direct example page link first and then follow its
   Python source link as needed.

## Reference Map

- `references/context7-queries.md`
  - Use for ready-to-run Context7 searches on Rerun APIs and examples.
- `references/python-sdk-patterns.md`
  - Use for the canonical Python SDK integration guidance in SLAM and RGB-D
    workflows.
- `references/official-examples-map.md`
  - Use when deciding which official example to open first.
- `references/vista-slam-patterns.md`
  - Use when comparing a local SLAM integration against the repo-local
    ViSTA-SLAM reference and the current PRML wrapper.

## Guardrails

- Prefer official docs and official examples over recollection.
- In this repo, treat Rerun as an observer sink or sidecar, not as a stage or
  coordinator-owned semantic boundary.
- Treat `Transform3D` relation semantics as a first-class design choice.
- Keep camera-local geometry and world-space geometry distinct.
- Do not call a pseudo-colored pointmap preview a depth image.
- Do not mix resized images with stale intrinsics or stale depth geometry.
- Use blueprints for viewer layout, not for scientific semantics.
