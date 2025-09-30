import json

import pytest

from STACpopulator.extensions.cordex6 import Cordex6DataModel, Cordex6DataModelNcML


def get_first_item_attrs(url):
    import requests
    import xncml
    from siphon.catalog import TDSCatalog

    from STACpopulator.stac_utils import np2py

    cat = TDSCatalog(url)

    if cat.datasets.items():
        for item_name, ds in cat.datasets.items():
            r = requests.get(ds.access_urls["NCML"])
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["access_urls"] = ds.access_urls
            return np2py(attrs)


def make_test_data():
    """Fetches attribute data from the PAVICS THREDDS catalog and stores it in the data/ directory as a json."""
    # Raw CORDEX data
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/disk2/ouranos/CORDEX/CMIP6/DD/NAM-12/OURANOS/MPI-ESM1-2-LR/ssp370/r1i1p1f1/CRCM5/v1-r1/day/tas/v20231208/catalog.html"
    attrs = get_first_item_attrs(url)
    with open("data/cordex6_raw.json", "w") as f:
        json.dump(attrs, f, indent=2)

    # NcML CORDEX data
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/RCM-CMIP6/CORDEX/NAM-12/day/catalog.html"
    attrs = get_first_item_attrs(url)
    with open("data/cordex6_ncml.json", "w") as f:
        json.dump(attrs, f, indent=2)


@pytest.mark.vcr("test_item_raw.yaml")
def test_item_raw():
    attrs = json.load(open("tests/data/cordex6_raw.json"))
    model = Cordex6DataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"cordex6", "thredds", "datacube"}

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["id"].startswith("DD_")


@pytest.mark.vcr("test_item_raw.yaml")
def test_item_ncml():
    attrs = json.load(open("tests/data/cordex6_ncml.json"))
    model = Cordex6DataModelNcML.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"cordex6", "thredds", "datacube", "xscen"}

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["properties"]["xscen:type"] == "simulation"
