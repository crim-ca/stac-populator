from pathlib import Path

import numpy as np
import pytest
import xncml

from STACpopulator.models import GeoJSONMultiPolygon, GeoJSONPolygon
from STACpopulator.stac_utils import GeoData

DIR = Path(__file__).parent


def test_np2py():
    """Test different use cases for np2py."""
    from STACpopulator.stac_utils import np2py

    # Test int
    i = np2py(np.int32(1))
    assert type(i) is int

    # Test float
    f = np2py(np.float32(1.0))
    assert type(f) is float

    # Test str
    s = np2py(np.str_("string"))
    assert type(s) is str

    # Test dict
    d = np2py({"a": np.int32(1), "b": np.float32(2.0)})
    assert d == {"a": 1, "b": 2.0}

    # Test list
    l_ = np2py([np.int32(1), np.float32(2.0)])
    assert l_ == [1, 2.0]

    # Test tuple
    t = np2py((np.int32(1), np.float32(2.0)))
    assert t == (1, 2.0)

    # Test NaNs
    n = np2py(np.float64(np.nan))
    assert type(n) is float

    # Test Infinity
    n = np2py(np.float64(np.inf))
    assert type(n) is float


class TestGeoData:
    class TestValidations:
        def test_already_compliant(self):
            data = GeoData(lon_min=-40, lon_max=140, lat_min=20, lat_max=33, vertical_min=-10, vertical_max=7)
            assert data.lon_min == -40.0
            assert data.lon_max == 140.0
            assert data.lat_min == 20.0
            assert data.lat_max == 33.0
            assert data.vertical_min == -10.0
            assert data.vertical_max == 7.0

        def test_latitude_out_of_range(self):
            with pytest.raises(ValueError):
                GeoData(lon_min=-40, lon_max=140, lat_min=-91, lat_max=33)
            with pytest.raises(ValueError):
                GeoData(lon_min=-40, lon_max=140, lat_min=20, lat_max=91)

        def test_longitude_out_of_range(self):
            with pytest.raises(ValueError):
                GeoData(lon_min=-181, lon_max=140, lat_min=20, lat_max=33)
            with pytest.raises(ValueError):
                GeoData(lon_min=-40, lon_max=361, lat_min=20, lat_max=33)

        def test_longitude_convert_to_wgs84_compliant(self):
            data = GeoData(lon_min=190, lon_max=300, lat_min=20, lat_max=33)
            assert data.lon_min == -170.0
            assert data.lon_max == -60.0

        def test_vertical_inverted_if_down(self):
            data = GeoData(
                lon_min=-40,
                lon_max=140,
                lat_min=20,
                lat_max=33,
                vertical_min=-10,
                vertical_max=7,
                vertical_positive="down",
            )
            assert data.vertical_min == -7
            assert data.vertical_max == 10

    class TestOriginalData:
        def test_original_data_maintained(self):
            org_data = dict(
                lon_min=200,
                lon_max=290,
                lon_units="degrees_east",
                lon_resolution=1.0,
                lat_min=20,
                lat_max=33,
                lat_units="degrees_north",
                lat_resolution=1.25,
                vertical_min=-10,
                vertical_max=7,
                vertical_positive="down",
                vertical_units="m",
                vertical_resolution=3,
            )
            assert GeoData(**org_data).original_data() == org_data

    class TestFromNcattrs:
        @pytest.fixture
        def attrs_w_vert(self):
            file_path = DIR / "data" / "huss_Amon_TaiESM1_historical_r1i1p1f1_gn_185001-201412.xml"
            ds = xncml.Dataset(filepath=str(file_path))
            return ds.to_cf_dict()

        @pytest.fixture
        def attrs_wo_vert(self):
            file_path = DIR / "data" / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml"
            ds = xncml.Dataset(filepath=str(file_path))
            return ds.to_cf_dict()

        def test_with_vertical_data(self, attrs_w_vert):
            data = GeoData.from_ncattrs(attrs_w_vert)
            assert data == GeoData(
                lon_min=0.0,
                lon_max=-1.25,
                lon_resolution=1.25,
                lat_min=-90.0,
                lat_max=90.0,
                lat_resolution=0.9424083769633508,
                vertical_min=2.0,
                vertical_max=2.0,
                vertical_units="m",
                vertical_positive="up",
                vertical_resolution=0.0,
            )

        def test_without_vertical_data(self, attrs_wo_vert):
            data = GeoData.from_ncattrs(attrs_wo_vert)
            assert data == GeoData(
                lon_min=0.049800001084804535,
                lon_max=-0.00506591796875,
                lon_resolution=0.0034359351726440477,
                lat_min=-78.39350128173828,
                lat_max=89.74176788330078,
                lat_resolution=0.0016049720708009724,
                vertical_min=None,
                vertical_max=None,
                vertical_units="m",
                vertical_positive="up",
            )

    class TestHasZ:
        def test_has_z(self):
            data = GeoData(lon_min=-40, lon_max=140, lat_min=20, lat_max=33, vertical_min=-10, vertical_max=7)
            assert data.has_z()

        def test_no_z(self):
            data = GeoData(lon_min=-40, lon_max=140, lat_min=20, lat_max=33)
            assert not data.has_z()

    class TestCrossesAntimeridian:
        def test_crosses(self):
            data = GeoData(lon_min=130, lon_max=30, lat_min=20, lat_max=33)
            assert data.crosses_antimeridian()

        def test_not_crosses(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33)
            assert not data.crosses_antimeridian()

    class TestToBBox:
        def test_2d_no_cross(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33)
            assert data.to_bbox() == [40, 20, 80, 33]

        def test_2d_cross(self):
            data = GeoData(lon_min=130, lon_max=30, lat_min=20, lat_max=33)
            assert data.to_bbox() == [130, 20, 30, 33]

        def test_3d_no_cross(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33, vertical_min=-3, vertical_max=44)
            assert data.to_bbox() == [40, 20, -3, 80, 33, 44]

        def test_3d_cross(self):
            data = GeoData(lon_min=130, lon_max=30, lat_min=20, lat_max=33, vertical_min=-3, vertical_max=44)
            assert data.to_bbox() == [130, 20, -3, 30, 33, 44]

    class TestToGeometry:
        def test_2d_no_cross(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33)
            assert data.to_geometry() == GeoJSONPolygon(
                type="Polygon", coordinates=[[[40.0, 20.0], [40.0, 33.0], [80.0, 33.0], [80.0, 20.0], [40.0, 20.0]]]
            )

        def test_2d_cross(self):
            data = GeoData(lon_min=130, lon_max=30, lat_min=20, lat_max=33)
            assert data.to_geometry() == GeoJSONMultiPolygon(
                type="MultiPolygon",
                coordinates=[
                    [[[130.0, 20.0], [130.0, 33.0], [180.0, 33.0], [180.0, 20.0], [130.0, 20.0]]],
                    [[[-180.0, 20.0], [-180.0, 33.0], [30.0, 33.0], [30.0, 20.0], [-180.0, 20.0]]],
                ],
            )

        def test_3d_different_vertical_min_max(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33, vertical_min=-3, vertical_max=44)
            assert data.to_geometry() == GeoJSONPolygon(
                type="Polygon", coordinates=[[[40.0, 20.0], [40.0, 33.0], [80.0, 33.0], [80.0, 20.0], [40.0, 20.0]]]
            )

        def test_3d_same_vertical_min_max(self):
            data = GeoData(lon_min=40, lon_max=80, lat_min=20, lat_max=33, vertical_min=-3, vertical_max=-3)
            assert data.to_geometry() == GeoJSONPolygon(
                type="Polygon",
                coordinates=[
                    [[40.0, 20.0, -3.0], [40.0, 33.0, -3.0], [80.0, 33.0, -3.0], [80.0, 20.0, -3.0], [40.0, 20.0, -3.0]]
                ],
            )
