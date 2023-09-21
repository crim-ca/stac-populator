import re
import datetime as dt
from enum import Enum
from typing import Any, Iterator, MutableMapping, Optional, Tuple
import pystac
from pystac.extensions.datacube import Dimension, DimensionType, VariableType, Variable, DatacubeExtension
from pydantic import BaseModel


def url_validate(target: str) -> bool:
    """Validate whether a supplied URL is reliably written.

    Parameters
    ----------
    target : str

    References
    ----------
    https://stackoverflow.com/a/7160778/7322852
    """
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        # domain...
        r"(?:(?:[A-Z\d](?:[A-Z\d-]{0,61}[A-Z\d])?\.)+(?:[A-Z]{2,6}\.?|[A-Z\d-]{2,}\.?)|"
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return True if re.match(url_regex, target) else False


def collection2enum(collection):
    """Create Enum based on terms from pyessv collection.

    Parameters
    ----------
    collection : pyessv.model.collection.Collection
      pyessv collection of terms.

    Returns
    -------
    Enum
      Enum storing terms and their labels from collection.
    """
    mp = {term.name: term.label for term in collection}
    return Enum(collection.raw_name.capitalize(), mp, module="base")


def collection2literal(collection):
    import typing
    terms = tuple(term.label for term in collection)
    return typing.Literal[terms]


class STACItem(BaseModel):
    start_datetime: dt.datetime
    end_datetime: dt.datetime


class CFJsonItem:
    """Return STAC Item from CF JSON metadata, as provided by `xncml.Dataset.to_cf_dict`."""
    def __init__(self, iid: str, attrs: dict, datamodel=None):
        self.attrs = attrs

        # Global attributes
        gattrs = attrs["attributes"]

        # Validate using pydantic data model if given
        if datamodel:
            props = datamodel(**gattrs).model_dump()
        else:
            props = gattrs

        # Create STAC item
        itemd = dict(
            id=iid,
            geometry=self.ncattrs_to_geometry(),
            bbox=self.ncattrs_to_bbox(),
            properties=props,
            datetime=None,
        )

        cfmeta = attrs["groups"]["CFMetadata"]["attributes"]
        itemd.update(STACItem(start_datetime=cfmeta["time_coverage_start"],
            end_datetime=cfmeta["time_coverage_end"],).model_dump())

        item = pystac.Item(**itemd)

        # Add assets
        for name, url in attrs["access_urls"].items():
            asset = pystac.Asset(href=url, media_type=media_types.get(name, None))
            item.add_asset(name, asset)

        self.item = item

    def ncattrs_to_geometry(self) -> MutableMapping[str, Any]:
        """Create Polygon geometry from CFMetadata."""
        attrs = self.attrs["groups"]["CFMetadata"]["attributes"]
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [
                        float(attrs["geospatial_lon_min"][0]),
                        float(attrs["geospatial_lat_min"][0]),
                    ],
                    [
                        float(attrs["geospatial_lon_min"][0]),
                        float(attrs["geospatial_lat_max"][0]),
                    ],
                    [
                        float(attrs["geospatial_lon_max"][0]),
                        float(attrs["geospatial_lat_max"][0]),
                    ],
                    [
                        float(attrs["geospatial_lon_max"][0]),
                        float(attrs["geospatial_lat_min"][0]),
                    ],
                    [
                        float(attrs["geospatial_lon_min"][0]),
                        float(attrs["geospatial_lat_min"][0]),
                    ],
                ]
            ],
        }

    def ncattrs_to_bbox(self) -> list:
        """Create BBOX from CFMetadata."""
        attrs = self.attrs["groups"]["CFMetadata"]["attributes"]
        return [
            float(attrs["geospatial_lon_min"][0]),
            float(attrs["geospatial_lat_min"][0]),
            float(attrs["geospatial_lon_max"][0]),
            float(attrs["geospatial_lat_max"][0]),
        ]


class DatacubeExt:
    """Extend STAC Item with Datacube properties."""
    axis = {"X": "x", "Y": "y", "Z": "z", "T": "t", "longitude": "x", "latitude": "y", "vertical": "z", "time": "t"}

    def __init__(self, obj: CFJsonItem):
        self.obj = obj
        self.attrs = obj.attrs

        self.ext = DatacubeExtension.ext(self.obj.item, add_if_missing=True)
        self.ext.apply(dimensions=self.dimensions(), variables=self.variables())

    def dimensions(self) -> dict:
        """Return Dimension objects."""

        dims = {}
        for name, length in self.attrs["dimensions"].items():
            v = self.attrs["variables"][name]
            bbox = self.obj.ncattrs_to_bbox()

            for key, criteria in coordinate_criteria.items():
                for criterion, expected in criteria.items():
                    if v['attributes'].get(criterion, None) in expected:
                        axis = self.axis[key]
                        type_ = DimensionType.SPATIAL if axis in ['x', 'y', 'z'] else DimensionType.TEMPORAL

                        if v['type'] == 'int':
                            extent = [0, int(length)]
                        else:  # Not clear the logic is sound
                            if key == 'X':
                                extent = bbox[0], bbox[2]
                            elif key == "Y":
                                extent = bbox[1], bbox[3]
                            else:
                                extent = None

                        dims[name] = Dimension(properties=dict(
                            axis = axis,
                            type = type_,
                            extent = extent,
                            description=v.get("description", v.get("long_name", criteria["standard_name"]))
                            )
                        )

            return dims

    def is_coordinate(self, attrs: dict)-> bool:
        """Return whether variable is a coordinate."""
        for key, criteria in coordinate_criteria.items():
            for criterion, expected in criteria.items():
                if attrs.get(criterion, None) in expected:
                    return True
        return False

    def variables(self)->dict:
        """Return Variable objects"""
        variables = {}

        for name, attrs in self.attrs["variables"].items():
            if name in self.attrs["dimensions"]:
                continue

            variables[name] = Variable(properties=dict(
                    dimensions=attrs["shape"],
                    type = VariableType.AUXILIARY.value if self.is_coordinate(attrs) else VariableType.DATA.value,
                    description=attrs.get("description", attrs.get("long_name", None)),
                    unit=attrs.get("units", None)
                ))
        return variables



# From CF-Xarray
coordinate_criteria = {
    'latitude': {'standard_name': ('latitude',),
  'units': ('degree_north',
   'degree_N',
   'degreeN',
   'degrees_north',
   'degrees_N',
   'degreesN'),
  '_CoordinateAxisType': ('Lat',),
  'long_name': ('latitude',)},
 'longitude': {'standard_name': ('longitude',),
  'units': ('degree_east',
   'degree_E',
   'degreeE',
   'degrees_east',
   'degrees_E',
   'degreesE'),
  '_CoordinateAxisType': ('Lon',),
  'long_name': ('longitude',)},
 'Z': {'standard_name': ('model_level_number',
   'atmosphere_ln_pressure_coordinate',
   'atmosphere_sigma_coordinate',
   'atmosphere_hybrid_sigma_pressure_coordinate',
   'atmosphere_hybrid_height_coordinate',
   'atmosphere_sleve_coordinate',
   'ocean_sigma_coordinate',
   'ocean_s_coordinate',
   'ocean_s_coordinate_g1',
   'ocean_s_coordinate_g2',
   'ocean_sigma_z_coordinate',
   'ocean_double_sigma_coordinate'),
  '_CoordinateAxisType': ('GeoZ', 'Height', 'Pressure'),
  'axis': ('Z',),
  'cartesian_axis': ('Z',),
  'grads_dim': ('z',),
  'long_name': ('model_level_number',
   'atmosphere_ln_pressure_coordinate',
   'atmosphere_sigma_coordinate',
   'atmosphere_hybrid_sigma_pressure_coordinate',
   'atmosphere_hybrid_height_coordinate',
   'atmosphere_sleve_coordinate',
   'ocean_sigma_coordinate',
   'ocean_s_coordinate',
   'ocean_s_coordinate_g1',
   'ocean_s_coordinate_g2',
   'ocean_sigma_z_coordinate',
   'ocean_double_sigma_coordinate')},
 'vertical': {'standard_name': ('air_pressure',
   'height',
   'depth',
   'geopotential_height',
   'altitude',
   'height_above_geopotential_datum',
   'height_above_reference_ellipsoid',
   'height_above_mean_sea_level'),
  'positive': ('up', 'down'),
  'long_name': ('air_pressure',
   'height',
   'depth',
   'geopotential_height',
   'altitude',
   'height_above_geopotential_datum',
   'height_above_reference_ellipsoid',
   'height_above_mean_sea_level')},
 'X': {'standard_name': ('projection_x_coordinate',
   'grid_longitude',
   'projection_x_angular_coordinate'),
  '_CoordinateAxisType': ('GeoX',),
  'axis': ('X',),
  'cartesian_axis': ('X',),
  'grads_dim': ('x',),
  'long_name': ('projection_x_coordinate',
   'grid_longitude',
   'projection_x_angular_coordinate',
   'cell index along first dimension')},
 'Y': {'standard_name': ('projection_y_coordinate',
   'grid_latitude',
   'projection_y_angular_coordinate'),
  '_CoordinateAxisType': ('GeoY',),
  'axis': ('Y',),
  'cartesian_axis': ('Y',),
  'grads_dim': ('y',),
  'long_name': ('projection_y_coordinate',
   'grid_latitude',
   'projection_y_angular_coordinate',
   'cell index along second dimension')},
 'T': {'standard_name': ('time',),
  '_CoordinateAxisType': ('Time',),
  'axis': ('T',),
  'cartesian_axis': ('T',),
  'grads_dim': ('t',),
  'long_name': ('time',)},
 'time': {'standard_name': ('time',),
  '_CoordinateAxisType': ('Time',),
  'axis': ('T',),
  'cartesian_axis': ('T',),
  'grads_dim': ('t',),
  'long_name': ('time',)}}


media_types = {"httpserver_service": "application/x-netcdf",
               "opendap_service": pystac.MediaType.HTML,
               "wcs_service": pystac.MediaType.XML,
               "wms_service": pystac.MediaType.XML,
               "nccs_service": "application/x-netcdf",
               "HTTPServer": "application/x-netcdf",
               "OPENDAP": pystac.MediaType.HTML,
               "NCML": pystac.MediaType.XML,
               "WCS": pystac.MediaType.XML,
               "ISO": pystac.MediaType.XML,
               "WMS": pystac.MediaType.XML,
               "NetcdfSubset": "application/x-netcdf",
               }
