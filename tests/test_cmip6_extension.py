from STACpopulator.extensions import cmip6
import xncml
from pathlib import Path
from pystac import Item

TEST_DATA = Path(__file__).parent / "data"

def test_extension():
    ds = xncml.Dataset(TEST_DATA / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml")
    attrs = ds.to_cf_dict()
    cfmeta = attrs["groups"]["CFMetadata"]["attributes"]

    item = Item(id="test", start_datetime=cfmeta["time_coverage_start"], end_datetime=cfmeta["time_coverage_end"])

    ext = cmip6.CMIP6Extension.ext(item, add_if_missing=True)
    ext.apply(attrs)


