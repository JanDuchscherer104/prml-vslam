"""Top-level package surface for the PRML VSLAM benchmark stack.

This package exposes the smallest repo-wide semantic DTOs that other packages
share directly, while the broader architecture fans out into
:mod:`prml_vslam.interfaces`, :mod:`prml_vslam.protocols`,
:mod:`prml_vslam.pipeline`, :mod:`prml_vslam.methods`, and
:mod:`prml_vslam.sources`. Use this module as the first click-through entry
point when orienting to the package: start with the shared DTOs here, then
follow the linked package owners to understand orchestration, backend wrappers,
and dataset normalization.
"""

from .interfaces import CameraIntrinsics, FrameTransform

__all__ = [
    "CameraIntrinsics",
    "FrameTransform",
    "__version__",
]

__version__ = "0.1.0"
