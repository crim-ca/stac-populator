import pytest
from STACpopulator.stac_utils import thredds_catalog_attrs, ncattrs

TEST_NC_URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6"
                            "/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc",
                "https://psl.noaa.gov/thredds/catalog/Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/catalog.html?dataset=Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/air.2m.mon.mean.nc"]

TEST_CATALOG_URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6/catalog.xml"]



@pytest.mark.parametrize("url", TEST_CATALOG_URLS)
@pytest.mark.online
def test_thredds_catalog_attrs(url):
    attrs = thredds_catalog_attrs(url)
    assert "service" in attrs["catalog"]
    assert "dataset" in attrs["catalog"]
    assert isinstance(attrs["catalog"]["service"]["service"], list)


@pytest.mark.parametrize("url", TEST_NC_URLS)
@pytest.mark.online
def test_ncattrs(url):
    url = "https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc"
    attrs = ncattrs(url)
    assert "access_urls" in attrs
    assert "attributes" in attrs
