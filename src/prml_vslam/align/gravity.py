"""Gravity-aligned benchmark world detection."""

from __future__ import annotations

import numpy as np

_RDF_DOWN_AXIS = np.array([0.0, 1.0, 0.0], dtype=np.float64)


def is_gravity_aligned_target(target_frame: str) -> bool:
    """Whether the benchmark target frame is gravity-aligned (up == RDF -Y).

    ADVIO provider worlds derive from Apple Y-up, so RDF ``-Y`` is gravity. The
    TUM first-camera RDF frame is *not* gravity-aligned, so it keeps full Umeyama.
    """
    return target_frame.startswith("advio_") and target_frame.endswith("_world")
