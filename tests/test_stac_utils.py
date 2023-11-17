import pytest
import requests
import responses
from pathlib import Path
from STACpopulator.stac_utils import catalog_url, access_urls
from STACpopulator.stac_utils import thredds_catalog_attrs, ncml_attrs, ds_attrs
from conftest import DATA

TEST_NC_URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6"
                            "/sic_SImon_CCCma-CanESM5_ssp245_r13i1p2f1_2020.nc",
                "https://psl.noaa.gov/thredds/catalog/Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/catalog.html?dataset=Datasets/20thC_ReanV2/Monthlies/gaussian/monolevel/air.2m.mon.mean.nc"]

TEST_CATALOG_URLS = ["https://pavics.ouranos.ca/twitcher/ows/proxy/thredds/birdhouse/testdata/xclim/cmip6/catalog.xml"]



@pytest.mark.parametrize("url", TEST_CATALOG_URLS)
@responses.activate
def test_thredds_catalog_attrs(url):
    responses._add_from_file(file_path=DATA / "responses.yaml")

    attrs = thredds_catalog_attrs(url)
    assert "service" in attrs["catalog"]
    assert "dataset" in attrs["catalog"]
    assert isinstance(attrs["catalog"]["service"]["service"], list)


@pytest.mark.parametrize("url", TEST_NC_URLS)
@responses.activate
def test_catalog_url(url):
    responses._add_from_file(file_path=DATA / "responses.yaml")

    link, ds = catalog_url(url)
    resp = requests.get(link)
    resp.raise_for_status()


@pytest.mark.parametrize("url", TEST_NC_URLS)
@responses.activate
def test_access_urls(url):
    responses._add_from_file(file_path=DATA / "responses.yaml")

    link, ds = catalog_url(url)
    urls = access_urls(link, ds)
    assert "NcML" in urls
    # assert "OPENDAP" in urls
    assert "HTTPServer" in urls


@pytest.mark.parametrize("url", TEST_NC_URLS)
@responses.activate
def test_ncml_attrs(url):
    responses._add_from_file(file_path=DATA / "responses.yaml")

    link, ds = catalog_url(url)
    urls = access_urls(link, ds)
    attrs = ncml_attrs(urls["NcML"])

    assert "attributes" in attrs


@pytest.mark.parametrize("url", TEST_NC_URLS)
@responses.activate
def test_ds_attrs(url):
    responses._add_from_file(file_path=DATA / "responses.yaml")

    attrs = ds_attrs(url)

    assert "attributes" in attrs
    assert "access_urls" in attrs



