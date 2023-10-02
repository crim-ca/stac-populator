from STACpopulator.extensions import cmip6
from STACpopulator.stac_utils import CFJsonItem
import xncml
from pathlib import Path
from pystac import Item, validation

TEST_DATA = Path(__file__).parent / "data"

def test_extension():
    ds = xncml.Dataset(TEST_DATA / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml")
    attrs = ds.to_cf_dict()

    item = CFJsonItem("test", attrs).item
    validation.validate(item)

    ext = cmip6.CMIP6Extension.ext(item, add_if_missing=True)
    ext.apply(attrs["attributes"])
    assert "cmip6:realm" in item.properties


def test_ingestion():
    """Test STAC item creation and ingestion using the CMIP6 extension."""
    import requests
    import site
    site.addsitedir(".")

    import add_CMIP6

    stac_host = 'http://localhost:8880/stac/'
    thredds_catalog_URL = ('https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/catalog/birdhouse/testdata/xclim'
                           '/cmip6/catalog.xml')
    config_file = 'CMIP6.yml'
    c = add_CMIP6.CMIP6populator(stac_host, thredds_catalog_URL, config_file)
    c.ingest()

    r = requests.get(stac_host + 'collections/CMIP6').json()
    assert r['id'] == 'CMIP6'
    for link in r["links"]:
        if link["rel"] == "source":
            assert link["href"] == thredds_catalog_URL
            assert "thredds:" in link["title"]
            break
    else:
        assert False, "No source link found"

    r = requests.get(stac_host + 'collections/CMIP6/items').json()
    for link in r["features"][0]["links"]:
        if link["rel"] == "source":
            assert "thredds:" in link["title"]
            break
    else:
        assert False, "No source link found"

