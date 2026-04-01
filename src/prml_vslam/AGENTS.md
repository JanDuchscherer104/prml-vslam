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

<<<<<<< HEAD
When work is specific to the Streamlit app subtree, also follow `src/prml_vslam/app/AGENTS.md`.

## Core Rules
=======
- **Typing**
  - All signatures must be typed; Use modern builtins (`list[str]`, `dict[str, Any]`)
  - Use `TYPE_CHECKING` guards for imports of types only used in annotations
  - Use `Literal` for constrained string values
>>>>>>> fb26801 (refactor: shrink metrics app PR scope)

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
<<<<<<< HEAD

## Config Pattern

- Config classes should inherit from `prml_vslam.utils.BaseConfig` where appropriate.
- Runtime objects should be instantiated from config objects via `.setup_target()`, not from loose dicts or long argument lists.
- Keep setup, construction, and non-runtime validation in config objects.
- Prefer composable hierarchical config objects over untyped blobs.
- Use `field_validator` and `model_validator` when validation belongs in the config layer.
- Do not convert config objects to raw dicts just to instantiate internal runtime classes.

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

## Verification

- For Python changes, run `make lint`.
- Run targeted tests with `uv run pytest <path>` when a focused surface changed; use `make test`
  when the change is broad enough to justify the full suite.
- When changing config contracts, artifact formats, or benchmark assumptions, update
  `docs/agent_reference.md` in the same change.
=======
>>>>>>> fb26801 (refactor: shrink metrics app PR scope)
