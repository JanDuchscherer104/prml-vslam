from __future__ import annotations
from genericpath import exists
import glob as glob
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
from open3d._ml3d.datasets.utils.dataprocessing import DataProcessing as DP
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
import pandas as pd
from pathlib import Path
import pickle as pickle
from posixpath import abspath
from posixpath import dirname
from posixpath import join
from sklearn.neighbors._kd_tree import KDTree
import sys as sys
import typing

__all__: list[str] = [
    "BaseDataset",
    "BaseDatasetSplit",
    "DATASET",
    "DP",
    "KDTree",
    "Path",
    "Semantic3D",
    "Semantic3DSplit",
    "abspath",
    "dirname",
    "exists",
    "glob",
    "join",
    "log",
    "logging",
    "make_dir",
    "np",
    "os",
    "pd",
    "pickle",
    "sys",
]

class Semantic3D(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the Semantic3D dataset,
        and used in visualizer, training, or testing.

        The dataset includes 8 semantic classes and covers a variety of urban
        outdoor scenes.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.

                Returns:
                    A dict where keys are label numbers and
                    values are the corresponding names.

        """
    def __init__(
        self,
        dataset_path,
        name="Semantic3D",
        cache_dir="./logs/cache",
        use_cache=False,
        num_points=65536,
        class_weights=[5181602, 5012952, 6830086, 1311528, 10476365, 946982, 334860, 269353],
        ignored_label_inds=[0],
        val_files=["bildstein_station3_xyz_intensity_rgb", "sg27_station2_intensity_rgb"],
        test_result_folder="./test",
        **kwargs,
    ):
        """
        Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (Semantic3D in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    num_points: The maximum number of points to use when splitting the dataset.
                    class_weights: The class weights to use in the dataset.
                    ignored_label_inds: A list of labels that should be ignored in the dataset.
                    val_files: The files with the data.
                    test_result_folder: The folder where the test results should be stored.

                Returns:
                    class: The corresponding class.

        """
    def get_split(self, split): ...
    def get_split_list(self, split):
        """
        Returns the list of data splits available.

                Args:
                    split: A string identifying the dataset split that is usually one of
                    'training', 'test', 'validation', or 'all'.

                Returns:
                    A dataset split object providing the requested subset of the data.

                Raises:
                    ValueError: Indicates that the split name passed is incorrect. The split name should be one of
                    'training', 'test', 'validation', or 'all'.

        """
    def is_tested(self, attr):
        """
        Checks if a datum in the dataset has been tested.

                Args:
                    attr: The attribute that needs to be checked.

                Returns:
                    If the datum attribute is tested, then return the path where the
                        attribute is stored; else, returns false.

        """
    def save_test_result(self, results, attr):
        """
        Saves the output of a model.

                Args:
                    results: The output of a model for the datum associated with the attribute passed.
                    attr: The attributes that correspond to the outputs passed in results.

        """

class Semantic3DSplit(open3d._ml3d.datasets.base_dataset.BaseDatasetSplit):
    """
    This class is used to create a split for Semantic3D dataset.

        Initialize the class.

        Args:
            dataset: The dataset to split.
            split: A string identifying the dataset split that is usually one of
                'training', 'test', 'validation', or 'all'.
            **kwargs: The configuration of the model as keyword arguments.

        Returns:
            A dataset split object providing the requested subset of the data.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    def __init__(self, dataset, split="training"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
