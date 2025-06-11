import logging
import os
from enum import Enum
from typing import Any, Literal, MutableMapping, Type, Union

import numpy as np
import pystac
import yaml

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


def ncattrs_to_geometry(attrs: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Create Polygon geometry from CFMetadata."""
    attrs = attrs["groups"]["CFMetadata"]["attributes"]
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    float(attrs["geospatial_lon_min"][0]),
                    float(attrs["geospatial_lat_min"][0]),
                ],
                [
                    float(attrs["geospatial_lon_min"][0]),
                    float(attrs["geospatial_lat_max"][0]),
                ],
                [
                    float(attrs["geospatial_lon_max"][0]),
                    float(attrs["geospatial_lat_max"][0]),
                ],
                [
                    float(attrs["geospatial_lon_max"][0]),
                    float(attrs["geospatial_lat_min"][0]),
                ],
                [
                    float(attrs["geospatial_lon_min"][0]),
                    float(attrs["geospatial_lat_min"][0]),
                ],
            ]
        ],
    }


def ncattrs_to_bbox(attrs: MutableMapping[str, Any]) -> list[float]:
    """Create BBOX from CFMetadata."""
    attrs = attrs["groups"]["CFMetadata"]["attributes"]
    return [
        float(attrs["geospatial_lon_min"][0]),
        float(attrs["geospatial_lat_min"][0]),
        float(attrs["geospatial_lon_max"][0]),
        float(attrs["geospatial_lat_max"][0]),
    ]


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
