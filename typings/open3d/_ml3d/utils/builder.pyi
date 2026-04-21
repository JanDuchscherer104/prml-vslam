from __future__ import annotations
import open3d._ml3d.utils.registry
from open3d._ml3d.utils.registry import Registry
from open3d._ml3d.utils.registry import get_from_name
__all__: list[str] = ['DATASET', 'MODEL', 'PIPELINE', 'Registry', 'SAMPLER', 'build', 'build_network', 'convert_device_name', 'convert_framework_name', 'get_from_name', 'get_module']
def build(cfg, registry, args = None):
    ...
def build_network(cfg):
    ...
def convert_device_name(device_type, device_ids):
    """
    Convert device to either cpu or cuda.
    """
def convert_framework_name(framework):
    """
    Convert framework to either tf or torch.
    """
def get_module(module_type, module_name, framework = None, **kwargs):
    """
    Fetch modules (pipeline, model, or) from registry.
    """
DATASET: open3d._ml3d.utils.registry.Registry
MODEL: open3d._ml3d.utils.registry.Registry
PIPELINE: open3d._ml3d.utils.registry.Registry
SAMPLER: open3d._ml3d.utils.registry.Registry
