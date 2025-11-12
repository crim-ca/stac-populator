import json

import requests
import xncml
from siphon.catalog import TDSCatalog

from STACpopulator.stac_utils import np2py

"""
Run this script to fetch metadata attributes from the PAVICS THREDDS catalog.
This avoids making requests to the server during tests.

The results are commited to the repository, so this script only needs to be run when attributes change
or new datasets are added.
"""


def get_first_item_attrs(url):
    cat = TDSCatalog(url)

    if cat.datasets.items():
        for item_name, ds in cat.datasets.items():
            r = requests.get(ds.access_urls["NCML"])
            attrs = xncml.Dataset.from_text(r.text).to_cf_dict()
            attrs["access_urls"] = ds.access_urls
            return np2py(attrs)


def make_test_data():
    """Fetches attribute data from the PAVICS THREDDS catalog and stores it in the data/ directory as a json."""
    # Mapping between test data file names and URLs
    urls = {
        "cordex6_raw.json": "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/disk2/ouranos/CORDEX/CMIP6/DD/NAM-12/OURANOS/MPI-ESM1-2-LR/ssp370/r1i1p1f1/CRCM5/v1-r1/day/tas/v20231208/catalog.html",
        "cordex6_ncml.json": "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/datasets/simulations"
        "/RCM-CMIP6/CORDEX/NAM-12/day/catalog.html",
        "rdps.json": "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/HRDPS"
        "/RDPS_sample/catalog.html",
        "hrdps_sfc.json": "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/HRDPS"
        "/HRDPS_sample/HRDPS_P_PR_SFC/catalog.html",
        "hrdps_p_tt.json": "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/HRDPS/HRDPS_sample/HRDPS_P_TT_10000/catalog.html",
    }

    for filename, url in urls.items():
        attrs = get_first_item_attrs(url)
        with open(filename, "w") as f:
            json.dump(attrs, f, indent=2)


if __name__ == "__main__":
    make_test_data()
    print("Test data files created in the current directory.")
