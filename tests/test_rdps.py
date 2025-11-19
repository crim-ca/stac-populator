"""Test RDPS and HRDPS netCDF files."""

import json

from STACpopulator.extensions.hrdps import HRDPSDataModel
from STACpopulator.extensions.rdps import RDPSDataModel


def test_rdps():
    attrs = json.load(open("tests/data/rdps.json"))
    model = RDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assets = item["assets"]
    cf_parameters = item["properties"].get("cf:parameter", [])
    parameter_names = [param["name"] for param in cf_parameters]

    assert set(model._helpers) == {"thredds", "datacube", "cf", "file"}
    assert item["id"] == "birdhouse__testdata__HRDPS__RDPS_sample__2024010100_000.nc"
    # DataCubeExtension
    assert "cube:variables" in item["properties"]
    assert "TD" in item["properties"]["cube:variables"]
    # CFExtension
    assert any("cf:parameter" in asset for asset in assets.values())
    assert "cf:parameter" in item["properties"]
    assert set(["time", "latitude", "longitude"]).issubset(set(parameter_names))
    # FileExtension
    assert any("file:size" in asset for asset in assets.values())


def test_hrdps_sfc():
    attrs = json.load(open("tests/data/hrdps_sfc.json"))
    model = HRDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assets = item["assets"]
    cf_parameters = item["properties"].get("cf:parameter", [])
    parameter_names = [param["name"] for param in cf_parameters]
    # DataCubeExtension
    assert "HRDPS_P_PR_SFC" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}
    # CFExtension
    assert any("cf:parameter" in asset for asset in assets.values())
    assert "cf:parameter" in item["properties"]
    assert set(["time", "latitude", "longitude"]).issubset(set(parameter_names))
    # FileExtension
    assert any("file:size" in asset for asset in assets.values())


def test_hrdps_p_tt():
    attrs = json.load(open("tests/data/hrdps_p_tt.json"))
    model = HRDPSDataModel.from_data(attrs)
    item = model.stac_item()
    assets = item["assets"]
    cf_parameters = item["properties"].get("cf:parameter", [])
    parameter_names = [param["name"] for param in cf_parameters]
    # DataCubeExtension
    assert "HRDPS_P_TT_10000" in item["properties"]["cube:variables"]
    assert item["properties"]["cube:dimensions"].keys() == {"time", "rlat", "rlon"}
    # CFExtension
    assert any("cf:parameter" in asset for asset in assets.values())
    assert "cf:parameter" in item["properties"]
    assert set(["time", "latitude", "longitude"]).issubset(set(parameter_names))
    # FileExtension
    assert any("file:size" in asset for asset in assets.values())
