"""Repo-wide behavior seams shared across package owners.

The :mod:`prml_vslam.protocols` package complements
:mod:`prml_vslam.interfaces`: interfaces define shared data meaning, while this
package defines shared behavioral boundaries such as packet streams and source
providers. Pipeline orchestration consumes these protocols, but ownership of
run planning and artifacts remains in :mod:`prml_vslam.pipeline`.
"""

from .rgbd import RgbdObservationSource
from .runtime import FramePacketStream

__all__ = ["FramePacketStream", "RgbdObservationSource"]
