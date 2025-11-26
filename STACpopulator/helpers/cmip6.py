from datetime import datetime
from typing import Any, MutableMapping, Type

import pystac

from STACpopulator.extensions.cmip6 import CMIP6Extension, CMIP6Properties
from STACpopulator.models import AnyGeometry
from STACpopulator.stac_utils import ncattrs_to_bbox, ncattrs_to_geometry


class CMIP6Helper:
    """Helper for CMIP6 data."""

    def __init__(self, attrs: MutableMapping[str, Any], geometry_model: Type[AnyGeometry]) -> None:
        self.attrs = attrs
        self.cmip6_attrs = attrs["attributes"]
        self.cfmeta = attrs["groups"]["CFMetadata"]["attributes"]
        self.geometry_model = geometry_model

    @property
    def uid(self) -> str:
        """Return a unique ID for CMIP6 data item."""
        keys = [
            "activity_id",
            "institution_id",
            "source_id",
            "experiment_id",
            "variant_label",
            "table_id",
            "variable_id",
            "grid_label",
        ]
        name = "_".join(self.cmip6_attrs[k] for k in keys)
        return name

    @property
    def geometry(self) -> AnyGeometry:
        """Return the geometry."""
        return self.geometry_model(**ncattrs_to_geometry(self.attrs))

    @property
    def bbox(self) -> list[float]:
        """Return the bounding box."""
        return ncattrs_to_bbox(self.attrs)

    @property
    def start_datetime(self) -> datetime:
        """Return the beginning of the temporal extent."""
        return self.cfmeta["time_coverage_start"]

    @property
    def end_datetime(self) -> datetime:
        """Return the end of the temporal extent."""
        return self.cfmeta["time_coverage_end"]

    @property
    def properties(self) -> CMIP6Properties:
        """Return properties."""
        props = CMIP6Properties(**self.cmip6_attrs)
        return props

    def stac_item(self) -> pystac.Item:
        """Return a pystac Item."""
        item = pystac.Item(
            id=self.uid,
            geometry=self.geometry.model_dump(),
            bbox=self.bbox,
            properties={
                "start_datetime": self.start_datetime,
                "end_datetime": self.end_datetime,
            },
            datetime=None,
        )
        item_cmip6 = CMIP6Extension.ext(item, add_if_missing=True)
        item_cmip6.apply(self.properties)
        return item
