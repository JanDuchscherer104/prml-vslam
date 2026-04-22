from __future__ import annotations
import ctypes
from open3d.cuda import pybind
from open3d.cuda.pybind import camera
from open3d.cuda.pybind import core
from open3d.cuda.pybind import data
from open3d.cuda.pybind import geometry
from open3d.cuda.pybind import io
from open3d.cuda.pybind import pipelines
from open3d.cuda.pybind import t
from open3d.cuda.pybind import utility
import platform as platform
import re as re
from . import _ml3d
from . import cuda
from . import ml
from . import visualization

__all__: list[str] = [
    "camera",
    "core",
    "cuda",
    "data",
    "geometry",
    "io",
    "ml",
    "open3d",
    "pipelines",
    "platform",
    "pybind",
    "re",
    "t",
    "utility",
    "visualization",
]

def _jupyter_labextension_paths():
    """
    Called by Jupyter Lab Server to detect if it is a valid labextension and
        to install the widget.

        Returns:
            src: Source directory name to copy files from. Webpack outputs generated
                files into this directory and Jupyter Lab copies from this directory
                during widget installation.
            dest: Destination directory name to install widget files to. Jupyter Lab
                copies from `src` directory into <jupyter path>/labextensions/<dest>
                directory during widget installation.

    """

def _jupyter_nbextension_paths():
    """
    Called by Jupyter Notebook Server to detect if it is a valid nbextension
        and to install the widget.

        Returns:
            section: The section of the Jupyter Notebook Server to change.
                Must be "notebook" for widget extensions.
            src: Source directory name to copy files from. Webpack outputs generated
                files into this directory and Jupyter Notebook copies from this
                directory during widget installation.
            dest: Destination directory name to install widget files to. Jupyter
                Notebook copies from `src` directory into
                <jupyter path>/nbextensions/<dest> directory during widget
                installation.
            require: Path to importable AMD Javascript module inside the
                <jupyter path>/nbextensions/<dest> directory.

    """

__DEVICE_API__: str = "cuda"
__version__: str = "0.19.0"
_build_config: dict = {
    "BUILD_TENSORFLOW_OPS": False,
    "BUILD_PYTORCH_OPS": True,
    "BUILD_CUDA_MODULE": True,
    "BUILD_SYCL_MODULE": False,
    "BUILD_AZURE_KINECT": True,
    "BUILD_LIBREALSENSE": True,
    "BUILD_SHARED_LIBS": False,
    "BUILD_GUI": True,
    "ENABLE_HEADLESS_RENDERING": False,
    "BUILD_JUPYTER_EXTENSION": True,
    "BUNDLE_OPEN3D_ML": True,
    "GLIBCXX_USE_CXX11_ABI": False,
    "CMAKE_BUILD_TYPE": "Release",
    "CUDA_VERSION": "12.1",
    "CUDA_GENCODES": "",
    "Tensorflow_VERSION": "",
    "Pytorch_VERSION": "2.2.2+cu121",
    "WITH_OPENMP": True,
}
_pybind_cuda: ctypes.CDLL
