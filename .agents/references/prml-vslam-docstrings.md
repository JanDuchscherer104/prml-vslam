# PRML VSLAM Docstring Addendum

Use `$python-docstrings` for the general workflow, section choice, and examples.
Apply the repo-specific rules below after the general skill.

Source of truth:

- [`src/prml_vslam/AGENTS.md`](../../src/prml_vslam/AGENTS.md)

## Checklist

- Document coordinate-frame semantics explicitly for any API that carries
  poses, transforms, trajectories, point clouds, depth-derived geometry,
  intrinsics, calibration, or extrinsics.
- Prefer explicit `T_target_source` naming in prose and examples.
- State tensor and image shapes when they are part of the API contract.
- State units, value ranges, ownership semantics, and persistence boundaries
  for artifacts, manifests, configs, and typed payloads when those details
  matter to callers.
- For wrappers around external systems, say what is normalized by the repo and
  what remains upstream-native.
- For config models, explain what each meaningful field changes and when it
  matters during setup or construction.
- For streaming and session APIs, document sequencing and lifecycle, not just
  the individual calls in isolation.
- Prefer Sphinx cross-references for internal symbols and markdown links for
  external docs or papers.
- Avoid `Raises:` unless the caller genuinely needs to rely on that failure
  contract.
