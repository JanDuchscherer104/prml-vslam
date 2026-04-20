"""Repo-wide semantic DTOs shared across package boundaries.

The :mod:`prml_vslam.interfaces` package owns the small set of normalized data
models whose semantics stay identical across datasets, pipeline orchestration,
method wrappers, and visualization. These models do not own execution flow or
behavior seams; those live in :mod:`prml_vslam.protocols` and
:mod:`prml_vslam.pipeline`.

Start here when you need the canonical meaning of camera intrinsics,
frame-labelled transforms, or runtime frame packets before following those
objects into :mod:`prml_vslam.datasets`, :mod:`prml_vslam.io`, or
:mod:`prml_vslam.methods`.
"""

from .camera import CameraIntrinsics
from .runtime import FramePacket, FramePacketProvenance, Record3DTransportId
from .transforms import FrameTransform

__all__ = [
    "CameraIntrinsics",
    "FrameTransform",
    "FramePacket",
    "FramePacketProvenance",
    "Record3DTransportId",
]
