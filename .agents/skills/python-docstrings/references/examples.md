# Examples

## Module Docstring

```python
"""Artifact import helpers for an external SLAM wrapper.

This module reads native backend outputs, validates the expected files, and
normalizes them into :class:`SlamArtifacts`. It owns end-of-run artifact
normalization only; live telemetry and viewer logging belong elsewhere.
"""
```

## Public Function Docstring

```python
def build_run_request(...) -> RunRequest:
    """Build one typed :class:`RunRequest` from a user-facing method selection.

    Normalizes the selected backend into a discriminated backend spec, attaches
    repo-owned runtime and placement defaults, and returns a request that can be
    handed directly to pipeline planning.

    Args:
        experiment_name:
            Human-readable run label used to derive the stable run id.
        method:
            Selected :class:`MethodId` used to choose the backend spec.

    Returns:
        Fully typed :class:`RunRequest` ready for
        :meth:`RunRequest.build`.

    Example:
        >>> request = build_run_request(
        ...     experiment_name="advio-15-offline-vista",
        ...     method=MethodId.VISTA,
        ...     source=DatasetSourceSpec(...),
        ... )
        >>> plan = request.build()
    """
```

## Public Class Docstring

```python
class BackendFactory:
    """Repository-local factory for backend descriptors and wrapper instances.

    Use this factory when pipeline code needs a truthful capability descriptor
    or an executable backend wrapper from a typed backend spec. Keep backend
    discovery and instantiation logic here rather than scattering method
    selection across orchestration code.
    """
```

## Config Or Datamodel Docstring

```python
class SlamOutputPolicy(BaseConfig):
    """Method-owned output materialization policy.

    These flags control which optional geometry surfaces a backend should
    persist. They do not change stage ordering, only the shape of the artifact
    bundle produced by the backend.
    """

    emit_dense_points: bool = True
    """Whether to materialize a dense point-cloud artifact."""

    emit_sparse_points: bool = True
    """Whether to materialize sparse geometry artifacts."""
```

## Streaming Or Session Docstring

```python
class SlamSession(Protocol):
    """Incremental SLAM session that consumes frames and buffers live updates.

    A session follows the lifecycle ``start_session() -> step(...) ->
    try_get_updates() -> close()``. Callers should treat the returned
    :class:`SlamUpdate` values as live telemetry and the final
    :class:`SlamArtifacts` bundle as the durable output boundary.
    """
```
