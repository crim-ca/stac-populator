import json
import os
import tempfile
from urllib.parse import quote

import pystac
import pytest
import requests
import xncml

from STACpopulator.extensions.cmip6 import CMIP6Helper
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper
from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import CMIP6populator
from STACpopulator.input import THREDDSLoader
from STACpopulator.models import GeoJSONPolygon

CUR_DIR = os.path.dirname(__file__)


def quote_none_safe(url):
    return quote(url, safe="")


@pytest.mark.online
def test_standalone_stac_item_thredds_ncml():
    thredds_url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds"
    thredds_path = "birdhouse/testdata/xclim/cmip6"
    thredds_nc = "sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc"
    thredds_catalog = f"{thredds_url}/catalog/{thredds_path}/catalog.html"
    thredds_ds = f"{thredds_path}/{thredds_nc}"
    thredds_ncml_url = (
        f"{thredds_url}/ncml/{thredds_path}/{thredds_nc}"
        f"?catalog={quote_none_safe(thredds_catalog)}&dataset={quote_none_safe(thredds_ds)}"
    )

    # FIXME: avoid hackish workarounds
    data = requests.get(thredds_ncml_url).text
    attrs = xncml.Dataset.from_text(data).to_cf_dict()
    attrs["access_urls"] = {  # FIXME: all following should be automatically added, but they are not!
        "HTTPServer": f"{thredds_url}/fileServer/{thredds_path}/{thredds_nc}",
        "OPENDAP": f"{thredds_url}/dodsC/{thredds_path}/{thredds_nc}",
        "WCS": f"{thredds_url}/wcs/{thredds_path}/{thredds_nc}?service=WCS&version=1.0.0&request=GetCapabilities",
        "WMS": f"{thredds_url}/wms/{thredds_path}/{thredds_nc}?service=WMS&version=1.3.0&request=GetCapabilities",
        "NetcdfSubset": f"{thredds_url}/ncss/{thredds_path}/{thredds_nc}/dataset.html",
    }
    stac_item = CMIP6Helper(attrs, GeoJSONPolygon).stac_item()
    thredds_helper = THREDDSHelper(attrs["access_urls"])
    thredds_ext = THREDDSExtension.ext(stac_item)
    thredds_ext.apply(services=thredds_helper.services, links=thredds_helper.links)

    ref_file = os.path.join(CUR_DIR, "data/stac_item_testdata_xclim_cmip6_ncml.json")
    with open(ref_file, mode="r", encoding="utf-8") as ff:
        reference = pystac.Item.from_dict(json.load(ff)).to_dict()

    assert stac_item.to_dict() == reference


class MockedNoSTACUpload(CMIP6populator):
    def load_config(self):
        # bypass auto-load config
        self._collection_info = {
            "id": "test",
            "title": "test",
            "description": "test",
            "keywords": ["test"],
            "license": "MIT",
            "spatialextent": [-180, -90, 180, 90],
            "temporalextent": ["1850-01-01", None],
        }

    def validate_host(self, stac_host: str) -> str:
        pass  # don't care

    def publish_stac_collection(self, *_) -> None:
        pass  # don't push to STAC API


@pytest.mark.online
def test_cmip6_stac_thredds_catalog_parsing():
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.html"
    loader = THREDDSLoader(url)
    with tempfile.NamedTemporaryFile():
        populator = MockedNoSTACUpload("https://host-dont-care.com", loader)

    result = populator.create_stac_collection()

    ref_file = os.path.join(CUR_DIR, "data/stac_collection_testdata_xclim_cmip6_catalog.json")
    with open(ref_file, mode="r", encoding="utf-8") as ff:
        reference = pystac.Collection.from_dict(json.load(ff)).to_dict()

    assert result == reference
