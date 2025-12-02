from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict
from enum import Enum
from typing import Any, List, Literal, MutableMapping, Self, Type, Union

import numpy as np
import pystac
import yaml
from pydantic import Field, model_validator
from pydantic.dataclasses import dataclass

from STACpopulator.models import GeoJSONMultiPolygon, GeoJSONPolygon

LOGGER = logging.getLogger(__name__)


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


@dataclass
class GeoData:
    """Representation of Geographic Data."""

    lon_min: float = Field(ge=-180.0, le=360.0)
    lon_max: float = Field(ge=-180.0, le=360.0)
    lon_units: str = "degrees_east"
    lon_resolution: float | None = None
    lat_min: float = Field(ge=-90.0, le=90.0)
    lat_max: float = Field(ge=-90.0, le=90.0)
    lat_units: str = "degrees_north"
    lat_resolution: float | None = None
    vertical_min: float | None = None
    vertical_max: float | None = None
    # vertical units are assumed to be in metres unless otherwise specified:
    # https://wiki.esipfed.org/Attribute_Convention_for_Data_Discovery_1-3
    vertical_units: str = "m"
    vertical_resolution: float | None = None
    # vertical orientation (up/down) is assumed to be "up" if not specified.
    vertical_positive: Literal["up", "down"] = "up"

    # see: https://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#longitude-coordinate
    _lon_units_pattern = re.compile(r"^degrees?_?e(ast)?$", re.IGNORECASE)
    # see https://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#latitude-coordinate
    _lat_units_pattern = re.compile(r"^degrees?_?n(orth)?$", re.IGNORECASE)
    # see: https://cfconventions.org/cf-conventions/v1.6.0/cf-conventions.html#vertical-coordinate
    # TODO: try to support more units: convert some common non-metre units to metres
    _vertical_units_pattern = re.compile(r"^m(et(re|er)s?)?$", re.IGNORECASE)

    @model_validator(mode="after")
    def to_wgs84(self) -> Self:
        """
        Make the data WGS84 compliant.

        This involves converting the longitude ranges to be between -180 an 180 degrees and
        ensuring that positive vertical values represent values higher than the surface.
        """
        self._org_lon_min = self.lon_min
        self._org_lon_max = self.lon_max
        self._org_vertical_min = self.vertical_min
        self._org_vertical_max = self.vertical_max
        self.lon_min = -(360 % self.lon_min) if self.lon_min > 180 else self.lon_min
        self.lon_max = -(360 % self.lon_max) if self.lon_max > 180 else self.lon_max
        coordinate_err_msg = (
            "%s units must be in %s. Units given in '%s'. "
            "If a different coordinate system is used, "
            "the STAC geometry representation may not be accurate."
        )
        if self.lon_units and not re.match(self._lon_units_pattern, self.lon_units):
            LOGGER.warning(coordinate_err_msg, "Longitude", "degrees east", self.lon_units)
        if self.lat_units and not re.match(self._lat_units_pattern, self.lat_units):
            LOGGER.warning(coordinate_err_msg, "Latitude", "degrees north", self.lat_units)
        if self.vertical_units and not re.match(self._vertical_units_pattern, self.vertical_units):
            LOGGER.warning(coordinate_err_msg, "Vertical", "metres", self.vertical_units)
        if self.has_z():
            if self.vertical_positive == "down":
                self.vertical_min *= -1
                self.vertical_max *= -1
                self.vertical_min, self.vertical_max = sorted([self.vertical_min, self.vertical_max])
        return self

    def original_data(self) -> dict[str, float | str | None]:
        """
        Return a dictionary representing the original values of the fields used to create this GeoData object.

        These are the values before the longitude values have been made compliant with WGS84.
        """
        data = asdict(self)
        data["lon_min"] = self._org_lon_min
        data["lon_max"] = self._org_lon_max
        data["vertical_min"] = self._org_vertical_min
        data["vertical_max"] = self._org_vertical_max
        return data

    @classmethod
    def from_ncattrs(cls, attrs: MutableMapping[str, Any]) -> GeoData:
        """Return a GeoData object from parsing attributes from CFMetadata."""
        attrs = attrs["groups"]["CFMetadata"]["attributes"]
        geo_range = {}
        for field in cls.__pydantic_fields__:
            field_suffix = field.split("_")[-1]
            val = attrs.get(f"geospatial_{field}")
            if field_suffix in ("min", "max", "resolution"):
                if isinstance(val, list):
                    val = val[0]
                geo_range[field] = None if val is None else float(val)
            elif val is not None:
                geo_range[field] = val
        return cls(**geo_range)

    def has_z(self) -> bool:
        """Return True if this GeoData contains data for the z (vertical) axis."""
        return self.vertical_min is not None and self.vertical_max is not None

    def crosses_antimeridian(self) -> bool:
        """Return True if the geometry that this GeoData represents extends across the antimeridian."""
        return self.lon_min > self.lon_max

    def to_bbox(self) -> list[float]:
        """Return a bounding box representation of this GeoData."""
        bbox = [self.lon_min, self.lat_min, self.lon_max, self.lat_max]
        if self.has_z():
            bbox.insert(2, self.vertical_min)
            bbox.append(self.vertical_max)
        return bbox

    def _create_linear_ring(
        self, lon_min: float | None = None, lon_max: float | None = None, vertical_val: float | None = None
    ) -> List[List[float]]:
        lon_min = self.lon_min if lon_min is None else lon_min
        lon_max = self.lon_max if lon_max is None else lon_max
        ring = [
            [
                lon_min,
                self.lat_min,
            ],
            [
                lon_min,
                self.lat_max,
            ],
            [
                lon_max,
                self.lat_max,
            ],
            [
                lon_max,
                self.lat_min,
            ],
            [
                lon_min,
                self.lat_min,
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
        vertical_val = self.vertical_min if self.vertical_min == self.vertical_max else None
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
