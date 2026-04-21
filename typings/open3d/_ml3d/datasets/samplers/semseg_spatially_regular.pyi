from __future__ import annotations
import numpy as np
import open3d._ml3d.utils.registry
import random as random
from tqdm.std import tqdm
__all__: list[str] = ['SAMPLER', 'SemSegSpatiallyRegularSampler', 'np', 'random', 'tqdm']
class SemSegSpatiallyRegularSampler:
    """
    Spatially regularSampler sampler for semantic segmentation datasets.
    """
    def __init__(self, dataset):
        ...
    def __len__(self):
        ...
    def get_cloud_sampler(self):
        ...
    def get_point_sampler(self):
        ...
    def initialize_with_dataloader(self, dataloader):
        ...
SAMPLER: open3d._ml3d.utils.registry.Registry
