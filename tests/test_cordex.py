from STACpopulator.extensions.cordex6 import Cordex6DataModel, Cordex6DataModelNcML
import json


def test_item_raw():
    attrs = json.load(open("tests/data/cordex6_raw.json"))
    model = Cordex6DataModel.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"cordex6", "thredds", "datacube"}

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["id"].startswith("DD_")


def test_item_ncml():
    attrs = json.load(open("tests/data/cordex6_ncml.json"))
    model = Cordex6DataModelNcML.from_data(attrs)
    item = model.stac_item()
    assert set(model._helpers) == {"cordex6", "thredds", "datacube", "xscen"}

    assert item["properties"]["cordex6:activity_id"] == "DD"
    assert item["properties"]["cordex6:project_id"] == "CORDEX"
    assert item["properties"]["xscen:type"] == "simulation"
