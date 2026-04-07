# Python Package Standards

This file applies to work under `src/prml_vslam/` and is package-level delta guidance on top of the root [../../AGENTS.md](../../AGENTS.md).

When work is specific to the Streamlit app subtree, also follow [`app/AGENTS.md`](./app/AGENTS.md).

## Local Sources Of Truth

- [REQUIREMENTS.md](./REQUIREMENTS.md) for top-level package ownership
- the nearest package `README.md` and `REQUIREMENTS.md` for package-local behavior and constraints
- [../../docs/architecture/interfaces-and-contracts.md](../../docs/architecture/interfaces-and-contracts.md) for human-facing ownership rationale

## Core Engineering Rules

- Config classes should inherit from `prml_vslam.utils.BaseConfig` where appropriate.
- Runtime objects should be instantiated from config objects via `.setup_target()`, not from loose dicts or long argument lists.
- All signatures must be typed; prefer modern builtins such as `list[str]` and `dict[str, Any]`.
- Public methods should use Google-style docstrings when they are part of a meaningful external or cross-module surface.
- Use `TYPE_CHECKING` guards for imports that are only needed for annotations.
- Use `Literal` for constrained string values when it improves clarity.
- Provide docstrings for relevant Pydantic fields or dataclass fields instead of relying on `Field(..., description="...")` for ordinary primitive fields.
- Use `pathlib.Path` for path handling.
- Prefer `match-case` over long `if` or `elif` chains when it fits the shape of the logic.
- Prefer `Enum` for categorical variables over ad hoc string literals when that keeps interfaces clearer.
- Prefer vectorized approaches over functional approaches, functional approaches over comprehensions, and comprehensions over manual loops when readability stays good.
- Document tensor shapes and coordinate frames in comments and use `jaxtyping` annotations where that improves clarity for tensor- or array-heavy code.
- Use `Console` from `prml_vslam.utils` for structured logging.
- Work test-driven for new Python behavior and add pytest coverage in `tests`.
- Never let anything fail silently.
- Do not write overly defensive workaround code for backwards compatibility or unlikely edge cases unless the task explicitly calls for it.
- Do not populate `__init__.py` files with imports that are not strictly necessary for the package's public API.

## Config And Contract Rules

- Keep setup, construction, and non-runtime validation in config objects.
- Prefer TOML as the persisted configuration surface for durable repo-owned workflows:
  - `BaseConfig.from_toml()` to load
  - `BaseConfig.to_toml()` and `save_toml()` to persist
  - `PathConfig.resolve_toml_path()` for repo-relative config paths
- Package-boundary DTOs, configs, manifests, requests, and results belong in `<package>/contracts.py`.
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
- Canonical metric units are meters for geometry and seconds for timestamps.
- Normalized trajectory artifacts should use TUM format plus side metadata when extra provenance is required.
- Normalized dense geometry artifacts should use PLY plus metadata when the format alone cannot carry the required benchmark information.
- Keep evaluation and alignment logic separate from method-execution wrappers.

## External Wrapper Rules

- Treat upstream repos as explicit external systems with thin adapters.
- Use official upstream entry points where practical.
- Keep wrappers thin: prepare normalized inputs, invoke the upstream entry point, validate expected native outputs, and write normalized repo artifacts.
- Do not adopt upstream live-camera modes as repository-wide streaming interfaces.
- If an upstream method needs image files instead of video, materialize that through pipeline workspace helpers rather than inventing a method-specific input contract.

## Verification

- Run `make lint` during iteration for Python changes.
- Run targeted tests with `uv run pytest <path>` when a focused surface changes.
- Use `make test` when the change is broad enough to justify the full suite.
- Before creating a commit, run `make ci`.
- When changing config contracts, artifact formats, or benchmark assumptions, update `.agents/references/agent_reference.md` in the same change.
