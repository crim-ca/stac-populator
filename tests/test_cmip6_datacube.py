from pathlib import Path

import pystac
import pytest
import xncml
from pystac.extensions.datacube import DatacubeExtension
from pystac.validation import validate_dict

from STACpopulator.extensions.cmip6 import CMIP6Helper
from STACpopulator.extensions.datacube import DataCubeHelper

DIR = Path(__file__).parent


def apply_attrs(xml: str):
    # create item
    file_path = DIR / "data" / xml
    ds = xncml.Dataset(filepath=str(file_path))
    attrs = ds.to_cf_dict()
    attrs["access_urls"] = {"HTTPServer": "http://example.com"}
    item = CMIP6Helper(attrs).stac_item()

    # Add extension
    dc = DataCubeHelper(attrs)
    dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
    dc_ext.apply(dimensions=dc.dimensions, variables=dc.variables)

    return item, dc_ext


@pytest.mark.vcr("test_datacube_helper.yaml")
@pytest.mark.parametrize(
    "xml",
    (
        "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml",
        "huss_Amon_TaiESM1_historical_r1i1p1f1_gn_185001-201412.xml",
    ),
)
def test_datacube_helper(xml):
    # Create item
    item, _dc_ext = apply_attrs(xml)

    # same thing as 'item.validate()' but omit the missing CMIP6 that is not official
    schemas = validate_dict(
        stac_dict=item.to_dict(),
        stac_object_type=item.STAC_OBJECT_TYPE,
        stac_version=pystac.get_stac_version(),
        extensions=[DatacubeExtension.get_schema_uri()],
        href=item.get_self_href(),
    )
    assert len(schemas) >= 2
    assert "item.json" in schemas[0]
    assert "datacube" in schemas[1]


def test_dimensions():
    _item, dc_ext = apply_attrs("huss_Amon_TaiESM1_historical_r1i1p1f1_gn_185001-201412.xml")

    assert dc_ext.properties["cube:dimensions"] == {
        "height": {
            "axis": "z",
            "description": "air_pressure",
            "extent": (
                2.0,
                2.0,
            ),
            "type": "spatial",
        },
        "lat": {
            "axis": "y",
            "description": "projection_y_coordinate",
            "extent": (
                -90.0,
                90.0,
            ),
            "type": "spatial",
        },
        "lon": {
            "axis": "x",
            "description": "projection_x_coordinate",
            "extent": (
                0.0,
                358.75,
            ),
            "type": "spatial",
        },
        "time": {
            "description": "time",
            "extent": [
                "1848-10-23T12:00:00Z",
                "2013-08-13T12:00:00Z",
            ],
            "type": "temporal",
        },
    }


def test_auxiliary_variables():
    # https://github.com/crim-ca/stac-populator/issues/52

    _item, dc_ext = apply_attrs("clt_Amon_EC-Earth3_historical_r2i1p1f1_gr_185001-201412.xml")

    p = dc_ext.properties
    assert set(["time", "lat", "lon"]) == set(p["cube:dimensions"].keys())
    assert p["cube:variables"]["lon_bnds"]["unit"] == "degrees_east"
    assert p["cube:variables"]["time_bnds"]["unit"] == "days since 1850-01-01"
    assert p["cube:variables"]["time_bnds"]["type"] == "auxiliary"
    assert p["cube:variables"]["time_bnds"]["description"] == "bounds for the time coordinate"
    assert p["cube:variables"]["clt"]["type"] == "data"
