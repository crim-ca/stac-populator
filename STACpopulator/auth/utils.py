import importlib
import inspect
import logging
import os
import re
from typing import Any, Callable, Dict, Optional, Type, Union

import requests
from requests import Response
from typing_extensions import Unpack

from STACpopulator.auth.typedefs import (
    AnyRequestMethod,
    AnyValueType,
    RequestOptions,
)

LOGGER = logging.getLogger(__name__)


RequestCachingKeywords = Dict[str, AnyValueType]
RequestCachingFunction = Callable[[AnyRequestMethod, str, RequestCachingKeywords], Response]


def make_request(
    method: AnyRequestMethod,
    url: str,
    ssl_verify: bool = True,
    **request_kwargs: Unpack[RequestOptions],
) -> Response:
    """Make an HTTP request with additional request options.

    Parameters
    ----------
    method: AnyRequestMethod
        The HTTP method to use (e.g., 'GET', 'POST').
    url: str
        The target URL for the request.
    ssl_verify: bool, optional
        Whether to verify SSL certificates (default is True). Overrides the `verify` parameter in `requests`.
    request_kwargs: dict, optional
        Additional keyword arguments to pass to the underlying request, such as headers, data, params, json, etc.

    Returns
    -------
    Response
        The response object returned by the request, typically containing status, headers, and content.
    """
    request_kwargs.setdefault("timeout", 5)
    request_kwargs.setdefault("verify", ssl_verify)
    # remove leftover options unknown to requests method in case of multiple entries
    known_req_opts = set(inspect.signature(requests.Session.request).parameters)
    known_req_opts -= {
        "url",
        "method",
    }  # add as unknown to always remove them since they are passed by arguments
    for req_opt in set(request_kwargs) - known_req_opts:
        request_kwargs.pop(req_opt)
    request_args = (method, url, request_kwargs)
    return _request_call(*request_args)


def _request_call(method: AnyRequestMethod, url: str, kwargs: RequestCachingKeywords) -> Response:
    """Request operation employed by :func:`request_extra` without caching."""
    with requests.Session() as session:
        res = session.request(method, url, **kwargs)
    return res


def fully_qualified_name(obj: Union[Any, Type[Any]]) -> str:
    """Get the full path definition of the object to allow finding and importing it.

    For classes, functions, and exceptions, the returned format is:

    .. code-block:: python
        module.name

    The ``module`` is omitted if it is a builtin object or type.

    For methods, the owning class is also included, resulting in:

    .. code-block:: python
        module.class.name
    """
    if inspect.ismethod(obj):
        return ".".join([obj.__module__, obj.__qualname__])
    cls = obj if inspect.isclass(obj) or inspect.isfunction(obj) else type(obj)
    if "builtins" in getattr(cls, "__module__", "builtins"):  # sometimes '_sitebuiltins'
        return cls.__name__
    return ".".join([cls.__module__, cls.__name__])


def import_target(target: str, default_root: Optional[str] = None) -> Optional[Any]:
    """Import a target resource class or function from a Python script as module or directly from a module reference.

    The Python script does not need to be defined within a module directory (i.e.: with ``__init__.py``).
    Files can be imported from virtually anywhere. To avoid name conflicts in generated module references,
    each imported target employs its full escaped file path as module name.

    The following target formats are supported:

    .. code-block:: text
        "path/to/script.py:function"
        "path/to/script.py:Class"
        "module.path.function"
        "module.path.Class"

    Parameters
    ----------
    target : str
        Resource to be imported, specified as a module path or file path with
        an optional attribute reference.
    default_root : str, optional
        Root directory to use when resolving relative file paths. Defaults to `None`.

    Returns
    -------
    Any or None
        The imported class or function if found; otherwise, `None`.
    """
    if ":" in target:
        mod_path, target = target.rsplit(":", 1)
        if not mod_path.startswith("/"):
            if default_root:
                mod_root = default_root
            else:
                mod_root = os.path.abspath(os.path.curdir)
            if not os.path.isdir(mod_root):
                LOGGER.warning("Cannot import relative target, root directory not found: [%s]", mod_root)
                return None
            mod_path = os.path.join(mod_root, mod_path)
        mod_path = os.path.abspath(mod_path)
        if not os.path.isfile(mod_path):
            LOGGER.warning("Cannot import target reference, file not found: [%s]", mod_path)
            return None
        mod_name = re.sub(r"\W", "_", mod_path)
        mod_spec = importlib.util.spec_from_file_location(mod_name, mod_path)
    else:
        mod_name = target
        mod_path, target = target.rsplit(".", 1)
        mod_spec = importlib.util.find_spec(mod_path)

    if not mod_spec:
        LOGGER.warning(
            "Cannot import target reference [%s], not found in file: [%s]",
            mod_name,
            mod_path,
        )
        return None

    mod = importlib.util.module_from_spec(mod_spec)
    mod_spec.loader.exec_module(mod)
    return getattr(mod, target, None)
