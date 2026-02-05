import json
import os
import pathlib
import sys
from copy import deepcopy
from unittest.mock import patch
from urllib.parse import quote

import pystac
import pytest
import requests
import xncml

from STACpopulator.extensions.cmip6 import CMIP6Helper
from STACpopulator.extensions.thredds import THREDDSExtension, THREDDSHelper
from STACpopulator.input import THREDDSLoader
from STACpopulator.populators import STACpopulatorBase


@pytest.fixture
def cur_dir(request: pytest.FixtureRequest) -> pathlib.Path:
    return request.path.parent


def quote_none_safe(url):
    return quote(url, safe="")


def _approximate_nested(val: float | list):
    if isinstance(val, list):
        return [_approximate_nested(x) for x in val]
    else:
        return pytest.approx(val)


def compare_stac_items(item1, item2):
    item_copy = deepcopy(item1)
    geometry = item_copy["geometry"]
    if item_copy["bbox"] is not None:
        item_copy["bbox"] = _approximate_nested(item_copy["bbox"])
    if geometry is not None:
        geometry["coordinates"] = _approximate_nested(geometry["coordinates"])
    assert item_copy == item2


@pytest.mark.vcr
def test_standalone_stac_item_thredds_ncml(cur_dir, epsg4979_0_360_wkt):
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
    attrs["access_urls"] = {  # these ideally should be added with xncml but they're not
        "HTTPServer": f"{thredds_url}/fileServer/{thredds_path}/{thredds_nc}",
        "OPENDAP": f"{thredds_url}/dodsC/{thredds_path}/{thredds_nc}",
        "WCS": f"{thredds_url}/wcs/{thredds_path}/{thredds_nc}",
        "WMS": f"{thredds_url}/wms/{thredds_path}/{thredds_nc}",
        "NetcdfSubset": f"{thredds_url}/ncss/{thredds_path}/{thredds_nc}/dataset.html",
    }
    attrs["@stac-populator"] = {"fallback_crs": epsg4979_0_360_wkt}
    stac_item = CMIP6Helper(attrs).stac_item()
    thredds_helper = THREDDSHelper(attrs["access_urls"])
    thredds_ext = THREDDSExtension.ext(stac_item)
    thredds_ext.apply(services=thredds_helper.services, links=thredds_helper.links)

    ref_file = os.path.join(cur_dir, "data/stac_item_testdata_xclim_cmip6_ncml.json")
    with open(ref_file, mode="r", encoding="utf-8") as ff:
        reference = pystac.Item.from_dict(json.load(ff)).to_dict()

    compare_stac_items(stac_item.to_dict(), reference)


class MockedNoSTACUpload(STACpopulatorBase):
    def load_config(self):
        # bypass auto-load config
        self._collection_info = {
            "id": "test",
            "title": "test",
            "description": "test",
            "keywords": ["test"],
            "license": "MIT",
            "spatialextent": [0, 0, 0, 0],
            "temporalextent": ["2020-01-01", None],
        }

    def validate_host(self, stac_host: str) -> str:
        pass  # don't care

    def publish_stac_collection(self, *_) -> None:
        pass  # don't push to STAC API

    def create_stac_item(self, item_name, item_data):
        self._count = getattr(self, "_count", -1) + 1
        bboxes = [[-10, -20, 10, 30], [-11, 2, 9, 50], [0, 0, 2, 4], [22, -1, 56, 11]]
        datetimes = [
            ("1845-12-04", "1893-02-18"),
            ("1992-05-12", "2222-04-11"),
            ("1066-05-01", "2045-09-20"),
            ("2000-01-01", "2045-01-01"),
        ]
        # random trivia to add to the stac item
        ducks = ["Alabio", "Blekinge", "Muscovy", "Rouen"]
        return {
            "id": item_name,
            "access_urls": item_data["access_urls"],
            "bbox": bboxes[self._count],
            "properties": {
                "start_datetime": datetimes[self._count][0],
                "end_datetime": datetimes[self._count][1],
                "ducks": ducks[self._count],
                "another_date": datetimes[self._count][1],
            },
        }

    def run(cls, *args, **kwargs): ...


@pytest.mark.vcr("test_cmip6_stac_thredds_catalog_parsing.yaml")
def test_cmip6_stac_thredds_catalog_parsing(cur_dir):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    populator = MockedNoSTACUpload("https://example.com", loader)

    result = populator.create_stac_collection()

    ref_file = os.path.join(cur_dir, "data/stac_collection_testdata_xclim_cmip6_catalog.json")
    with open(ref_file, mode="r", encoding="utf-8") as ff:
        reference = pystac.Collection.from_dict(json.load(ff)).to_dict()

    assert result == reference


@pytest.mark.vcr("test_cmip6_stac_thredds_catalog_parsing.yaml")
def test_cmip6_stac_thredds_catalog_parsing_with_extra_collection_parser(request):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    sys.path.append(str(request.path.parent / "extra_functions"))
    populator = MockedNoSTACUpload(
        "https://example.com",
        loader,
        extra_collection_parsers=[
            "collection_parsers:update_keywords_args",
            "collection_parsers:update_keywords_kwargs",
            "collection_parsers:update_keywords_vkwargs",
        ],
        extra_parser_arguments={"arg1": "a", "arg2": "b", "kw1": "c", "kw2": "d", "kw3": "e", "kw4": "f"},
    )

    result = populator.create_stac_collection()

    assert result["keywords"][-6:] == ["a", "b", "c", "d", "e", "f"]


@pytest.mark.vcr("test_standalone_stac_item_thredds_via_loader.yaml")
def test_standalone_stac_item_thredds_via_loader():
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    populator = MockedNoSTACUpload("https://example.com", loader)

    with patch("STACpopulator.populators.post_stac_item") as mock:
        populator.ingest()
        for call in mock.mock_calls:
            data = call.args[3]
            assert {str(k) for k in data["access_urls"]} == set(
                {
                    "HTTPServer",
                    "OpenDAP",
                    "NCML",
                    "UDDC",
                    "ISO",
                    "WCS",
                    "WMS",
                    "NetcdfSubsetGrid",
                    "NetcdfSubsetPoint",
                }
            )
            assert data["access_urls"]["WCS"].endswith("?request=GetCapabilities")
            assert data["access_urls"]["WMS"].endswith("?request=GetCapabilities")


@pytest.mark.vcr("test_standalone_stac_item_thredds_via_loader.yaml")
def test_standalone_stac_item_thredds_via_loader_with_extra_item_parser(request):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    sys.path.append(str(request.path.parent / "extra_functions"))
    populator = MockedNoSTACUpload(
        "https://example.com",
        loader,
        extra_item_parsers=[
            "item_parsers:extra_property_args",
            "item_parsers:extra_property_kwargs",
            "item_parsers:extra_property_vkwargs",
        ],
        extra_parser_arguments={
            "args_name": "a",
            "args_value": "b",
            "kwargs_name": "c",
            "kwargs_value": "d",
            "vkwargs_name": "e",
            "vkwargs_value": "f",
        },
    )
    with patch("STACpopulator.populators.post_stac_item") as mock:
        populator.ingest()
        for call in mock.mock_calls:
            data = call.args[3]
            assert data["properties"]["a"] == "b"
            assert data["properties"]["c"] == "d"
            assert data["properties"]["e"] == "f"


@pytest.mark.vcr("test_standalone_stac_item_thredds_via_loader.yaml")
def test_standalone_stac_item_thredds_via_loader_with_extra_item_parsers_from_file(request):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    item_parsers_file = request.path.parent / "extra_functions" / "item_parsers.py"
    populator = MockedNoSTACUpload(
        "https://example.com",
        loader,
        extra_item_parsers=[
            f"{item_parsers_file}:extra_property_args",
            f"{item_parsers_file}:extra_property_kwargs",
            f"{item_parsers_file}:extra_property_vkwargs",
        ],
        extra_parser_arguments={
            "args_name": "a",
            "args_value": "b",
            "kwargs_name": "c",
            "kwargs_value": "d",
            "vkwargs_name": "e",
            "vkwargs_value": "f",
        },
    )
    with patch("STACpopulator.populators.post_stac_item") as mock:
        populator.ingest()
        for call in mock.mock_calls:
            data = call.args[3]
            assert data["properties"]["a"] == "b"
            assert data["properties"]["c"] == "d"
            assert data["properties"]["e"] == "f"


@pytest.mark.parametrize("update_collection", ["none", "extents", "summaries", "all"])
@pytest.mark.parametrize("exclude_summaries", [(), ("ducks"), ("ducks", "another_date")])
@pytest.mark.vcr("test_standalone_stac_item_thredds_via_loader.yaml")
def test_standalone_stac_item_update_collection(update_collection, exclude_summaries):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim/cmip6/catalog.xml"
    loader = THREDDSLoader(url)
    populator = MockedNoSTACUpload(
        "https://example.com",
        loader,
        update_collection=update_collection,
        exclude_summaries=exclude_summaries,
        update=True,
    )

    with patch("STACpopulator.populators.post_stac_item"):
        populator.ingest()
        data = populator._collection
        if update_collection in ("extents", "all"):
            assert data["extent"]["spatial"]["bbox"][0] == [-11, -20, 56, 50]
            assert data["extent"]["temporal"]["interval"][0] == ["1066-05-01", None]
        if update_collection in ("summaries", "all"):
            summaries = {
                "another_date": {"maximum": "2222-04-11", "minimum": "1893-02-18"},
                "ducks": ["Alabio", "Blekinge", "Muscovy", "Rouen"],
            }
            for exclude in exclude_summaries:
                summaries.pop(exclude, None)
            assert data["summaries"] == summaries
        if update_collection in ("extents", "none"):
            assert data["summaries"] == {"needs_summaries_update": ["true"]}
        if update_collection in ("summaries", "none"):
            assert data["extent"]["spatial"]["bbox"][0] == [0, 0, 0, 0]
            assert data["extent"]["temporal"]["interval"][0] == ["2020-01-01T00:00:00Z", None]
