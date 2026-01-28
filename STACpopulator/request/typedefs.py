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
from typing_extensions import NotRequired, TypedDict

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
RequestOptions = TypedDict(
    "RequestOptions",
    {
        "timeout": NotRequired[int],
        "connect_timeout": NotRequired[int],
        "read_timeout": NotRequired[int],
        "retry": NotRequired[int],
        "retries": NotRequired[int],
        "max_retries": NotRequired[int],
        "backoff": NotRequired[int | float],
        "backoff_factor": NotRequired[int | float],
        "headers": NotRequired[AnyHeadersContainer],
        "cookies": NotRequired[CookiesType],
        "stream": NotRequired[bool],
        "cache": NotRequired[bool],
        "cache_enabled": NotRequired[bool],
    },
    total=False,
)

# Standard Content-Type for JSON responses
APP_JSON = "application/json"
