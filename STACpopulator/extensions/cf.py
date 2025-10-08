"""CF Extension Module."""

from __future__ import annotations

import functools
from typing import Any, Dict, List, Optional, TypeVar

import pystac
from pystac.extensions import item_assets
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
)
from pystac.item import Item

T = TypeVar("T", pystac.Item, pystac.Asset, item_assets.AssetDefinition)
SCHEMA_URI = "https://stac-extensions.github.io/cf/v0.2.0/schema.json"


class CFParameter:
    """CFParameter."""

    def __init__(self, name: str, unit: Optional[str] = None) -> None:
        if not name:
            raise ValueError("CFParameter name must be non-empty")
        self.name = name
        self.unit = unit

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {"name": self.name}
        if self.unit:
            data["unit"] = self.unit
        return data

    @staticmethod
    def from_dict(d: dict[str, Any]) -> CFParameter:
        """Convert from dictionary."""
        return CFParameter(name=d["name"], unit=d["unit"])

    def __repr__(self) -> str:
        """Return string repr."""
        return f"CFParameter (name={self.name}, unit={self.unit})"


class CFHelper:
    """CFHelper."""

    def __init__(self, variables: dict[str, any]) -> None:
        """Take a STAC item variables to identify CF parameters metadata."""
        self.variables = variables

    @functools.cached_property
    def cf_parameters(self) -> List[CFParameter]:
        """Extracts cf:parameter-like information from item_data."""
        parameters = []

        for _, var in self.variables.items():
            attrs = var.get("attributes", {})
            name = attrs.get("standard_name")  # Get the required standard name
            if not name:
                # Skip if no valid name
                continue

            unit = attrs.get("units")
            parameters.append(CFParameter(name=name, unit=unit))

        return parameters


# -------------------------------
# CF Extension for Items/Assets
# -------------------------------
class CFItemExtension(PropertiesExtension, ExtensionManagementMixin):
    """CFItemExtension."""

    def __init__(self, item: Item) -> None:
        self.item = item
        self.properties = item.properties

    @property
    def cf_parameters(self) -> Optional[List[CFParameter]]:
        """Return the cf parameters list."""
        result = self._get_property("cf:parameter", List[Dict[str, Any]])
        return [CFParameter.from_dict(v) for v in result]

    @cf_parameters.setter
    def cf_parameters(self, value: List[CFParameter]) -> None:
        """Set the cf parameters list."""
        self._set_property("cf:parameter", [p.to_dict() for p in value])

    def apply(self, parameters: List[CFParameter], apply_to_properties: bool = True) -> None:
        """Add cf:parameter array to assets (requirement) and optionally to item properties (informative)."""
        if not self.item.assets:
            return  # FIXME: Raise that THREDDSExtension should be called before to populate assets.

        # FIXME: This is temporary fix to validate the item. Normally, add cf:parameter to properties should be enough.
        asset = self.item.assets["HTTPServer"]
        if "stac_extensions" not in asset.extra_fields:
            asset.extra_fields["stac_extensions"] = []
        if SCHEMA_URI not in asset.extra_fields["stac_extensions"]:
            asset.extra_fields["stac_extensions"].append(SCHEMA_URI)
        # Add cf:parameter array to asset extra_fields
        asset.extra_fields["cf:parameter"] = [p.to_dict() for p in parameters]

        if apply_to_properties:
            self.cf_parameters = parameters

    @classmethod
    def ext(cls, item: Item, add_if_missing: bool = False) -> CFItemExtension:  # FIXME: Use a generic type
        """Extend the given STAC Object with properties from the :stac-ext:`CF Extension <cf>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        cls.ensure_has_extension(item, add_if_missing)
        return cls(item)

    @classmethod
    def get_schema_uri(cls) -> str:
        """Return this extension's schema URI."""
        return SCHEMA_URI
