import functools

from pystac.extensions.datacube import Dimension, DimensionType, Variable, VariableType

from STACpopulator.stac_utils import ncattrs_to_bbox


class DataCubeHelper:
    """Return STAC Item from CF JSON metadata, as provided by `xncml.Dataset.to_cf_dict`."""

    axis = {"X": "x", "Y": "y", "Z": "z", "T": "t", "longitude": "x", "latitude": "y", "vertical": "z", "time": "t"}

    def __init__(self, attrs: dict):
        """
        Create STAC Item from CF JSON metadata.

        Parameters
        ----------
        iid : str
            Unique item ID.
        attrs: dict
            CF JSON metadata returned by `xncml.Dataset.to_cf_dict`.
        datamodel : pydantic.BaseModel, optional
            Data model for validating global attributes.
        """
        self.attrs = attrs

        # From CF-Xarray
        self.coordinate_criteria = {
            "latitude": {
                "standard_name": ("latitude",),
                "units": ("degree_north", "degree_N", "degreeN", "degrees_north", "degrees_N", "degreesN"),
                "_CoordinateAxisType": ("Lat",),
                "long_name": ("latitude",),
            },
            "longitude": {
                "standard_name": ("longitude",),
                "units": ("degree_east", "degree_E", "degreeE", "degrees_east", "degrees_E", "degreesE"),
                "_CoordinateAxisType": ("Lon",),
                "long_name": ("longitude",),
            },
            "Z": {
                "standard_name": (
                    "model_level_number",
                    "atmosphere_ln_pressure_coordinate",
                    "atmosphere_sigma_coordinate",
                    "atmosphere_hybrid_sigma_pressure_coordinate",
                    "atmosphere_hybrid_height_coordinate",
                    "atmosphere_sleve_coordinate",
                    "ocean_sigma_coordinate",
                    "ocean_s_coordinate",
                    "ocean_s_coordinate_g1",
                    "ocean_s_coordinate_g2",
                    "ocean_sigma_z_coordinate",
                    "ocean_double_sigma_coordinate",
                ),
                "_CoordinateAxisType": ("GeoZ", "Height", "Pressure"),
                "axis": ("Z",),
                "cartesian_axis": ("Z",),
                "grads_dim": ("z",),
                "long_name": (
                    "model_level_number",
                    "atmosphere_ln_pressure_coordinate",
                    "atmosphere_sigma_coordinate",
                    "atmosphere_hybrid_sigma_pressure_coordinate",
                    "atmosphere_hybrid_height_coordinate",
                    "atmosphere_sleve_coordinate",
                    "ocean_sigma_coordinate",
                    "ocean_s_coordinate",
                    "ocean_s_coordinate_g1",
                    "ocean_s_coordinate_g2",
                    "ocean_sigma_z_coordinate",
                    "ocean_double_sigma_coordinate",
                ),
            },
            "vertical": {
                "standard_name": (
                    "air_pressure",
                    "height",
                    "depth",
                    "geopotential_height",
                    "altitude",
                    "height_above_geopotential_datum",
                    "height_above_reference_ellipsoid",
                    "height_above_mean_sea_level",
                ),
                "positive": ("up", "down"),
                "long_name": (
                    "air_pressure",
                    "height",
                    "depth",
                    "geopotential_height",
                    "altitude",
                    "height_above_geopotential_datum",
                    "height_above_reference_ellipsoid",
                    "height_above_mean_sea_level",
                ),
            },
            "X": {
                "standard_name": ("projection_x_coordinate", "grid_longitude", "projection_x_angular_coordinate"),
                "_CoordinateAxisType": ("GeoX",),
                "axis": ("X",),
                "cartesian_axis": ("X",),
                "grads_dim": ("x",),
                "long_name": (
                    "projection_x_coordinate",
                    "grid_longitude",
                    "projection_x_angular_coordinate",
                    "cell index along first dimension",
                ),
            },
            "Y": {
                "standard_name": ("projection_y_coordinate", "grid_latitude", "projection_y_angular_coordinate"),
                "_CoordinateAxisType": ("GeoY",),
                "axis": ("Y",),
                "cartesian_axis": ("Y",),
                "grads_dim": ("y",),
                "long_name": (
                    "projection_y_coordinate",
                    "grid_latitude",
                    "projection_y_angular_coordinate",
                    "cell index along second dimension",
                ),
            },
            "T": {
                "standard_name": ("time",),
                "_CoordinateAxisType": ("Time",),
                "axis": ("T",),
                "cartesian_axis": ("T",),
                "grads_dim": ("t",),
                "long_name": ("time",),
            },
            "time": {
                "standard_name": ("time",),
                "_CoordinateAxisType": ("Time",),
                "axis": ("T",),
                "cartesian_axis": ("T",),
                "grads_dim": ("t",),
                "long_name": ("time",),
            },
        }

    @property
    @functools.cache
    def dimensions(self) -> dict:
        """Return Dimension objects required for Datacube extension."""

        dims = {}
        for name, length in self.attrs["dimensions"].items():
            v = self.attrs["variables"].get(name)
            if v:
                bbox = ncattrs_to_bbox(self.attrs)
                for key, criteria in self.coordinate_criteria.items():
                    for criterion, expected in criteria.items():
                        if v["attributes"].get(criterion, None) in expected:
                            axis = self.axis[key]
                            type_ = DimensionType.SPATIAL if axis in ["x", "y", "z"] else DimensionType.TEMPORAL

                            if v["type"] == "int":
                                extent = [0, int(length)]
                            else:  # Not clear the logic is sound
                                if key == "X":
                                    extent = bbox[0], bbox[2]
                                elif key == "Y":
                                    extent = bbox[1], bbox[3]
                                else:
                                    extent = None

                            dims[name] = Dimension(
                                properties=dict(
                                    axis=axis,
                                    type=type_,
                                    extent=extent,
                                    description=v.get("description", v.get("long_name", criteria["standard_name"])),
                                )
                            )

        return dims

    @property
    @functools.cache
    def variables(self) -> dict:
        """Return Variable objects required for Datacube extension."""
        variables = {}

        for name, meta in self.attrs["variables"].items():
            if name in self.attrs["dimensions"]:
                continue

            attrs = meta["attributes"]
            variables[name] = Variable(
                properties=dict(
                    dimensions=meta["shape"],
                    type=VariableType.AUXILIARY.value if self.is_coordinate(attrs) else VariableType.DATA.value,
                    description=attrs.get("description", attrs.get("long_name")),
                    unit=attrs.get("units", None),
                )
            )
        return variables

    # @property
    # @functools.cache
    def is_coordinate(self, attrs: dict) -> bool:
        """Return whether variable is a coordinate."""
        for key, criteria in self.coordinate_criteria.items():
            for criterion, expected in criteria.items():
                if attrs.get(criterion, None) in expected:
                    return True
        return False
