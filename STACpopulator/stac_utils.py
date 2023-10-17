import json
import re
from typing import Any, Literal, MutableMapping

import numpy as np
import pystac

from STACpopulator.models import STACItem


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


def collection2literal(collection):
    terms = tuple(term.label for term in collection)
    return Literal[terms]


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

    # Add assets
    if "access_urls" in attrs:
        root = attrs["access_urls"]
    elif "THREDDSMetadata" in attrs["groups"]:
        root = attrs["groups"]["THREDDSMetadata"]["groups"]["services"]["attributes"]
    else:
        root = {}

    for name, url in root.items():
        name = str(name)  # converting name from siphon.catalog.CaseInsensitiveStr to str
        asset = pystac.Asset(href=url, media_type=media_types.get(name), roles=asset_roles.get(name))
        item.add_asset(name, asset)

    return item


media_types = {
    "httpserver_service": "application/x-netcdf",
    "opendap_service": pystac.MediaType.HTML,
    "wcs_service": pystac.MediaType.XML,
    "wms_service": pystac.MediaType.XML,
    "nccs_service": "application/x-netcdf",
    "HTTPServer": "application/x-netcdf",
    "OPENDAP": pystac.MediaType.HTML,
    "NCML": pystac.MediaType.XML,
    "WCS": pystac.MediaType.XML,
    "ISO": pystac.MediaType.XML,
    "WMS": pystac.MediaType.XML,
    "NetcdfSubset": "application/x-netcdf",
}

asset_roles = {
    "httpserver_service": ["data"],
    "opendap_service": ["data"],
    "wcs_service": ["data"],
    "wms_service": ["visual"],
    "nccs_service": ["data"],
    "HTTPServer": ["data"],
    "OPENDAP": ["data"],
    "NCML": ["metadata"],
    "WCS": ["data"],
    "ISO": ["metadata"],
    "WMS": ["visual"],
    "NetcdfSubset": ["data"],
}
