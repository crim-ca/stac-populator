import importlib
import os
import re
from collections.abc import Callable

from STACpopulator.exceptions import FunctionLoadError


def import_target(target_str: str) -> Callable:
    """Import a target resource class or function from a Python script or directly from a module reference.

    The Python script does not need to be defined within a module directory (i.e.: with ``__init__.py``).
    Files can be imported from virtually anywhere. To avoid name conflicts in generated module references,
    each imported target employs its full escaped file path as module name.

    If extra_kwargs are provided, they will be

    The following target formats are supported:

    .. code-block:: text
        "path/to/script.py:function"
        "path/to/script.py:Class"
        "module.path:function"
        "module.path:Class"
    """
    if ":" in target_str:
        mod, target = target_str.split(":", 1)
        if mod.endswith(".py"):
            mod_name = re.sub(r"\W", "_", os.path.splitext(mod)[0])
            mod_spec = importlib.util.spec_from_file_location(mod_name, mod)
            ns = importlib.util.module_from_spec(mod_spec)
            try:
                mod_spec.loader.exec_module(ns)
            except FileNotFoundError as e:
                raise FunctionLoadError(f"Unable to load python module from file: '{mod}'") from e
        else:
            try:
                ns = importlib.import_module(mod)
            except ModuleNotFoundError as e:
                raise FunctionLoadError(f"Unable to load module '{mod}'") from e
        try:
            return getattr(ns, target)
        except AttributeError as e:
            raise FunctionLoadError(f"Unable to load target '{target}' from '{mod}'") from e
    else:
        raise FunctionLoadError(
            "Target string is not properly formatted. Should be in the form 'module_or_path:function_or_class_name'"
        )
