import urllib.parse
import json
import pytest
import responses
from responses import _recorder
from pathlib import Path
import requests
from STACpopulator.stac_utils import catalog_url, access_urls, ds_attrs
from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import CMIP6ItemProperties, CMIP6populator
from STACpopulator.models import GeoJSONPolygon
from STACpopulator.stac_utils import STAC_item_from_metadata


URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6"
                            "/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc",
            ]
URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6"
                            "/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc",
                "https://psl.noaa.gov/thredds/catalog/Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/catalog.html?dataset=Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/air.2m.mon.mean.nc"]

DATA = Path(__file__).parent / "data"


def reference_path_from_url(url):
    """Return local path to json dict representation of STAC item."""
    catalog_link, nc = catalog_url(url)
    nc = Path(nc)
    parts = catalog_link.split("/")
    return DATA.joinpath("references", parts[-2], nc.with_suffix(".json"))


@_recorder.record(file_path=DATA / "responses.yaml")
def store_responses():
    """Store server responses.

    Run this if new URLs are added, if remote THREDDS servers are updated or their configuration changed.
    """
    for url in URLS:
        # Request to catalog link
        catalog_link, nc = catalog_url(url)
        requests.get(catalog_link)

        # Request to NcML link
        ncml_link = access_urls(catalog_link, nc)["NCML"]
        requests.get(ncml_link)


@responses.activate
def create_reference_items(overwrite=False):
    """Store json representation of STAC item dict created from stored XML responses.

    - Run after store_responses() to update the expected STAC item representation.
    - Run if the STAC item representation changes.
    """
    # Get server responses from files stored on disk
    responses._add_from_file(file_path=DATA / "responses.yaml")

    for url in URLS:
        # Request to catalog link
        catalog_link, nc = catalog_url(url)

        # Request to NcML link
        ncml_link = access_urls(catalog_link, nc)["NcML"]

        reference_path = reference_path_from_url(url)

        if overwrite or not reference_path.exists():
            reference_path.parent.mkdir(parents=True, exist_ok=True)
            attrs = ds_attrs(ncml_link, catalog_link)

            if "cmip6" in url:
                stac_item_id = CMIP6populator.make_cmip6_item_id(attrs["attributes"])
                stac_item = STAC_item_from_metadata(stac_item_id, attrs, CMIP6ItemProperties, GeoJSONPolygon)
                reference_path.write_text(json.dumps(stac_item.to_dict()))
