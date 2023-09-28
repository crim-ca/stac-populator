from STACpopulator.extensions import cmip6
from STACpopulator.stac_utils import CFJsonItem
import xncml
from pathlib import Path
from pystac import Item, validation

TEST_DATA = Path(__file__).parent / "data"

def test_extension():
    ds = xncml.Dataset(TEST_DATA / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml")
    attrs = ds.to_cf_dict()

    item = CFJsonItem("test", attrs).item
    validation.validate(item)

    ext = cmip6.CMIP6Extension.ext(item, add_if_missing=True)
    ext.apply(attrs["attributes"])
    assert "cmip6:realm" in item.properties


