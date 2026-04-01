# Python Standards

This file applies to work under `src/prml_vslam/`.

## Core Rules

- Use `pathlib.Path` for filesystem paths.
- Use `Console` from `prml_vslam.utils` for structured logging.
- Do not let failures go silent. Validate external-tool assumptions explicitly and raise clear
  errors when inputs, paths, or outputs are invalid.
- Prefer vectorized implementations when they improve clarity and performance. Use explicit loops when they are clearer or required by an external API.
- Add or update targeted pytest coverage for new behavior in `tests/`.
- Keep compatibility workarounds narrow and justified. Do not add broad defensive fallbacks for unsupported or undefined cases.

## Typing and Documentation

- Type all public signatures and prefer modern builtins such as `list[str]` and `dict[str, Any]`.
- Use `TYPE_CHECKING` guards for imports used only in annotations.
- Use `Literal` or `StrEnum` for constrained values instead of unchecked string literals.
- Prefer `match-case` over long multi-branch `if` chains when it improves clarity.
- Provide attribute docstrings for relevant fields in pydantic models or dataclasses instead of
  `Field(..., description=...)` for ordinary primitive fields.
- Use Google-style docstrings for public methods and functions.
- Document tensor and array shapes plus coordinate-frame assumptions whenever they are not obvious.
- Use jaxtyping annotations for arrays and tensors. Do not introduce bare `np.ndarray`,
  `numpy.ndarray`, or tensor annotations when a jaxtyping shape-and-dtype annotation is applicable.

### Example (Typing + Docstring)

```python
from torch import Tensor

def compute_rri(
    P_t: Float[Tensor, "N 3"],
    T_world_cam: Float[Tensor, "4 4"],
) -> tuple[Float[Tensor, "B num_classes H W"], Float[Tensor, "B"]]:
    """Compute Relative Reconstruction Improvement for candidate view.

    Args:
        P_t (Tensor["N 3", float32]): Current reconstruction point cloud (N points, XYZ; world frame).
        T_world_cam (Tensor["4 4", float32]): SE(3) transform: camera -> world.

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
- Prefer composable hierarchical config objects over untyped blobs.
- Use `field_validator` and `model_validator` when validation belongs in the config layer.
- Do not convert config objects to raw dicts just to instantiate internal runtime classes.

## VSLAM Contract Summary

- Treat external SLAM systems, ARCore, and reference reconstructions as separate systems with explicit boundaries. Normalize their outputs at the repo boundary before evaluation.
- Use explicit frame names in code and metadata. Do not rely on ambiguous names like `pose` or `transform` without frame direction.
- When transforms are stored explicitly, use `T_world_camera` naming for world <- camera transforms unless a subsystem documents a different convention at the boundary.
- Canonical metric units are meters for geometry and seconds for timestamps.
- Normalized trajectory artifacts should use TUM format plus a JSON sidecar when additional metadata is required, such as frame names, timestamp provenance, or alignment transforms.
- Normalized dense geometry artifacts should use PLY plus metadata when the file format alone cannot encode required benchmark information such as frame, units, color availability, or preprocessing.
- Keep evaluation and alignment logic separate from method-execution wrappers.

## Verification

- For Python changes, run `make lint`.
- Run targeted tests with `uv run pytest <path>` when a focused surface changed; use `make test`
  when the change is broad enough to justify the full suite.
- When changing config contracts, artifact formats, or benchmark assumptions, update
  `docs/agent_reference.md` in the same change.
