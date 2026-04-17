"""Typed backend factory for pipeline-owned orchestration."""

from __future__ import annotations

from typing import Protocol

from prml_vslam.methods import MockSlamBackendConfig, VistaSlamBackendConfig
from prml_vslam.methods.contracts import MethodId
from prml_vslam.methods.descriptors import BackendCapabilities, BackendDescriptor
from prml_vslam.utils import PathConfig


class BackendFactoryProtocol(Protocol):
    """Factory surface consumed by the pipeline."""

    def describe(self, backend_spec: object) -> BackendDescriptor:
        """Return the descriptor for one backend spec."""

    def build(self, backend_spec: object, *, path_config: PathConfig | None = None) -> object:
        """Instantiate one executable backend from its typed spec."""


class BackendFactory(BackendFactoryProtocol):
    """Repository-local backend factory."""

    def describe(self, backend_spec: object) -> BackendDescriptor:
        kind = backend_spec.kind
        match kind:
            case MethodId.MOCK.value:
                return BackendDescriptor(
                    key=kind,
                    display_name=MethodId.MOCK.display_name,
                    capabilities=BackendCapabilities(
                        offline=True,
                        streaming=True,
                        dense_points=True,
                        live_preview=True,
                        native_visualization=False,
                        trajectory_benchmark_support=True,
                    ),
                    default_resources={"CPU": 1.0},
                )
            case MethodId.VISTA.value:
                return BackendDescriptor(
                    key=kind,
                    display_name=MethodId.VISTA.display_name,
                    capabilities=BackendCapabilities(
                        offline=True,
                        streaming=True,
                        dense_points=True,
                        live_preview=True,
                        native_visualization=True,
                        trajectory_benchmark_support=True,
                    ),
                    default_resources={"CPU": 2.0, "GPU": 1.0},
                    notes=["GPU acceleration is recommended for real ViSTA runs."],
                )
            case MethodId.MAST3R.value:
                return BackendDescriptor(
                    key=kind,
                    display_name=MethodId.MAST3R.display_name,
                    capabilities=BackendCapabilities(
                        offline=False,
                        streaming=False,
                        dense_points=False,
                        live_preview=False,
                        native_visualization=False,
                        trajectory_benchmark_support=False,
                    ),
                    default_resources={},
                    notes=["MASt3R remains a placeholder backend in this repository."],
                )
            case _:
                raise RuntimeError(f"Unsupported backend kind: {kind}")

    def build(self, backend_spec: object, *, path_config: PathConfig | None = None) -> object:
        kind = backend_spec.kind
        match kind:
            case MethodId.MOCK.value:
                backend = MockSlamBackendConfig(method_id=MethodId.MOCK).setup_target()
            case MethodId.VISTA.value:
                backend = VistaSlamBackendConfig.model_validate(_backend_config_payload(backend_spec)).setup_target(
                    path_config=path_config
                )
            case MethodId.MAST3R.value:
                raise RuntimeError("MASt3R-SLAM is not executable in this repository yet.")
            case _:
                raise RuntimeError(f"Unsupported backend kind: {kind}")
        if backend is None:
            raise RuntimeError(f"Failed to build backend '{kind}'.")
        return backend


def _backend_config_payload(backend_spec: object) -> dict[str, object]:
    payload = backend_spec.model_dump(mode="python")
    payload.pop("kind")
    return payload


__all__ = ["BackendFactory", "BackendFactoryProtocol"]
