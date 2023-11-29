import xncml
from pathlib import Path
from STACpopulator.implementations.CMIP6_UofT.extensions import DataCubeHelper
from pystac.extensions.datacube import DatacubeExtension
from STACpopulator.stac_utils import STAC_item_from_metadata
from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import CMIP6ItemProperties
from STACpopulator.models import GeoJSONPolygon

DIR = Path(__file__).parent


def test_datacube_helper():
    # Create item
    ds = xncml.Dataset(filepath=DIR / "data" / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml")
    attrs = ds.to_cf_dict()
    attrs["access_urls"] = {"HTTPServer": "http://example.com"}
    item = STAC_item_from_metadata("test", attrs, CMIP6ItemProperties, GeoJSONPolygon)

    # Add extension
    dc = DataCubeHelper(attrs)
    dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
    dc_ext.apply(dimensions=dc.dimensions, variables=dc.variables)

    schemas = item.validate()
    assert len(schemas) >= 2
    assert "item.json" in schemas[0]
    assert "datacube" in schemas[1]
