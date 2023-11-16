import xncml
from pathlib import Path
from STACpopulator.implementations.CMIP6_UofT.extensions import DataCubeHelper
from pystac.extensions.datacube import DatacubeExtension
from STACpopulator.stac_utils import STAC_item_from_metadata
from STACpopulator.implementations.CMIP6_UofT.add_CMIP6 import CMIP6ItemProperties
from STACpopulator.models import GeoJSONPolygon
from pystac import Item
from pystac.validation.stac_validator import JsonSchemaSTACValidator

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

    # Get schema for version of datacube extension used
    ext_version = item.stac_extensions[0].split("/")[-2]

    # Try to find the schema locally, otherwise it will be fetched from the net.
    schema_uri = DIR / "schemas" / "datacube" / f"{ext_version}.json"
    if not schema_uri.exists():
        schema_uri = item.stac_extensions[0]

    # Validate
    val = JsonSchemaSTACValidator()
    val.validate_extension(stac_dict=item.to_dict(),
                           stac_object_type=Item,
                           stac_version="1.0",
                           extension_id=schema_uri)

