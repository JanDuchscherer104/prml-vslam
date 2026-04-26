from __future__ import annotations
import inspect as inspect

__all__: list[str] = ["Registry", "get_from_name", "inspect"]

class Registry:
    def __init__(self, name): ...
    def _register_module(self, module_class, framework=None, module_name=None): ...
    def get(self, key, framework):
        """
        Get the registry record.

                Args:
                    key (str): The class name in string format.

                Returns:
                    class: The corresponding class.

        """
    def register_module(self, framework=None, name=None): ...
    @property
    def module_dict(self): ...
    @property
    def name(self): ...

def get_from_name(module_name, registry, framework):
    """
    Build a module from config dict.

        Args:
            module_name (string): Name of the module.
            registry: The registry to search the type from.
            framework (string): Framework, one of 'tf' or 'torch'

        Returns:
            object: The constructed object.

    """
