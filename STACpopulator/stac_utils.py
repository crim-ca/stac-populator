import logging
import os
import re
from enum import Enum
from typing import Any, Literal, MutableMapping, Type, Union

import numpy as np
import pystac
import yaml
from colorlog import ColoredFormatter


def get_logger(
    name: str,
    log_fmt: str = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s",
) -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = ColoredFormatter(log_fmt)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


LOGGER = get_logger(__name__)


def url_validate(target: str) -> bool:
    """Validate whether a supplied URL is reliably written.

    Parameters
    ----------
    target : str

    References
    ----------
    https://stackoverflow.com/a/7160778/7322852
    """
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        # domain...
        r"(?:(?:[A-Z\d](?:[A-Z\d-]{0,61}[A-Z\d])?\.)+(?:[A-Z]{2,6}\.?|[A-Z\d-]{2,}\.?)|"
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return True if re.match(url_regex, target) else False


def load_config(
    config_file: Union[os.PathLike[str], str],
) -> MutableMapping[str, Any]:
    """Reads a generic YAML or JSON configuration file.

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


def collection2literal(collection, property="label") -> "Type[Literal]":
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
    # Converting numpy datatypes to python standard datatypes
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


def magpie_resource_link(url: str) -> pystac.Link:
    """Creates a link that will be used by Cowbird to create a resource in Magpie
    associated with the STAC item.

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
    adde = "ADDE"
    dap4 = "DAP4"
    dods = "DODS"  # same as OpenDAP
    opendap = "OpenDAP"
    opendapg = "OpenDAPG"
    netcdfsubset = "NetcdfSubset"
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
