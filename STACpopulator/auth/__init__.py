"""Authentication module for STAC Populator."""

from typing import (
    Dict,
    List,
    Literal,
    Mapping,
    Tuple,
)

from requests import PreparedRequest
from requests import Request as RequestsRequest
from requests.structures import CaseInsensitiveDict

RequestMethod = Literal[
    "HEAD",
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]
AnyHeadersContainer = (
    Mapping[str, str]  # Headers can be provided as a dict-like object
    | List[Tuple[str, str]]  # or as a list of tuples
    | CaseInsensitiveDict  # or as a CaseInsensitiveDict from requests
)
AnyRequestType = PreparedRequest | RequestsRequest
CookiesType = Dict[str, str]

# Standard Content-Type for JSON responses
APP_JSON = "application/json"

__all__ = [
    "RequestMethod",
    "AnyHeadersContainer",
    "AnyRequestType",
    "CookiesType",
    "APP_JSON",
]
