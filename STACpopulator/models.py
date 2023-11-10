import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class Geometry(BaseModel):
    type: str
    coordinates: List


class GeoJSONPoint(Geometry):
    type: Literal["Point"]
    coordinates: List[float]


class GeoJSONMultiPoint(Geometry):
    type: Literal["MultiPoint"]
    coordinates: List[List[float]]


class GeoJSONPolygon(Geometry):
    type: Literal["Polygon"]
    coordinates: List[List[List[float]]]


class GeoJSONMultiPolygon(Geometry):
    type: Literal["MultiPolygon"]
    coordinates: List[List[List[List[float]]]]


class STACItemProperties(BaseModel):
    """
    Base STAC Item properties data model.

    In concrete implementations, users would want to define a new data model that inherits from this base model
    and extends it with properties tailored to the data they are ingesting.
    """
    start_datetime: Optional[datetime.datetime] = None
    end_datetime: Optional[datetime.datetime] = None
    datetime_: Optional[datetime.datetime] = Field(None, alias="datetime")

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, item):
        return getattr(self, item)

    def __delitem__(self, item):
        return delattr(self, item)
