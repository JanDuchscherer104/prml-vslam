"""
Python binding of Open3D
"""
from __future__ import annotations
from . import camera
from . import core
from . import data
from . import geometry
from . import io
from . import ml
from . import pipelines
from . import t
from . import utility
from . import visualization
__all__: list[str] = ['camera', 'core', 'data', 'geometry', 'io', 'ml', 'pipelines', 't', 'utility', 'visualization']
_GLIBCXX_USE_CXX11_ABI: bool = False
