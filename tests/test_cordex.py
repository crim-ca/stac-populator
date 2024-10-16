from STACpopulator.extensions.cordex6 import Cordex6DataModel


def get_test_data():
    import requests
    from siphon.catalog import TDSCatalog
    import xncml
    from STACpopulator.stac_utils import numpy_to_python_datatypes

    cat = TDSCatalog("https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/disk2/ouranos/CORDEX/CMIP6/DD/NAM-12/OURANOS/MPI-ESM1-2-LR/ssp370/r1i1p1f1/CRCM5/v1-r1/day/tas/v20231208/catalog.html")

    if cat.datasets.items():
        for item_name, ds in cat.datasets.items():
            url = ds.access_urls["NCML"]
            r = requests.get(url)
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["attributes"] = numpy_to_python_datatypes(attrs["attributes"])
            attrs["access_urls"] = ds.access_urls
            return attrs

def test_item():
    attrs = get_test_data()
    model = Cordex6DataModel.from_data(attrs)
    item = model.stac_item()

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["properties"]["xscen:type"] == "simulation"

