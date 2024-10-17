from STACpopulator.extensions.cordex6 import Cordex6DataModel


def get_first_item_attrs(url):
    import requests
    from siphon.catalog import TDSCatalog
    import xncml
    from STACpopulator.stac_utils import numpy_to_python_datatypes

    cat = TDSCatalog(url)

    if cat.datasets.items():
        for item_name, ds in cat.datasets.items():
            r = requests.get(ds.access_urls["NCML"])
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
            attrs["access_urls"] = ds.access_urls
            return attrs


def test_item_raw():
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/disk2/ouranos/CORDEX/CMIP6/DD/NAM-12/OURANOS/MPI-ESM1-2-LR/ssp370/r1i1p1f1/CRCM5/v1-r1/day/tas/v20231208/catalog.html"
    attrs = get_first_item_attrs(url)
    model = Cordex6DataModel.from_data(attrs)
    item = model.stac_item()

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["properties"]["xscen:type"] == "simulation"


def test_item_ncml():
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations/RCM-CMIP6/CORDEX/NAM-12/day/catalog.html"

    attrs = get_first_item_attrs(url)
    model = Cordex6DataModel.from_data(attrs)
    item = model.stac_item()

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["properties"]["xscen:type"] == "simulation"
