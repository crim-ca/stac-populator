"""Test RDPS and HRDPS netCDF files."""
import json
from STACpopulator.extensions.thredds import THREDDSCatalogDataModel

def test_rdps():
    attrs = json.load(open("tests/data/rdps.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"thredds", "datacube"}


def test_hrdps():
    attrs = json.load(open("tests/data/hrdps_sfc.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"thredds", "datacube"}

    attrs = json.load(open("tests/data/hrdps_p_tt.json"))
    model = THREDDSCatalogDataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"thredds", "datacube"}
