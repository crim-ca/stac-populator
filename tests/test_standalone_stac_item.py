import json

import requests
import xncml

from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import (
    CMIP6ItemProperties,
    make_cmip6_item_id,
)
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.stac_utils import STAC_item_from_metadata


def test_standalone_stac_item():
    url = (
        "https://pavics.ouranos.ca/twitcher/ows/proxy/"
        "thredds/ncml/birdhouse/testdata/xclim/cmip6/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc"
        "?catalog=https%3A%2F%2Fpavics.ouranos.ca%2Ftwitcher%2Fows%2Fproxy%2F"
        "thredds%2Fcatalog%2Fbirdhouse%2Ftestdata%2Fxclim%2Fcmip6%2Fcatalog.html"
        "&dataset=birdhouse%2Ftestdata%2Fxclim%2Fcmip6%2Fsic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc"
    )

    attrs = xncml.Dataset.from_text(requests.get(url).content).to_cf_dict()
    stac_item_id = make_cmip6_item_id(attrs["attributes"])
    stac_item = STAC_item_from_metadata(stac_item_id, attrs, CMIP6ItemProperties, GeoJSONPolygon)

    with open("tests/ref.json", "r") as ff:
        reference = json.load(ff)

    assert stac_item.to_dict() == reference
