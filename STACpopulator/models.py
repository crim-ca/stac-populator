import datetime as dt
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, AnyUrl, BaseModel, Field, field_validator
from typing_extensions import TypedDict


class Geometry(TypedDict):
    type: str
    coordinates: List[List[List[float]]]


class Asset(BaseModel):
    href: AnyHttpUrl
    media_type: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    roles: Optional[List[str]] = None


class STACItemProperties(BaseModel):
    start_datetime: Optional[dt.datetime] = None
    end_datetime: Optional[dt.datetime] = None
    datetime: Optional[dt.datetime] = None

    @field_validator("datetime", mode="before")
    @classmethod
    def validate_datetime(cls, v: Union[dt.datetime, str], values: Dict[str, Any]) -> dt:
        if v == "null":
            if not values["start_datetime"] and not values["end_datetime"]:
                raise ValueError("start_datetime and end_datetime must be specified when datetime is null")


# class Link(BaseModel):
#     """
#     https://github.com/radiantearth/stac-spec/blob/v1.0.0/collection-spec/collection-spec.md#link-object
#     """

#     href: str = Field(..., alias="href", min_length=1)
#     rel: str = Field(..., alias="rel", min_length=1)
#     type: Optional[str] = None
#     title: Optional[str] = None
#     # Label extension
#     label: Optional[str] = Field(None, alias="label:assets")
#     model_config = ConfigDict(use_enum_values=True)

#     def resolve(self, base_url: str) -> None:
#         """resolve a link to the given base URL"""
#         self.href = urljoin(base_url, self.href)


# class PaginationLink(Link):
#     """
#     https://github.com/radiantearth/stac-api-spec/blob/master/api-spec.md#paging-extension
#     """

#     rel: Literal["next", "previous"]
#     method: Literal["GET", "POST"]
#     body: Optional[Dict[Any, Any]] = None
#     merge: bool = False


# Links = RootModel[List[Union[PaginationLink, Link]]]


class STACItem(BaseModel):
    id: str = Field(..., alias="id", min_length=1)
    geometry: Optional[Geometry] = None
    bbox: Optional[List[float]] = None
    properties: Optional[STACItemProperties] = None
    assets: Dict[str, Asset] = None
    stac_extensions: Optional[List[AnyUrl]] = []
    collection: Optional[str] = None
    datetime: Optional[dt.datetime] = None  # Not in the spec, but needed by pystac.Item.