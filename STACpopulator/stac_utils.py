from __future__ import annotations

import logging
import os
import re
from enum import Enum
from functools import cached_property
from typing import Any, List, Literal, MutableMapping, Type, TypedDict, Union

import numpy as np
import pyproj
import pyproj.crs
import pystac
import yaml
from pydantic import ConfigDict, field_validator
from pydantic.dataclasses import dataclass

from STACpopulator.exceptions import STACPopulatorError
from STACpopulator.models import GeoJSONMultiPolygon, GeoJSONPolygon

LOGGER = logging.getLogger(__name__)

CoordDict = TypedDict("Coordinates", {"lat": float, "lon": float, "vert": float | None})


def load_config(
    config_file: Union[os.PathLike[str], str],
) -> MutableMapping[str, Any]:
    """Read a generic YAML or JSON configuration file.

    :raises OSError: If the configuration file is not present
    :raises ValueError: If the configuration file is not correctly formatted.
    :return: A python dictionary describing a generic configuration.
    :rtype: MutableMapping[str, Any]
    """
    if not os.path.isfile(config_file):
        raise OSError(f"Missing configuration file does not exist: [{config_file}]")

    with open(config_file) as f:
        config_info = yaml.load(f, yaml.Loader)

    if not isinstance(config_info, dict) or not config_info:
        raise ValueError(f"Invalid configuration file does not define a mapping: [{config_file}]")
    return config_info


def collection2literal(collection: str, property: str = "label") -> "Type[Literal]":
    """Return a Literal annotation for the given collection and property."""
    terms = tuple(getattr(term, property) for term in collection)
    return Literal[terms]  # noqa


@dataclass(config=ConfigDict(arbitrary_types_allowed=True))
class GeoData:
    """Representation of Geographic Data."""

    crs: pyproj.CRS
    x: tuple[float, float]
    y: tuple[float, float]
    z: tuple[float, float] | None
    x_resolution: float | None
    y_resolution: float | None
    z_resolution: float | None

    @field_validator("crs", mode="before")
    @classmethod
    def create_crs(cls, val: Any) -> pyproj.CRS:
        """Convert crs value to a valid pyproj.CRS class."""
        return pyproj.CRS(val)

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attributes normally but also invalidate cached properties that would need to be recalculated."""
        if name in ("crs", "x", "y", "z") and hasattr(self, "to_wgs84"):
            del self.to_wgs84
        if name == "crs" and hasattr(self, "x_is_longitude"):
            del self.x_is_longitude
        super().__setattr__(name, value)

    @property
    def x_units(self) -> str:
        """Return the unit name for the x axis."""
        return self.crs.axis_info[0].unit_name

    @property
    def y_units(self) -> str:
        """Return the unit name for the y axis."""
        return self.crs.axis_info[1].unit_name

    @property
    def z_units(self) -> str | None:
        """Return the unit name for the z axis or None if there are no values for the z axis."""
        if self.z:
            return self.crs.axis_info[2].unit_name

    @cached_property
    def x_is_longitude(self) -> bool:
        """Return True if x is the longitudinal axis."""
        return self._crs_axis_is_longitude(self.crs.axis_info[0])

    @staticmethod
    def _crs_axis_is_longitude(axis) -> bool:  # noqa: ANN001
        """Guess if axis contains longitude values."""
        lon_pattern = re.compile(r"(^|\s)lon", re.IGNORECASE)
        return bool(
            re.search(lon_pattern, axis.name)
            or re.search(lon_pattern, axis.abbrev)
            or axis.direction.lower() in ("east", "west")
        )

    @cached_property
    def to_wgs84(self) -> CoordDict:
        """
        Return coordinate values converted from the current CRS to a WGS 84 compliant CRS.

        Coordinate values are for longitude, latitude and vertical.
        If the coordinates are 3 dimensional, the CRS EPSG:4979 is used; otherwise EPSG:4326
        is used.
        """
        transformer = pyproj.Transformer.from_crs(self.crs, ("EPSG:4979" if self.z else "EPSG:4326"), always_xy=True)
        coords = ((self.x, self.y) if self.x_is_longitude else (self.y, self.x)) + (self.z,)
        lon, lat, *vert = transformer.transform(*coords)
        if vert:
            vert = vert[0]
        else:
            vert = None
        for val in lon:
            if val > 180 or val < -180:
                raise STACPopulatorError(
                    f"Longitude value {val} is not compliant with WGS 84. "
                    "Please check that the CRS is correct for this data."
                )
        for val in lat:
            if val > 90 or val < -90:
                raise STACPopulatorError(
                    f"Latitude value {val} is not compliant with WGS 84. "
                    "Please check that the CRS is correct for this data."
                )
        return {"lat": lat, "lon": lon, "vert": vert}

    @classmethod
    def from_ncattrs(cls, attrs: MutableMapping[str, Any]) -> GeoData:
        """Return a GeoData object from parsing attributes from CFMetadata."""
        cf_attrs = attrs["groups"]["CFMetadata"]["attributes"]
        stac_populator_attrs = attrs.get("@stac-populator", {})
        geo_data = {}
        # get coordinate reference system
        force_crs = stac_populator_attrs.get("force_crs")
        fallback_crs = stac_populator_attrs.get("fallback_crs")
        if force_crs is not None:
            geo_data["crs"] = force_crs
        elif "geospatial_bounds_crs" in cf_attrs:
            geo_data["crs"] = cf_attrs["geospatial_bounds_crs"]
            if "geospatial_bounds_crs_vertical" in cf_attrs:
                all_crs = (cf_attrs["geospatial_bounds_crs"], cf_attrs["geospatial_bounds_crs_vertical"])
                geo_data["crs"] = pyproj.crs.CompoundCRS(name=" + ".join(all_crs), components=all_crs)
        elif fallback_crs is not None:
            geo_data["crs"] = fallback_crs
        elif cf_attrs.get("geospatial_vertical_min") and cf_attrs.get("geospatial_vertical_max"):
            geo_data["crs"] = "EPSG:4979"
        else:
            geo_data["crs"] = "EPSG:4326"
        geo_data["crs"] = pyproj.CRS(geo_data["crs"])
        # ensure that the CRS is 3D if there are vertical values in the cf_attrs
        if len(geo_data["crs"].axis_info) < 3 and any("_vertical_" in attr for attr in cf_attrs):
            geo_data["crs"] = geo_data["crs"].to_3d()
        x_name = "lon" if cls._crs_axis_is_longitude(geo_data["crs"].axis_info[0]) else "lat"
        # discover min, max, and resolution values for x, y, and z axes
        for axis in ("lat", "lon", "vertical"):
            key = "z" if axis == "vertical" else ("x" if axis == x_name else "y")
            geo_data[key] = []
            for attr in ("min", "max", "resolution"):
                val = cf_attrs.get(f"geospatial_{axis}_{attr}")
                if isinstance(val, list):
                    val = val[0]
                if attr == "resolution":
                    geo_data[f"{key}_resolution"] = None if val is None else float(val)
                else:
                    geo_data[key].append(None if val is None else float(val))
        if geo_data["z"] == [None, None]:
            geo_data["z"] = None
        return cls(**geo_data)

    def crosses_antimeridian(self) -> bool:
        """Return True if the geometry that this GeoData represents extends across the antimeridian."""
        lon_min, lon_max = self.to_wgs84["lon"]
        return lon_min > lon_max

    def to_bbox(self) -> list[float]:
        """Return a bounding box representation of this GeoData."""
        data = self.to_wgs84
        bbox = [data["lon"][0], data["lat"][0], data["lon"][1], data["lat"][1]]
        if data["vert"]:
            bbox.insert(2, data["vert"][0])
            bbox.append(data["vert"][1])
        return bbox

    def _create_linear_ring(
        self, lon_min: float | None = None, lon_max: float | None = None, vertical_val: float | None = None
    ) -> List[List[float]]:
        lon_min = self.to_wgs84["lon"][0] if lon_min is None else lon_min
        lon_max = self.to_wgs84["lon"][1] if lon_max is None else lon_max
        lat_min, lat_max = self.to_wgs84["lat"]
        ring = [
            [
                lon_min,
                lat_min,
            ],
            [
                lon_min,
                lat_max,
            ],
            [
                lon_max,
                lat_max,
            ],
            [
                lon_max,
                lat_min,
            ],
            [
                lon_min,
                lat_min,
            ],
        ]
        if vertical_val is not None:
            for position in ring:
                position.append(vertical_val)
        return ring

    def to_geometry(self) -> GeoJSONPolygon | GeoJSONMultiPolygon:
        """
        Return a GeoJSON geometry representation of this GeoData.

        Vertical data will be included only if the vertical data is not None and vertical_max
        equals vertical_min. This is because GeoJSON geometries do not represent 3D shapes and
        so cannot represent a shape with volume. In the case where the vertical dimension is
        omitted from the result here, it can still be seen in the bounding box that is returned
        from calling the to_bbox method.
        """
        vertical = self.to_wgs84["vert"]
        vertical_val = vertical[0] if vertical and vertical[0] == vertical[1] else None
        if self.crosses_antimeridian():
            return GeoJSONMultiPolygon(
                type="MultiPolygon",
                coordinates=[
                    [self._create_linear_ring(lon_max=180, vertical_val=vertical_val)],
                    [self._create_linear_ring(lon_min=-180, vertical_val=vertical_val)],
                ],
            )
        else:
            return GeoJSONPolygon(type="Polygon", coordinates=[self._create_linear_ring(vertical_val=vertical_val)])


def numpy_to_python_datatypes(data: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Convert numpy datatypes to python standard datatypes.

    This is useful when validating against a JSON schema that does not recognize an int32 as an integer.
    """
    for key, value in data.items():
        if isinstance(value, list):
            newlist = []
            for item in value:
                if issubclass(type(item), np.integer):
                    newlist.append(int(item))
                elif issubclass(type(item), np.floating):
                    newlist.append(float(item))
                else:
                    newlist.append(item)
            data[key] = newlist
        elif isinstance(type(value), np.integer):
            data[key] = int(value)

    return data


def np2py(data: Any) -> Any:
    """Convert numpy datatypes to python standard datatypes.

    This is useful when validating against a JSON schema that does not recognize an int32 as an integer.

    Parameters
    ----------
    data : dict, list, tuple, int, float, np.integer, np.floating, str
      Object to convert.
    """
    if isinstance(data, dict):
        return {key: np2py(value) for key, value in data.items()}

    elif isinstance(data, (list, tuple)):
        out = [np2py(item) for item in data]
        if isinstance(data, tuple):
            return tuple(out)
        return out

    else:
        return getattr(data, "tolist", lambda: data)()


def magpie_resource_link(url: str) -> pystac.Link:
    """
    Create a link that will be used by Cowbird to create a resource in Magpie associated with the STAC item.

    :param url: HTTPServer access URL for a STAC item
    :type url: str
    :return: A PySTAC Link
    :rtype: pystac.Link
    """
    url_ = url.replace("fileServer", "*")
    i = url_.find("*")
    title = url_[i + 2 :]
    link = pystac.Link(rel="source", title=title, target=url, media_type="application/x-netcdf")
    return link


class ServiceType(Enum):
    """Service Type."""

    adde = "ADDE"
    dap4 = "DAP4"
    dods = "DODS"  # same as OpenDAP
    opendap = "OpenDAP"
    opendapg = "OpenDAPG"
    netcdfsubset = "NetcdfSubset"  # used in THREDDS version < 5.0
    netcdfsubsetgrid = "NetcdfSubsetGrid"  # used in THREDDS version > 5.0
    netcdfsubsetpoint = "NetcdfSubsetPoint"  # used in THREDDS version > 5.0
    cdmremote = "CdmRemote"
    cdmfeature = "CdmFeature"
    ncjson = "ncJSON"
    h5service = "H5Service"
    httpserver = "HTTPServer"
    ftp = "FTP"
    gridftp = "GridFTP"
    file = "File"
    iso = "ISO"
    las = "LAS"
    ncml = "NcML"
    uddc = "UDDC"
    wcs = "WCS"
    wms = "WMS"
    wsdl = "WSDL"
    webform = "WebForm"
    catalog = "Catalog"
    compound = "Compound"
    resolver = "Resolver"
    thredds = "THREDDS"

    @classmethod
    def from_value(cls, value: str, default: Any = KeyError) -> "ServiceType":
        """Return value irrespective of case."""
        try:
            svc = value.lower()
            if svc.endswith("_service"):  # handle NCML edge cases
                svc = svc.rsplit("_", 1)[0]
            return cls[svc]
        except KeyError:
            if default is not KeyError:
                return default
            raise
