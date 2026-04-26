from __future__ import annotations
import addict.addict
from addict.addict import Dict
from collections import abc
from importlib import import_module
import os as os
from pathlib import Path
import shutil as shutil
import sys as sys
import tempfile as tempfile
import yaml as yaml

__all__: list[str] = [
    "Config",
    "ConfigDict",
    "Dict",
    "Path",
    "abc",
    "add_args",
    "import_module",
    "os",
    "shutil",
    "sys",
    "tempfile",
    "yaml",
]

class Config:
    @staticmethod
    def _merge_a_into_b(a, b): ...
    @staticmethod
    def load_from_file(filename): ...
    @staticmethod
    def merge_cfg_file(cfg, args, extra_dict):
        """
        Merge args and extra_dict from the input arguments.

                Merge the dict parsed by MultipleKVAction into this cfg.

        """
    @staticmethod
    def merge_module_cfg_file(args, extra_dict):
        """
        Merge args and extra_dict from the input arguments.

                Merge the dict parsed by MultipleKVAction into this cfg.

        """
    def __getattr__(self, name): ...
    def __getitem__(self, name): ...
    def __getstate__(self): ...
    def __init__(self, cfg_dict=None): ...
    def __setstate__(self, state): ...
    def convert_to_tf_names(self, name):
        """
        Convert keys compatible with tensorflow.
        """
    def dump(self, *args, **kwargs):
        """
        Dump to a string.
        """
    def merge_from_dict(self, new_dict):
        """
        Merge a new dict into cfg_dict.

                Args:
                    new_dict (dict): a dict of configs.

        """

class ConfigDict(addict.addict.Dict):
    def __getattr__(self, name): ...
    def __missing__(self, name): ...

def add_args(parser, cfg, prefix=""): ...
