import datetime as dt
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    AnyHttpUrl,
    AnyUrl,
    BaseModel,
    Field,
    SerializeAsAny,
    field_validator,
)


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


AnyGeometry = Union[
    Geometry,
    GeoJSONPoint,
    GeoJSONMultiPoint,
    GeoJSONPolygon,
    GeoJSONMultiPolygon,
]
