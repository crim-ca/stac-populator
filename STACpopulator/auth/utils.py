import inspect
import logging
from types import MappingProxyType
from typing import Any, Callable, Dict, List, Optional, Type, Union

import requests
from requests import Response
from requests.structures import CaseInsensitiveDict
from typing_extensions import Unpack

from STACpopulator.auth.typedefs import (
    AnyHeadersContainer,
    AnyRequestMethod,
    AnyValueType,
    RequestOptions,
)

LOGGER = logging.getLogger(__name__)


RequestCachingKeywords = Dict[str, AnyValueType]
RequestCachingFunction = Callable[[AnyRequestMethod, str, RequestCachingKeywords], Response]


def _request_call(method: AnyRequestMethod, url: str, kwargs: RequestCachingKeywords) -> Response:
    """Request operation employed by :func:`request_extra` without caching."""
    with requests.Session() as request_session:
        resp = request_session.request(method, url, **kwargs)
    return resp


def request_extra(
    method: AnyRequestMethod, url: str, ssl_verify: bool = True, **request_kwargs: Unpack[RequestOptions]
) -> Response:
    """
    Make an HTTP request with additional request options.

    :param method: HTTP method to use (e.g., 'GET', 'POST'). Type should be compatible with `AnyRequestMethod`.
    :param url: Target URL for the request.
    :param ssl_verify: Whether to verify SSL certificates (default: True). Overrides `verify` in `requests`.
    :param request_kwargs: Additional keyword arguments to pass to the underlying request,
                           e.g., headers, data, params, json, etc.
    :return: The response from `_request_call`.
    """
    request_kwargs.setdefault("timeout", 5)
    request_kwargs.setdefault("verify", ssl_verify)
    # remove leftover options unknown to requests method in case of multiple entries
    known_req_opts = set(inspect.signature(requests.Session.request).parameters)
    known_req_opts -= {"url", "method"}  # add as unknown to always remove them since they are passed by arguments
    for req_opt in set(request_kwargs) - known_req_opts:
        request_kwargs.pop(req_opt)
    request_args = (method, url, request_kwargs)
    return _request_call(*request_args)


def get_header(
    header_name: str,
    header_container: AnyHeadersContainer,
    default: Optional[Union[str, List[str]]] = None,
    pop: bool = False,
    concat: bool = False,
) -> Optional[Union[str, List[str]]]:
    """
    Find the specified header within a header container.

    Retrieves :paramref:`header_name` by fuzzy match (independently of upper/lower-case and underscore/dash) from
    various framework implementations of *Headers*.

    :param header_name: Header to find.
    :param header_container: Where to look for :paramref:`header_name`.
    :param default: Returned value if :paramref:`header_container` is invalid or :paramref:`header_name` is not found.
    :param pop: Remove the matched header(s) by name from the input container.
    :param concat:
        Allow parts of the header name to be concatenated without hyphens/underscores.
        This can be the case in some :term:`S3` responses.
        Disabled by default to avoid unexpected mismatches, notably for shorter named headers.
    :returns: Found header if applicable, or the default value.
    """

    def fuzzy_name(_name: str) -> str:
        return _name.lower().replace("-", "_")

    def concat_name(_name: str) -> str:
        return _name.replace("-", " ").replace("_", " ").capitalize().replace(" ", "")

    if header_container is None:
        return default
    headers = header_container
    if isinstance(
        headers,
        (CaseInsensitiveDict, MappingProxyType),
    ):
        headers = dict(headers)
    if isinstance(headers, dict):
        headers = header_container.items()
    header_name = fuzzy_name(header_name)
    for i, (h, v) in enumerate(list(headers)):
        if fuzzy_name(h) == header_name or (concat and concat_name(h) == concat_name(header_name)):
            if pop:
                if isinstance(header_container, dict):
                    del header_container[h]
                else:
                    del header_container[i]
            return v
    return default


def fully_qualified_name(obj: Union[Any, Type[Any]]) -> str:
    """
    Get the full path definition of the object to allow finding and importing it.

    For classes, functions and exceptions, the following format is returned:

    .. code-block:: python

        module.name

    The ``module`` is omitted if it is a builtin object or type.

    For methods, the class is also represented, resulting in the following format:

    .. code-block:: python

        module.class.name
    """
    if inspect.ismethod(obj):
        return ".".join([obj.__module__, obj.__qualname__])
    cls = obj if inspect.isclass(obj) or inspect.isfunction(obj) else type(obj)
    if "builtins" in getattr(cls, "__module__", "builtins"):  # sometimes '_sitebuiltins'
        return cls.__name__
    return ".".join([cls.__module__, cls.__name__])
