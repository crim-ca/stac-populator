"""Test RDPS and HRDPS netCDF files."""

import json

from STACpopulator.extensions.hrdps import HRDPSDataModel
from STACpopulator.extensions.rdps import RDPSDataModel


def test_rdps():
    attrs = json.load(open("tests/data/rdps.json"))
    model = RDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"thredds", "datacube", "cf", "file"}
    assert item["id"] == "birdhouse__testdata__HRDPS__RDPS_sample__2024010100_000.nc"
    assert "TD" in item["properties"]["cube:variables"]


def test_hrdps():
    attrs = json.load(open("tests/data/hrdps_sfc.json"))
    model = HRDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assert "HRDPS_P_PR_SFC" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}

    attrs = json.load(open("tests/data/hrdps_p_tt.json"))
    model = HRDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assert "HRDPS_P_TT_10000" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}
