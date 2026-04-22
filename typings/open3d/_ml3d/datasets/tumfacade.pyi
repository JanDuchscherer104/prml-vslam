from __future__ import annotations
import glob as glob
import logging as logging
import numpy as np
import open3d as o3d
import open3d._ml3d.datasets.base_dataset
from open3d._ml3d.datasets.base_dataset import BaseDataset
from open3d._ml3d.datasets.base_dataset import BaseDatasetSplit
import open3d._ml3d.utils.registry
from pathlib import Path
import typing

__all__: list[str] = [
    "BaseDataset",
    "BaseDatasetSplit",
    "DATASET",
    "Path",
    "TUMFacade",
    "TUMFacadeSplit",
    "glob",
    "log",
    "logging",
    "np",
    "o3d",
]

class TUMFacade(open3d._ml3d.datasets.base_dataset.BaseDataset):
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    @staticmethod
    def get_label_to_names():
        """
        Returns a label to names dictionary object.

                Returns:
                    A dict where keys are label numbers and values are the corresponding
                    names.

        """
    def __init__(
        self,
        dataset_path,
        info_path=None,
        name="TUM_Facade",
        cache_dir="./logs/cache",
        use_cache=False,
        use_global=False,
        **kwargs,
    ):
        """
        Dataset classes for the TUM-Facade dataset. Semantic segmentation
                annotations over TUM-MLS-2016 point cloud data.

                Website: https://mediatum.ub.tum.de/node?id=1636761
                Code: https://github.com/OloOcki/tum-facade
                Download:
                    - Original: https://dataserv.ub.tum.de/index.php/s/m1636761.003
                    - Processed: https://tumde-my.sharepoint.com/:f:/g/personal/olaf_wysocki_tum_de/EjA8B_KGDyFEulRzmq-CG1QBBL4dZ7z5PoHeI8zMD0JxIQ?e=9MrMcl
                Data License: CC BY-NC-SA 4.0
                Citation:
                    - Paper: Wysocki, O. and Hoegner, L. and Stilla, U., TUM-FAÇADE:
                      Reviewing and enriching point cloud benchmarks for façade
                      segmentation, ISPRS 2022
                    - Dataset: Wysocki, Olaf  and  Tan, Yue and  Zhang, Jiarui  and
                      Stilla, Uwe, TUM-FACADE dataset, TU Munich, 2023

                README file from processed dataset website:

                The dataset split is provided in the following folder structure

                    -->tum-facade
                        -->pointclouds
                            -->annotatedGlobalCRS
                                -->test_files
                                -->training_files
                                -->validation_files
                            -->annotatedLocalCRS
                                -->test_files
                                -->training_files
                                -->validation_file

                    The indivisual point clouds are compressed as .7z files and are
                    stored in the .pcd format.

                    To make use of the dataset split in open3D-ML, all the point cloud
                    files have to be unpacked with 7Zip. The folder structure itself
                    must not be modified, else the reading functionalities in open3D-ML
                    are not going to work. As a path to the dataset, the path to the
                    'tum-facade' folder must be set.

                    The dataset is split in the following way (10.08.2023):

                    Testing    :   Building Nr. 23
                    Training   :   Buildings Nr. 57, Nr.58, Nr. 60
                    Validation :   Buildings Nr. 22, Nr.59, Nr. 62, Nr. 81


                Initialize the function by passing the dataset and other details.

                Args:
                    dataset_path: The path to the dataset to use.
                    info_path: The path to the file that includes information about
                        the dataset. This is default to dataset path if nothing is
                        provided.
                    name: The name of the dataset (TUM_Facade in this case).
                    cache_dir: The directory where the cache is stored.
                    use_cache: Indicates if the dataset should be cached.
                    use_global: Inidcates if the dataset should be used in a local or
                        the global CRS

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
                    ValueError: Indicates that the split name passed is incorrect. The
                    split name should be one of 'training', 'test', 'validation', or
                    'all'.

        """
    def is_tested(self, attr): ...
    def save_test_result(self, results, attr): ...

class TUMFacadeSplit(open3d._ml3d.datasets.base_dataset.BaseDatasetSplit):
    __abstractmethods__: typing.ClassVar[frozenset]
    _abc_impl: typing.ClassVar[_abc._abc_data]
    def __init__(self, dataset, split="train"): ...
    def __len__(self): ...
    def get_attr(self, idx): ...
    def get_data(self, idx): ...

DATASET: open3d._ml3d.utils.registry.Registry
log: logging.Logger
