"""
Dataset augmentation classes with functions such as random rotation, translation, and scaling.
"""
from __future__ import annotations
from open3d._ml3d.datasets.augment.augmentation import ObjdetAugmentation
from open3d._ml3d.datasets.augment.augmentation import SemsegAugmentation
from . import augmentation
__all__: list[str] = ['ObjdetAugmentation', 'SemsegAugmentation', 'augmentation']
