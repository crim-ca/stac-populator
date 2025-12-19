from enum import Enum
from typing import (
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Tuple,
    Union,
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

AnyRequestMethod = Union[RequestMethod, str]
HeadersType = Mapping[str, str]
HeadersTupleType = List[Tuple[str, str]]
HeadersBaseType = Union[HeadersType, HeadersTupleType]
AnyHeadersContainer = Union[HeadersBaseType, CaseInsensitiveDict]
AnyRequestType = Union[PreparedRequest, RequestsRequest]
Number = Union[int, float]
ValueType = Union[str, Number, bool]
AnyValueType = Optional[ValueType]
CookiesType = Dict[str, str]
CookiesTupleType = List[Tuple[str, str]]
HeaderCookiesList = Union[HeadersTupleType, CookiesTupleType]
CookiesBaseType = Union[CookiesType, CookiesTupleType]
HeaderCookiesType = Union[HeadersBaseType, CookiesBaseType]
HeaderCookiesTuple = Union[Tuple[None, None], Tuple[HeadersBaseType, CookiesBaseType]]
AnyCookiesContainer = Union[CookiesBaseType, AnyHeadersContainer]
AnyHeadersCookieContainer = Union[AnyHeadersContainer, AnyCookiesContainer]

RequestOptions = TypedDict(
    "RequestOptions",
    {
        "timeout": NotRequired[int],
        "connect_timeout": NotRequired[int],
        "read_timeout": NotRequired[int],
        "retry": NotRequired[int],
        "retries": NotRequired[int],
        "max_retries": NotRequired[int],
        "backoff": NotRequired[Number],
        "backoff_factor": NotRequired[Number],
        "headers": NotRequired[AnyHeadersContainer],
        "cookies": NotRequired[AnyCookiesContainer],
        "stream": NotRequired[bool],
        "cache": NotRequired[bool],
        "cache_enabled": NotRequired[bool],
    },
    total=False,
)


class ContentType(Enum):
    """
    Supported ``Content-Type`` values.

    Media-Type nomenclature::

        <type> "/" [x- | <tree> "."] <subtype> ["+" suffix] *[";" parameter=value]
    """

    APP_JSON = "application/json"
