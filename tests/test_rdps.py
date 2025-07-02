"""Test RDPS and HRDPS netCDF files."""

import json

from STACpopulator.extensions.thredds import THREDDSCatalogDataModel


def test_rdps():
    attrs = json.load(open("tests/data/rdps.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"thredds", "datacube"}
    assert item["id"] == "birdhouse/testdata/HRDPS/RDPS_sample/2024010100_000.nc"
    assert "TD" in item["properties"]["cube:variables"]


def test_hrdps():
    attrs = json.load(open("tests/data/hrdps_sfc.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert "HRDPS_P_PR_SFC" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}

    attrs = json.load(open("tests/data/hrdps_p_tt.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert "HRDPS_P_TT_10000" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}
