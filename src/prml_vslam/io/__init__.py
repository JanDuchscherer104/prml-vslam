"""Public IO surface for replay and live ingress helpers.

The :mod:`prml_vslam.io` package owns low-level transport and replay adapters
that emit normalized :class:`prml_vslam.interfaces.FramePacket` values. It does
not own pipeline semantics or dataset catalogs; it provides the ingress
building blocks that those higher-level packages consume.
"""

from .cv2_producer import (
    Cv2FrameProducer,
    Cv2ProducerConfig,
    Cv2ReplayMode,
)
from .record3d import Record3DStreamConfig

__all__ = [
    "Cv2FrameProducer",
    "Cv2ProducerConfig",
    "Cv2ReplayMode",
    "Record3DStreamConfig",
]
