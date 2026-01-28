import inspect
import logging
from typing import Any, Type, Union

import requests
from requests import Response

from STACpopulator.request.typedefs import RequestMethod

LOGGER = logging.getLogger(__name__)


def make_request(
    method: RequestMethod,
    url: str,
    ssl_verify: bool = True,
    **request_kwargs: Any,
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
    res = requests.request(method, url, **request_kwargs)
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
