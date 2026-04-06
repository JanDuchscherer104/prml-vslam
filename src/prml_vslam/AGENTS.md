# Python Standards

- ✓ Config classes inherit from our pydantic `BaseConfig`
- ✓ All functional classes (targets), services, and models are instantiated via `my_config.setup_target()`
- ✓ Provide docstrings for all relevant fields in pydantic classes or dataclasses, rather than using `Field(..., description="...")`. Do not use `Field(...)` for primitive fields unless necessary, for example when `default_factory` is required. Example:
    ```py
    class MyConfig(BaseConfig):
        my_bool: bool = True
        """Whether to enable the awesome feature."""
    ```
- ✓ Prefer vectorized approaches over functional approaches over comprehensions over loops.
- ✓ Use `pathlib.Path` for path handling.
- ✓ Work test-driven; every new feature must have corresponding tests in `tests` using `pytest`.
- ✓ Prefer `match-case` over `if-elif-else` for multi-branch logic when applicable.
- ✓ Prefer `Enum` for categorical variables over string literals.
- ✓ Document tensor shapes and coordinate frames in comments and use jaxtyping for tensor and array annotations.
- ✓ Use `Console` from `prml_vslam.utils` for structured logging.
- ✓ Identify present issues, overcomplications and redundancies and suggest elegant solutions to the user.
- *NEVER* let anything fail silently.
- *NEVER* write overly defensive workarounds to accommodate backwards compatibility or unlikely edge-cases.
- *Do NOT* populate `__init__.py` files with imports that are not strictly necessary for the package's public API.


When work is specific to the Streamlit app subtree, also follow `src/prml_vslam/app/AGENTS.md`.

## Core Rules

- **Typing**
  - All signatures must be typed; use modern builtins (`list[str]`, `dict[str, Any]`)
  - Use `TYPE_CHECKING` guards for imports of types only used in annotations
  - Use `Literal` for constrained string values

## Python Design Pattern

- Runtime objects should be constructed from config objects, not from loose dicts or long argument lists.
- Config classes should be composable and hierarchical if it improves clarity.
- Use our `BaseConfig` factory pattern consistently:
  - `class MyConfig(BaseConfig)`
  - `@property def target_type(self) -> type[MyRuntime] | None: ...`
  - Instantiate via `my_config.setup_target()`
  - The target's init method: `__init__(self, config: MyConfig)`
- If a runtime object needs external values at construction time, prefer `field_validator` over `model_validator`, and use `setup_target(...)` for late-bound runtime inputs.

### Factory Example

```python
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import Field
from torch import Tensor
from torch.optim import AdamW, Optimizer

from prml_vslam.utils import BaseConfig


class OptimizerConfig(BaseConfig):
    learning_rate: float = 5e-4
    """Learning rate for AdamW."""

    def setup_target(self, params: Iterable[Tensor] | list[dict[str, Any]]) -> AdamW:  # type: ignore[override]
        """Build the optimizer from model parameters."""
        return AdamW(params=params, lr=self.learning_rate)


class ModuleConfig(BaseConfig):
    """All setup, creation, and non-runtime validation lives in the config."""

    @property
    def target_type(self) -> type["MyModule"]:
        return MyModule

    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    """Nested optimizer configuration."""


class MyModule:
    """Runtime object."""

    def __init__(self, config: ModuleConfig) -> None:
        self.config = config
```

### Usage Pattern

```python
module = module_config.setup_target()
optimizer = module_config.optimizer.setup_target(model.parameters())
```

- **Anti-Patterns**
  - Do not convert configs to raw dicts just to instantiate internal classes.
  - Do not store untyped `dict[str, Any]` blobs where a dedicated `BaseConfig` subclass should exist.
  - Do not bypass nested config objects; if `self.config.optimizer` exists, it should construct the optimizer.

- **Example (Typing + Docstring)**: All public methods must have Google-style doc-strings and obey the following style:

```python
from torch import Tensor

def compute_rri(
    P_t: Float[Tensor, "N 3"],
) -> tuple[Float[Tensor, "B num_classes H W"], Float[Tensor, "B"]]:
    """Compute Relative Reconstruction Improvement for candidate view.

    Args:
        P_t (Tensor["N 3", float32]): Current reconstruction point cloud (N points, XYZ).

    Returns:
        Tuple[Tensor, Tensor] containing:
            - Tensor['B num_classes H W', float32]: Output tensor after processing.
            - Tensor['B', float32]: Auxiliary output tensor.
    """
    ...
```

## Config Pattern

- Config classes should inherit from `prml_vslam.utils.BaseConfig` where appropriate.
- Runtime objects should be instantiated from config objects via `.setup_target()`, not from loose dicts or long argument lists.
- Keep setup, construction, and non-runtime validation in config objects.
- Prefer TOML as the persisted configuration surface for `BaseConfig` derivatives that represent
  durable repo-owned workflows.
  - load configs with `BaseConfig.from_toml()`
  - persist configs with `BaseConfig.to_toml()` / `save_toml()`
  - resolve repo-owned config paths with `PathConfig.resolve_toml_path()`
- Prefer composable hierarchical config objects over untyped blobs.
- Use `field_validator` and `model_validator` when validation belongs in the config layer.
- Do not convert config objects to raw dicts just to instantiate internal runtime classes.

## Contract Ownership And Namespacing

- The full current-state findings, target ownership model, minimal public
  surface, and migration rules live in
  `docs/architecture/interfaces-and-contracts.md`.
- One semantic concept must have exactly one owning module in this repository.
- Repo-wide canonical datamodels live in `prml_vslam.interfaces.*`.
  - Use this namespace only for shared geometry, pose, trajectory, calibration, and live-frame datamodels that are imported across top-level packages.
- Repo-wide shared protocols live in `prml_vslam.protocols.*`.
  - `FramePacketStream` is owned by `prml_vslam.protocols.runtime`.
  - shared source-provider seams such as `OfflineSequenceSource` and `StreamingSequenceSource`
    are owned by `prml_vslam.protocols.source`.
- Package-boundary DTOs, enums, config objects, manifests, requests, and results belong in `<package>/contracts.py`.
- Package-local `Protocol` definitions belong in `<package>/protocols.py` when a package needs local behavior seams.
  - `prml_vslam.methods.protocols` owns SLAM behavior seams such as `SlamBackend` and `SlamSession`.
- Do not reintroduce mixed `interfaces.py` owner modules.
- Streamlit-only state belongs in `prml_vslam.app.models`.
  - App models must not leak into `pipeline`, `datasets`, `methods`, `eval`, or `io`.
- `services.py` owns implementations only.
  - Do not define new public contract types in service modules.
- Promote a type into `prml_vslam.interfaces` only when both of the following are true:
  - it is imported by multiple top-level packages
  - it has identical semantics across those packages
- Prefer reuse over parallel shapes.
  - Do not create method-local, app-local, or dataset-local copies of canonical pose, intrinsics, trajectory, frame, or pipeline artifact contracts.
- Keep normalized pipeline boundaries authoritative.
  - `SequenceManifest` is the shared offline input boundary.
  - `TrackingArtifacts` and other pipeline artifact bundles are the normalized outputs that downstream stages consume.
- Keep wrapper-private transport or upstream-native payloads private unless they are true shared repo contracts.

## VSLAM Contract Summary

- Treat external SLAM systems, ARCore, and reference reconstructions as separate systems with
  explicit boundaries. Normalize their outputs at the repo boundary before evaluation.
- Use explicit frame names in code and metadata. Do not rely on ambiguous names like `pose` or
  `transform` without frame direction.
- When transforms are stored explicitly, use `T_world_camera` naming for world <- camera
  transforms unless a subsystem documents a different convention at the boundary.
- Canonical metric units are meters for geometry and seconds for timestamps.
- Normalized trajectory artifacts should use TUM format plus a JSON sidecar when additional
  metadata is required, such as frame names, timestamp provenance, or alignment transforms.
- Normalized dense geometry artifacts should use PLY plus metadata when the file format alone
  cannot encode required benchmark information such as frame, units, color availability, or
  preprocessing.
- Keep evaluation and alignment logic separate from method-execution wrappers.

## External Method Wrapper Rules

- Treat upstream repos as explicit external systems with thin adapters.
- Use the upstream repo's official CLI or documented entrypoint when practical.
- ViSTA-SLAM integration should treat `run.py --images ... --config ... --output ...` as the primary offline seam and normalize native artifacts such as `trajectory.npy` and `pointcloud.ply` into repo-owned outputs.
- MASt3R-SLAM integration should treat `main.py --dataset ... --config ... [--calib ...] [--save-as ...]` as the primary offline seam and normalize its native trajectory text and reconstruction PLY into repo-owned outputs.
- Do not adopt upstream live-camera modes as repository-wide streaming interfaces.
  - Repo streaming remains owned by `FramePacket`, `FramePacketStream`, and pipeline session services.
- Keep method wrappers thin.
  - They should prepare normalized inputs, invoke the upstream entrypoint, validate expected native outputs, and write normalized repo artifacts.
- If an upstream method needs image files instead of video, materialize that through pipeline workspace helpers rather than inventing a method-specific input contract.

## Verification

- For Python changes, run `make lint` during iteration.
- Run targeted tests with `uv run pytest <path>` when a focused surface changed; use `make test`
  when the change is broad enough to justify the full suite.
- Before creating a commit, run `make ci`.
- When changing config contracts, artifact formats, or benchmark assumptions, update
  `.agents/references/agent_reference.md` in the same change.

## Local Responsibilities

- Only submodules with cross-module contracts, external integrations, or user-facing behavior
  should define a minimal and self-contained `REQUIREMENTS.md`.
- `app`
  - owns Streamlit pages, page state, UI composition, and app-facing services
  - does not own transport decoding, dataset parsing, method execution, or evaluation policy
- `io`
  - owns device and transport adapters, packet contracts, and transport-level normalization
  - does not own app state, benchmark policy, or dataset semantics
- `datasets`
  - owns dataset catalogs, download and extract flows, and normalization into repository contracts
  - does not own evaluation logic or method-specific behavior
- `pipeline`
  - owns run planning, artifact layout, manifests, and repository-level execution contracts
  - does not own backend-specific method logic or benchmark metric definitions
- `methods`
  - owns typed SLAM backend/session interfaces and repository-local mock setups needed by the app and tests
  - does not own real upstream orchestration, installation, or heavy visualization logic
- `eval`
  - owns only typed evaluation interfaces and repository-local mock metric flows needed by the app and tests
  - does not own benchmark policy, alignment research, or a full `evo` integration
- `utils`
  - owns shared generic primitives such as config helpers, geometry primitives, path handling, and logging
  - does not own domain policy for app, datasets, methods, eval, or pipeline
