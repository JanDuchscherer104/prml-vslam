# Python Package Standards

This file applies to work under `src/prml_vslam/` and is package-level delta guidance on top of the root [../../AGENTS.md](../../AGENTS.md).

When work is specific to the Streamlit app subtree, also follow [`app/AGENTS.md`](./app/AGENTS.md).

## Local Sources Of Truth

- [REQUIREMENTS.md](./REQUIREMENTS.md) for top-level package ownership
- the nearest package `README.md` and `REQUIREMENTS.md` for package-local behavior and constraints
- [../../docs/architecture/interfaces-and-contracts.md](../../docs/architecture/interfaces-and-contracts.md) for human-facing minimal public surface, wrapper normalization, and migration rationale

## Core Engineering Rules

- Prefer existing external tools and libraries over local reimplementation when the repo already depends on them.
- Config classes should inherit from `prml_vslam.utils.BaseConfig` where appropriate.
- Runtime objects should be instantiated from config objects via `.setup_target()`, not from loose dicts or long argument lists.
- All signatures must be typed; prefer modern builtins such as `list[str]` and `dict[str, Any]`.
- Never use `object` in type annotations. Replace it with a concrete repo-owned protocol, discriminated union, typed payload model, or other explicit boundary type instead of treating `object` as a generic escape hatch.
- Use `TYPE_CHECKING` guards for imports that are only needed for annotations.
- Prefer normal repo-local imports over lazy `importlib` indirection or other runtime import tricks. Use `TYPE_CHECKING` to break annotation-only cycles, but do not hide local types from the language server or static tooling.
- Use `Literal` for constrained string values when it improves clarity.
- Use `pathlib.Path` for path handling.
- When a repo-owned `Path` must cross a CLI, config, or persisted text boundary, prefer `.to_posix()` unless the boundary explicitly requires native platform formatting.
- Prefer `match-case` over long `if` or `elif` chains when it fits the shape of the logic.
- Prefer `Enum` for categorical variables over ad hoc string literals when that keeps interfaces clearer.
- Prefer vectorized approaches over functional approaches, functional approaches over comprehensions, and comprehensions over manual loops when readability stays good.
- Document tensor shapes and coordinate frames in comments and use `jaxtyping` annotations where that improves clarity for tensor- or array-heavy code.
- Use `Console` from `prml_vslam.utils` for structured logging.
- Work test-driven for new Python behavior and add pytest coverage in `tests`.
- Never let anything fail silently.
- Do not write overly defensive workaround code for backwards compatibility or unlikely edge cases unless the task explicitly calls for it.
- Prefer direct API calls over reflective attribute probing such as `getattr(...)` or `hasattr(...)` when the attribute is known for the repo-targeted version.
- When integrating an external library, inspect the exact version used in this repo before adding compatibility workarounds; do not implement multi-version fallbacks unless the task explicitly requires them.
- Prefer inlining trivial one-off wrappers when the call site stays clear. If logic is genuinely reusable across leaf modules, move it to the shared owning module instead of leaving ad hoc helpers buried in leaf code.
- Keep one semantic concept under one canonical owner. During cleanup, delete duplicate DTOs, wrapper types, and shallow re-export surfaces instead of preserving parallel APIs for backwards compatibility unless transition support is explicitly required.
- Do not populate `__init__.py` files with imports that are not strictly necessary for the package's public API.
- Never disable the formatter with inline pragmas; restructure code to satisfy formatting constraints without turning formatting off for a file or block.

## Docstring Rules

- Treat docstrings as API contracts, not filler. Add them for modules, public classes, public functions, public methods, and typed fields that are part of a meaningful external or cross-module surface.
- Public modules should start with a module docstring that explains the module's purpose, its main contents, and what responsibilities belong there.
- Public functions and methods should use Google-style docstrings with a concise summary line followed by the sections that matter, usually `Args:`, `Returns:`, `Raises:`, `Yields:`, or `Attributes:`.
- Prefer short, information-dense docstrings over boilerplate. Do not restate the function name or paraphrase obvious type hints; explain behavior, invariants, side effects, and non-obvious semantics.
- When an API is non-trivial to call correctly, add a small usage example. Examples are especially encouraged for public entry points, config-driven workflows, and APIs with sequencing or frame-convention pitfalls.
- Cross-reference important internal types with `:class:` roles when helpful. Stable external keyword links are encouraged when they materially clarify an external API, algorithm, or concept.
- Provide attribute docstrings for relevant Pydantic fields, dataclass fields, and typed container fields instead of relying on `Field(..., description="...")` for ordinary primitive fields.
- Field and attribute docstrings should state units, shapes, coordinate frames, value ranges, and ownership semantics when those details are part of the contract.
- Class docstrings should explain the abstraction's role and when to use it, not just repeat the class name. Add theory or decision-making context only when it materially helps a caller understand the abstraction.

## Config And Contract Rules

- Keep setup, construction, and non-runtime validation in config objects.
- Prefer TOML as the persisted configuration surface for durable repo-owned workflows:
  - `BaseConfig.from_toml()` to load
  - `BaseConfig.to_toml()` and `save_toml()` to persist
  - `PathConfig.resolve_toml_path()` for repo-relative config paths
- Package-boundary DTOs, configs, manifests, requests, and results belong in `<package>/contracts.py` or
  `<package>/contracts/` when a package owns several distinct contract slices.
- Package-local `Protocol` definitions belong in `<package>/protocols.py` when a package owns that behavior seam.
- `services.py` modules own implementations only.
- Shared datamodel and protocol ownership should follow the canonical docs instead of being redefined locally:
  - shared datamodels in `prml_vslam.interfaces.*`
  - shared behavior seams in `prml_vslam.protocols.*`
- Streamlit-only state belongs in `prml_vslam.app.models`.
- Reuse canonical pipeline artifact contracts instead of creating app-local, dataset-local, or method-local copies of the same concept.
- Keep normalized pipeline boundaries authoritative:
  - `SequenceManifest` is the shared offline input boundary
  - pipeline-owned artifact bundles remain the normalized downstream outputs

## VSLAM-Specific Defaults

- Treat external SLAM systems, ARCore, and reference reconstructions as separate systems with explicit normalization boundaries.
- Use explicit frame names in code and metadata.
- Every interface, datamodel, artifact, and public method that carries poses, trajectories, point clouds, depth-derived geometry, calibration, or extrinsics must state its coordinate-frame semantics explicitly in names and docstrings.
- Use `T_target_source` naming for explicit transforms and transform-like variables. Prefer names such as `T_world_camera`, `T_cam_imu`, and `points_xyz_camera` over ambiguous names such as `pose`, `transform`, or `points`.
- The canonical repo pose convention for camera poses is world <- camera (`T_world_camera`). For pose datamodels, translation is the source-frame origin expressed in target coordinates, and rotation maps source-frame vectors into target coordinates.
- `FrameTransform`, `FramePacket.pose`, normalized trajectory artifacts, and downstream pipeline-owned pose outputs must use the canonical repo pose convention unless a boundary adapter explicitly documents an upstream-native exception.
- Use `FrameTransform` for both runtime camera poses and explicit frame-labelled static transforms such as calibration, frame-graph edges, or viewer export transforms.
- Camera-frame metric geometry must document its axis convention.
- World frames must be named explicitly at boundaries. Do not assume that upstream `world` frames from different systems are interchangeable.
- Cross-system alignment transforms are derived comparison artifacts, not raw source poses. Do not silently align or relabel upstream trajectories inside loaders or wrappers.
- `PoseTrajectory3D` from `evo.core.trajectory` is the canonical in-memory trajectory representation.
- If a file format cannot encode frame semantics, persist side metadata that records source frame, target frame, units, timestamp basis, and any applied alignment or normalization.
- Do not hide frame semantics in free-form `metadata` when the value crosses a package boundary; promote them into typed fields or typed artifact metadata.
- Normalized trajectory artifacts should use TUM format plus side metadata when extra provenance is required.
- Normalized dense geometry artifacts should use PLY plus metadata when the format alone cannot carry the required benchmark information.
- Keep evaluation and alignment logic separate from method-execution wrappers.

## External Wrapper Rules

- Treat upstream repos as explicit external systems with thin adapters.
- Use official upstream entry points where practical.
- Keep wrappers thin: prepare normalized inputs, invoke the upstream entry point, validate expected native outputs, and write normalized repo artifacts.
- Fail early when an external dependency is unavailable or misconfigured.
- Document unsupported cases explicitly.
- Do not hide fallback behavior inside wrappers.
- Do not adopt upstream live-camera modes as repository-wide streaming interfaces.
- If an upstream method needs image files instead of video, materialize that through pipeline workspace helpers rather than inventing a method-specific input contract.

## Verification

- After editing a file, run `ruff format` on touched Python files before finishing the task.
- Run `make lint` during iteration for Python changes.
- Run targeted tests with `uv run pytest <path>` when a focused surface changes.
- Use `make test` when the change is broad enough to justify the full suite.
- Before creating a commit, run `make ci`.
- When changing config contracts, artifact formats, or benchmark assumptions, update [`REQUIREMENTS.md`](./REQUIREMENTS.md) and/or [../../docs/architecture/interfaces-and-contracts.md](../../docs/architecture/interfaces-and-contracts.md) in the same change.
