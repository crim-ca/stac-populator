"""HRPDS Extension Module."""

from typing import (
    Literal,
    TypeVar,
    get_args,
)

import pystac
from pydantic import ConfigDict
from pystac.extensions import item_assets

from STACpopulator.extensions.rdps import RDPSHelper, RDPSProperties

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset, item_assets.AssetDefinition)

SchemaName = Literal["hrdps"]
SCHEMA_URI: str = "STACpopulator/extensions/schemas/rdps/hrdps-global-attrs-schema.json"  # FIXME: To be defined
PREFIX = f"{get_args(SchemaName)[0]}:"


def add_ext_prefix(name: str) -> str:
    """Return the given name prefixed with this extension's prefix."""
    return PREFIX + name if "datetime" not in name else name


class HRDPSProperties(RDPSProperties, validate_assignment=True):
    """Data model for HRDPS."""

    product: str

    Remarks: str

    License: str

    _prefix = "hrdps"

    model_config = ConfigDict(alias_generator=add_ext_prefix, populate_by_name=True, extra="ignore")


class HRDPSHelper(RDPSHelper):
    """Helper for HRDPS data."""

    @property
    def properties(self) -> HRDPSProperties:
        """Return properties."""
        props = HRDPSProperties(**self.rdps_attrs)
        return props
