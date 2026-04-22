from __future__ import annotations
from genericpath import exists
import json as json
import logging as logging
import numpy as np
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.utils.dataset_helper import make_dir
import open3d._ml3d.utils.registry
import os as os
from pathlib import Path
from posixpath import join
import typing

__all__: list[str] = [
    "BaseDataset",
    "DATASET",
    "Path",
    "ShapeNet",
    "ShapeNetSplit",
    "exists",
    "join",
    "json",
    "log",
    "logging",
    "make_dir",
    "np",
    "os",
]

class ShapeNet(open3d._ml3d.datasets.base_dataset.BaseDataset):
    """
    This class is used to create a dataset based on the ShapeNet dataset, and
        used in object detection, visualizer, training, or testing.

        The ShapeNet dataset includes a large set of 3D shapes.

    """

    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def get_label_to_names(task="classification"):
        """
        Returns a label to names dictionary object depending on the task. The
                valid values for task for classification and segmentation.

                Returns:
                    A dict where keys are label numbers and values are the corresponding
                    names.

        """
    def __init__(
        self,
        dataset_path,
        name="ShapeNet",
        class_weights=[2690, 76, 55, 1824, 3746, 69, 787, 392, 1546, 445, 202, 184, 275, 66, 152, 5266],
        ignored_label_inds=list(),
        test_result_folder="./test",
        task="classification",
        **kwargs,
    ):
        """
        Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    name: The name of the dataset (ShapeNet in this case).
                    class_weights: The class weights to use in the dataset.
                    ignored_label_inds: A list of labels that should be ignored in the dataset.
                    test_result_folder: The folder where the test results should be stored.
                    task: The task that identifies the purpose. The valid values are classification and segmentation.

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

class ShapeNetSplit:
    """
    The class gets data and attributes based on the split and
        classification.

    """
    def __init__(self, dataset, split="training", task="classification"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
