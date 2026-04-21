"""Public IO surface for replay and live ingress helpers.

The :mod:`prml_vslam.io` package owns low-level transport and replay adapters
that emit normalized :class:`prml_vslam.interfaces.FramePacket` values. It does
not own pipeline semantics or dataset catalogs; it provides the ingress
building blocks that those higher-level packages consume.
"""

import sys

from prml_vslam import datasets as datasets

from .cv2_producer import (
    Cv2FrameProducer,
    Cv2ProducerConfig,
    Cv2ReplayMode,
)
from .record3d import Record3DStreamConfig

# TODO: what the fuck is this? Decide, should datasets become an actual submodule of io or stay a top level module?
sys.modules.setdefault(__name__ + ".datasets", datasets)

__all__ = [
    "Cv2FrameProducer",
    "Cv2ProducerConfig",
    "Cv2ReplayMode",
    "Record3DStreamConfig",
]
