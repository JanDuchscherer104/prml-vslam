from __future__ import annotations
import open3d.cuda.pybind.core

__all__: list[str] = [
    "enable_persistent_jit_cache",
    "get_available_devices",
    "get_device_type",
    "is_available",
    "print_sycl_devices",
]

def enable_persistent_jit_cache() -> None:
    """
    Enables the JIT cache for SYCL. This sets an environment variable and will affect the entire process and any child processes.
    """

def get_available_devices() -> list[open3d.cuda.pybind.core.Device]:
    """
    Return a list of available SYCL devices.
    """

def get_device_type(device: open3d.cuda.pybind.core.Device) -> str:
    """
    Returns the device type (cpu / gpu / accelerator / custom) of the specified device as a string. Returns empty string if the device is not available.
    """

def is_available() -> bool:
    """
    Returns true if Open3D is compiled with SYCL support and at least one compatible SYCL device is detected.
    """

def print_sycl_devices(print_all: bool = False) -> None:
    """
    Print SYCL device available to Open3D (either the best available GPU, or a fallback CPU device).  If `print_all` is specified, also print SYCL devices of other types.
    """
