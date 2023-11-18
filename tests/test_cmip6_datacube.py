import pystac
import xncml
from pathlib import Path
from pystac.validation import validate_dict

from STACpopulator.extensions.datacube import DataCubeHelper
from STACpopulator.extensions.cmip6 import CMIP6Helper
from pystac.extensions.datacube import DatacubeExtension
from STACpopulator.models import GeoJSONPolygon

DIR = Path(__file__).parent


def test_datacube_helper():
    # Create item
    file_path = DIR / "data" / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml"
    ds = xncml.Dataset(filepath=str(file_path))
    attrs = ds.to_cf_dict()
    attrs["access_urls"] = {"HTTPServer": "http://example.com"}
    item = CMIP6Helper(attrs, GeoJSONPolygon).stac_item()

    # Add extension
    dc = DataCubeHelper(attrs)
    dc_ext = DatacubeExtension.ext(item, add_if_missing=True)
    dc_ext.apply(dimensions=dc.dimensions, variables=dc.variables)

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