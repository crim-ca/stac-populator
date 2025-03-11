from typing import List, Literal, Union

from pydantic import (
    BaseModel,
)


class Geometry(BaseModel):
    """GeoJSON geometry."""

    type: str
    coordinates: List


class GeoJSONPoint(Geometry):
    """GeoJSON Point geometry."""

    type: Literal["Point"]
    coordinates: List[float]


class GeoJSONMultiPoint(Geometry):
    """GeoJSON Multi Point geometry."""

    type: Literal["MultiPoint"]
    coordinates: List[List[float]]


class GeoJSONPolygon(Geometry):
    """GeoJSON Polygon geometry."""

    type: Literal["Polygon"]
    coordinates: List[List[List[float]]]


class GeoJSONMultiPolygon(Geometry):
    """GeoJSON Multi Polygon geometry."""

    type: Literal["MultiPolygon"]
    coordinates: List[List[List[List[float]]]]


AnyGeometry = Union[
    Geometry,
    GeoJSONPoint,
    GeoJSONMultiPoint,
    GeoJSONPolygon,
    GeoJSONMultiPolygon,
]
