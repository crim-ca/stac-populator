import datetime
import json
import logging
import os
import re
import sys
from typing import Any, Literal, MutableMapping
import requests
import xncml
import xmltodict
import urllib

import numpy as np
import pystac
import yaml
from colorlog import ColoredFormatter

from STACpopulator.models import STACItem

LOGGER = logging.getLogger(__name__)
LOG_FORMAT = "  %(log_color)s%(levelname)s:%(reset)s %(blue)s[%(name)-30s]%(reset)s %(message)s"
formatter = ColoredFormatter(LOG_FORMAT)
stream = logging.StreamHandler()
stream.setFormatter(formatter)
LOGGER.addHandler(stream)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


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


def load_collection_configuration() -> MutableMapping[str, Any]:
    """Reads details of the STAC Collection to be created from a configuration file. the
    code expects a "collection_config.yml" file to be present in the app directory.

    :raises RuntimeError: If the configuration file is not present
    :raises RuntimeError: If required values are not present in the configuration file
    :return: A python dictionary describing the details of the Collection
    :rtype: MutableMapping[str, Any]
    """
    collection_info_filename = "collection_config.yml"
    app_directory = os.path.dirname(sys.argv[0])

    if not os.path.exists(os.path.join(app_directory, collection_info_filename)):
        raise RuntimeError(f"Missing {collection_info_filename} file for this implementation")

    with open(os.path.join(app_directory, collection_info_filename)) as f:
        collection_info = yaml.load(f, yaml.Loader)

    req_definitions = ["title", "id", "description", "keywords", "license"]
    for req in req_definitions:
        if req not in collection_info.keys():
            LOGGER.error(f"'{req}' is required in the configuration file")
            raise RuntimeError(f"'{req}' is required in the configuration file")

    return collection_info


def collection2literal(collection, property="label"):
    terms = tuple(getattr(term, property) for term in collection)
    return Literal[terms]


def thredds_catalog_attrs(url: str) -> dict:
    """Return attributes from the catalog.xml THREDDS server response."""
    xml = requests.get(url).text

    raw = xmltodict.parse(
        xml,
        process_namespaces=True,
        namespaces={
            "http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0": None,
            "https://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0": None,
        },
    )
    return raw


def ncattrs(url: str) -> dict:
    """Return attributes from a THREDDS netCDF dataset."""

    pr = urllib.parse.urlparse(url)
    scheme, netloc, path, params, query, frag = pr

    # URL is a reference to a catalog item
    if query:
        q = urllib.parse.parse_qs(query)
        nc = q["dataset"][0].split("/")[-1]

        if path.endswith("catalog.html"):
            path = path.replace("catalog.html", "catalog.xml")
    else:
        nc = path.split("/")[-1]
        path = path.replace(nc, "catalog.xml")

    # Get catalog information about available services
    catalog = urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))
    cattrs = thredds_catalog_attrs(catalog)["catalog"]
    cid = cattrs["dataset"]["@ID"]

    if not query:
        cid += f"/{nc}"

    # Get service URLs for the dataset
    access_urls = {}
    for service in cattrs["service"]["service"]:
        access_urls[service["@serviceType"]] = f'{scheme}://{netloc}{service["@base"]}{cid}'

    # Get dataset attributes
    r = requests.get(access_urls["NCML"])
    attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
    attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])

    # Include service attributes
    attrs["access_urls"] = access_urls
    return attrs


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


def STAC_item_from_metadata(iid: str, attrs: MutableMapping[str, Any], item_props_datamodel, item_geometry_model):
    """
    Create STAC Item from CF JSON metadata.

    Parameters
    ----------
    iid : str
        Unique item ID.
    attrs: dict
        CF JSON metadata returned by `xncml.Dataset.to_cf_dict`.
    item_props_datamodel : pydantic.BaseModel
        Data model describing the properties of the STAC item.
    item_geometry_model : pydantic.BaseModel
        Data model describing the geometry of the STAC item.
    """

    cfmeta = attrs["groups"]["CFMetadata"]["attributes"]

    # Create pydantic STAC item
    item = STACItem(
        id=iid,
        geometry=item_geometry_model(**ncattrs_to_geometry(attrs)),
        bbox=ncattrs_to_bbox(attrs),
        properties=item_props_datamodel(
            start_datetime=cfmeta["time_coverage_start"],
            end_datetime=cfmeta["time_coverage_end"],
            **attrs["attributes"],
        ),
        datetime=None,
    )

    # Convert pydantic STAC item to a PySTAC Item
    item = pystac.Item(**json.loads(item.model_dump_json(by_alias=True)))

    root = attrs["access_urls"]

    for name, url in root.items():
        name = str(name)  # converting name from siphon.catalog.CaseInsensitiveStr to str
        asset = pystac.Asset(href=url, media_type=media_types.get(name), roles=asset_roles.get(name))

        item.add_asset(name, asset)

    item.add_link(magpie_resource_link(root["HTTPServer"]))

    return item


asset_name_remaps = {
    "httpserver_service": "HTTPServer",
    "opendap_service": "OPENDAP",
    "wcs_service": "WCS",
    "wms_service": "WMS",
    "nccs_service": "NetcdfSubset",
}

media_types = {
    "HTTPServer": "application/x-netcdf",
    "OPENDAP": pystac.MediaType.HTML,
    "NCML": pystac.MediaType.XML,
    "WCS": pystac.MediaType.XML,
    "WMS": pystac.MediaType.XML,
    "NetcdfSubset": "application/x-netcdf",
    "ISO": pystac.MediaType.XML,
    "UDDC": pystac.MediaType.HTML
}

asset_roles = {
    "HTTPServer": ["data"],
    "OPENDAP": ["data"],
    "WCS": ["data"],
    "WMS": ["visual"],
    "NetcdfSubset": ["data"],
    "NCML": ["metadata"],
    "ISO": ["metadata"],
    "UDDC": ["metadata"]
}
