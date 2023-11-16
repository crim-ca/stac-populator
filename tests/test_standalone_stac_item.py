import json
import pytest
import os
import tempfile
from urllib.parse import quote

from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import CMIP6ItemProperties, CMIP6populator
from STACpopulator.input import THREDDSLoader
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.stac_utils import STAC_item_from_metadata, ncattrs
from pystac.validation import JsonSchemaSTACValidator
from pystac import STACObjectType

CUR_DIR = os.path.dirname(__file__)


def quote_none_safe(url):
    return quote(url, safe="")


@pytest.mark.online
def test_standalone_stac_item_thredds_ncml():
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc"
    attrs = ncattrs(url)
    stac_item_id = CMIP6populator.make_cmip6_item_id(attrs["attributes"])
    stac_item = STAC_item_from_metadata(stac_item_id, attrs, CMIP6ItemProperties, GeoJSONPolygon)
    assert stac_item.validate()


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
            "temporalextent": ['1850-01-01', None]
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
        reference = json.load(ff)

    assert result == reference
