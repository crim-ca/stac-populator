from pathlib import Path
from unittest.mock import patch

import numpy as np
import pyproj
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
    @pytest.fixture
    def basic_data(self):
        return {
            "x": [10, 20],
            "y": [30, 40],
            "z": [-10, 12],
            "x_resolution": 1.3,
            "y_resolution": 0.22,
            "z_resolution": 1,
            "crs": pyproj.CRS(4979),
        }

    class TestValidations:
        def test_create_crs_epsg_code(self, basic_data):
            GeoData(**{**basic_data, "crs": 4326})

        def test_create_crs_wkt(self, basic_data, epsg4979_0_360_wkt):
            GeoData(**{**basic_data, "crs": epsg4979_0_360_wkt})

    class TestProperties:
        @pytest.fixture
        def geo_with_different_units(self, basic_data):
            wkt = (
                pyproj.CRS(4979)
                .to_wkt()
                .replace('north,ORDER[1],ANGLEUNIT["degree"', 'north,ORDER[1],ANGLEUNIT["north_degree"')
                .replace('east,ORDER[2],ANGLEUNIT["degree"', 'north,ORDER[2],ANGLEUNIT["east_degree"')
                .replace('LENGTHUNIT["metre"', 'LENGTHUNIT["up_metre"')
                .replace(',ID["EPSG",4979]', "")
            )
            return GeoData(**{**basic_data, "crs": pyproj.CRS(wkt)})

        def test_x_units(self, geo_with_different_units):
            assert geo_with_different_units.x_units == "north_degree"

        def test_y_units(self, geo_with_different_units):
            assert geo_with_different_units.y_units == "east_degree"

        def test_z_units(self, geo_with_different_units):
            assert geo_with_different_units.z_units == "up_metre"

    class TestXIsLongitude:
        @pytest.fixture
        def crs_json(self):
            json_dict = pyproj.CRS(4326).to_json_dict()
            json_dict.pop("id")
            return json_dict

        def test_no_match(self, basic_data):
            geo = GeoData(**{**basic_data, "crs": pyproj.CRS(4326)})
            assert not geo.x_is_longitude

        def test_matches_name(self, basic_data, crs_json):
            crs_json["coordinate_system"]["axis"][0]["name"] = "geodetic longitude"
            geo = GeoData(**{**basic_data, "crs": pyproj.CRS(crs_json)})
            assert geo.x_is_longitude

        def test_matches_abbreviation(self, basic_data, crs_json):
            crs_json["coordinate_system"]["axis"][0]["abbreviation"] = "Lon"
            geo = GeoData(**{**basic_data, "crs": pyproj.CRS(crs_json)})
            assert geo.x_is_longitude

        def test_matches_direction(self, basic_data, crs_json):
            crs_json["coordinate_system"]["axis"][0]["direction"] = "east"
            geo = GeoData(**{**basic_data, "crs": pyproj.CRS(crs_json)})
            assert geo.x_is_longitude

        def test_cached(self, basic_data):
            geo = GeoData(**{**basic_data, "crs": pyproj.CRS(4326)})
            val = geo.x_is_longitude
            with patch("re.search") as mock:
                assert geo.x_is_longitude == val
                assert not mock.call_count
            # reset cache
            geo.crs = pyproj.CRS(4326)
            with patch("re.search") as mock:
                geo.x_is_longitude
                assert mock.call_count

    class TestToWGS84:
        def test_no_change(self, basic_data):
            geo = GeoData(**basic_data)
            out = geo.to_wgs84
            assert geo.x == out["lat"]
            assert geo.y == out["lon"]
            assert geo.z == out["vert"]

        def test_from_shifted_longitude(self, basic_data, epsg4979_0_360_wkt):
            geo = GeoData(**{**basic_data, "x": [100, 280], "crs": pyproj.CRS(epsg4979_0_360_wkt)})
            out = geo.to_wgs84
            assert out["lon"] == pytest.approx([100, -80])

        def test_from_cylindrical(self, basic_data):
            geo = GeoData(**{**basic_data, "x": [10044, 33000], "y": [-235544, 909900], "crs": pyproj.CRS(4087)})
            out = geo.to_wgs84
            assert out["lat"] == pytest.approx([-2.1159277528264853, 8.173770770203525])
            assert out["lon"] == pytest.approx([0.09022678713696472, 0.29644404375944206])

        def test_from_NAD83(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [2093070, 2000000], "x": [10436931, 5740845], "crs": pyproj.CRS(3348)})
            out = geo.to_wgs84
            assert out["lat"] == pytest.approx([38.7545891461986, 53.94358296286908])
            assert out["lon"] == pytest.approx([-40.00269171523382, -98.98931749790985])

    class TestFromNcattrs:
        @pytest.fixture
        def attrs_w_vert(self, epsg4979_0_360_wkt):
            file_path = DIR / "data" / "huss_Amon_TaiESM1_historical_r1i1p1f1_gn_185001-201412.xml"
            ds = xncml.Dataset(filepath=str(file_path))
            attrs = ds.to_cf_dict()
            attrs["@stac-populator"] = {"fallback_crs": epsg4979_0_360_wkt}
            return attrs

        @pytest.fixture
        def attrs_wo_vert(self, epsg4979_0_360_wkt):
            file_path = DIR / "data" / "o3_Amon_GFDL-ESM4_historical_r1i1p1f1_gr1_185001-194912.xml"
            ds = xncml.Dataset(filepath=str(file_path))
            attrs = ds.to_cf_dict()
            attrs["@stac-populator"] = {"fallback_crs": epsg4979_0_360_wkt}
            return attrs

        def test_with_vertical_data(self, attrs_w_vert, epsg4979_0_360_wkt):
            data = GeoData.from_ncattrs(attrs_w_vert)
            assert data == GeoData(
                crs=pyproj.CRS(epsg4979_0_360_wkt),
                x=[0.0, 358.75],
                x_resolution=1.25,
                y=[-90.0, 90.0],
                y_resolution=0.9424083769633508,
                z=[2.0, 2.0],
                z_resolution=0.0,
            )

        def test_without_vertical_data(self, attrs_wo_vert, epsg4979_0_360_wkt):
            data = GeoData.from_ncattrs(attrs_wo_vert)
            assert data == GeoData(
                crs=pyproj.CRS(epsg4979_0_360_wkt),
                x=[0.049800001084804535, 359.99493408203125],
                x_resolution=0.0034359351726440477,
                y=[-78.39350128173828, 89.74176788330078],
                y_resolution=0.0016049720708009724,
                z=None,
                z_resolution=None,
            )

    class TestCrossesAntimeridian:
        def test_crosses(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [170, -33]})
            assert geo.crosses_antimeridian()

        def test_not_crosses(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [-33, 170]})
            assert not geo.crosses_antimeridian()

    class TestToBBox:
        def test_2d_no_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [40, 80], "x": [20, 33], "z": None})
            assert geo.to_bbox() == [40, 20, 80, 33]

        def test_2d_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [130, 30], "x": [20, 33], "z": None})
            assert geo.to_bbox() == [130, 20, 30, 33]

        def test_3d_no_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [40, 80], "x": [20, 33], "z": [-3, 44]})
            assert geo.to_bbox() == [40, 20, -3, 80, 33, 44]

        def test_3d_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [130, 30], "x": [20, 33], "z": [-3, 44]})
            assert geo.to_bbox() == [130, 20, -3, 30, 33, 44]

    class TestToGeometry:
        def test_2d_no_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [40, 80], "x": [20, 33], "z": None})
            assert geo.to_geometry() == GeoJSONPolygon(
                type="Polygon", coordinates=[[[40.0, 20.0], [40.0, 33.0], [80.0, 33.0], [80.0, 20.0], [40.0, 20.0]]]
            )

        def test_2d_cross(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [130, 30], "x": [20, 33], "z": None})
            assert geo.to_geometry() == GeoJSONMultiPolygon(
                type="MultiPolygon",
                coordinates=[
                    [[[130.0, 20.0], [130.0, 33.0], [180.0, 33.0], [180.0, 20.0], [130.0, 20.0]]],
                    [[[-180.0, 20.0], [-180.0, 33.0], [30.0, 33.0], [30.0, 20.0], [-180.0, 20.0]]],
                ],
            )

        def test_3d_different_vertical_min_max(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [40, 80], "x": [20, 33], "z": [-3, 44]})
            assert geo.to_geometry() == GeoJSONPolygon(
                type="Polygon", coordinates=[[[40.0, 20.0], [40.0, 33.0], [80.0, 33.0], [80.0, 20.0], [40.0, 20.0]]]
            )

        def test_3d_same_vertical_min_max(self, basic_data):
            geo = GeoData(**{**basic_data, "y": [40, 80], "x": [20, 33], "z": [-3, -3]})
            assert geo.to_geometry() == GeoJSONPolygon(
                type="Polygon",
                coordinates=[
                    [[40.0, 20.0, -3.0], [40.0, 33.0, -3.0], [80.0, 33.0, -3.0], [80.0, 20.0, -3.0], [40.0, 20.0, -3.0]]
                ],
            )
