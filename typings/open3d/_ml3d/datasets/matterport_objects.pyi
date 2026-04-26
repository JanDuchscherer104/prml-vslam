from __future__ import annotations
from glob import glob
import joblib as joblib
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.utils.bev_box import BEVBox3D
import open3d._ml3d.utils.registry
from pathlib import Path
from posixpath import join
import typing

__all__: list[str] = [
    "BEVBox3D",
    "BaseDataset",
    "DATASET",
    "MatterportObjects",
    "MatterportObjectsSplit",
    "Path",
    "glob",
    "joblib",
    "join",
    "log",
    "logging",
    "np",
]

class MatterportObjects(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the Matterport-Chair
        dataset and other related datasets.

        The Matterport-Chair dataset is introduced in Sparse PointPillars as a
        chair detection task for an embodied agent in various homes in Matterport3D
        (https://niessner.github.io/Matterport/). The training and test splits for
        Matterport-Chair are available on the Sparse PointPillars project webpage
        (https://vedder.io/sparse_point_pillars) and code to generate Matterport-Chair
        can be used to generate datasets of other objects in Matterport3D
        (https://github.com/kylevedder/MatterportDataSampling).

        Point clouds and bounding boxes are stored as numpy arrays serialized with
        joblib. All coordinates are in the standard robot coordinate frame
        (https://en.wikipedia.org/wiki/Right-hand_rule#Coordinates), with X forward,
        Y to the left, and Z up. All bounding boxes are assumed to only have a rotation
        along the Z axis in the form of yaw (positive yaw is counterclockwise).

        Like with KITTI, before you use Matterport-Chair you should run
        scripts/collect_bboxes.py to generate the bbox dictionary for data augmentation,
        but with '--dataset_type MatterportObjects' specified.

        If you use this in your research, we ask that you please cite Sparse PointPillars
        (https://github.com/kylevedder/SparsePointPillars#citation).

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictonary object.

                Returns:
                    A dict where keys are label numbers and values are the corresponding
                    names.

                    Names are extracted from Matterport3D's `metadata/category_mapping.tsv`'s
                    "ShapeNetCore55" column.

        """
    @staticmethod
    def read_label(path):
        """
        Reads labels of bound boxes.

                Returns:
                    The data objects with bound boxes information.

        """
    @staticmethod
    def read_lidar(path):
        """
        Reads lidar data from the path provided.

                Returns:
                    A data object with lidar information.

        """
    def __init__(
        self,
        dataset_path,
        name="MatterportObjects",
        cache_dir="./logs/cache",
        use_cache=False,
        val_split=5000,
        test_result_folder="./test",
        **kwargs,
    ):
        """
        Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (MatterportObjects in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    val_split: The split value to get a set of images for training,
                    validation, for testing.
                    test_result_folder: Path to store test output.

                Returns:
                    class: The corresponding class.

        """
    def get_split(self, split):
        """
        Returns a dataset split.

                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.

                Returns:
                    A dataset split object providing the requested subset of the data.

        """
    def get_split_list(self, split):
        """
        Returns the list of data splits available.

                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.

                Returns:
                    A dataset split object providing the requested subset of the data.

                Raises:
                    ValueError: Indicates that the split name passed is incorrect. The
                    split name should be one of 'training', 'test', 'validation', or
                    'all'.

        """
    def is_tested(self, attr):
        """
        Checks if a datum in the dataset has been tested.

                Args:
                    dataset: The current dataset to which the datum belongs to.
                    attr: The attribute that needs to be checked.

                Returns:
                    If the dataum attribute is tested, then resturn the path where the
                    attribute is stored; else, returns false.

        """
    def save_test_result(self, results, attrs):
        """
        Saves the output of a model.

                Args:
                    results: The output of a model for the datum associated with the
                    attribute passed.
                    attrs: The attributes that correspond to the outputs passed in
                    results.

        """

class MatterportObjectsSplit:
    def __init__(self, dataset, split="train"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
