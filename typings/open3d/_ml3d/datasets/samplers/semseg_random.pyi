from __future__ import annotations
import numpy as np
import open3d._ml3d.utils.registry
import random as random

__all__: list[str] = ["SAMPLER", "SemSegRandomSampler", "np", "random"]

class SemSegRandomSampler:
    """
    Random sampler for semantic segmentation datasets.
    """
    @staticmethod
    def get_point_sampler(): ...
    def __init__(self, dataset): ...
    def __len__(self): ...
    def get_cloud_sampler(self): ...
    def initialize_with_dataloader(self, dataloader): ...

SAMPLER: open3d._ml3d.utils.registry.Registry
