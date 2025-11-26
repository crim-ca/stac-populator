"""
Base classes for STAC extensions.

What we have:
  - `Loader`, which returns attributes.
  - An external json schema describing a subset of the attributes returned by the Loader. This schema might preclude
  additional properties, so it cannot be applied wholesale to the Loader's output. (maybe overkill since not a lot of schemas can be found in the wild...)
  - `data model` describing the content we want included in the catalog. It includes a subset of the schema properties,
  as well as additional attributes desired by the catalog admins.

Desiderata:
  - Not having to replicate existing validation logic in the schema
  - Not having to create a modified schema
  - Being able to supplement the schema validation by pydantic validation logic
  - Streamline the creation of new data models (reduce boilerplate, allow subclassing)
  - Developer-friendly validation error messages


How-to:
  - Instructions to create basic datamodel from schema (codegen)



"""

from __future__ import annotations

import logging
import types
from typing import Any, Generic, Optional, Type, TypeVar, Union, cast

import pystac
from pydantic import (
    BaseModel,
    Field,
    create_model,
)
from pystac.extensions import item_assets
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
    S,  # generic pystac.STACObject
)

from STACpopulator.stac_utils import ServiceType

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset, item_assets.AssetDefinition)

LOGGER = logging.getLogger(__name__)


def metacls_extension(name: str, schema_uri: str) -> "Type[MetaExtension]":
    """Create an extension class dynamically from the properties."""
    cls_name = f"{name.upper()}Extension"

    bases = (
        MetaExtension,
        Generic[T],
        PropertiesExtension,
        ExtensionManagementMixin[Union[pystac.Asset, pystac.Item, pystac.Collection]],
    )

    attrs = {"name": name, "schema_uri": schema_uri}
    return types.new_class(name=cls_name, bases=bases, kwds=None, exec_body=lambda ns: ns.update(attrs))


class MetaExtension:
    """Extension metaclass."""

    name: str
    schema_uri: str

    def apply(self, properties: dict[str, Any]) -> None:
        """Apply Extension properties to the extended :class:`~pystac.Item` or :class:`~pystac.Asset`."""
        for prop, val in properties.items():
            self._set_property(prop, val)

    @classmethod
    def get_schema_uri(cls) -> str:
        """We have already validated the JSON schema."""
        return cls.schema_uri

    @classmethod
    def has_extension(cls, obj: S) -> bool:
        """Return True iff the object has an extension for that matches this class' schema URI."""
        ext_uri = cls.get_schema_uri()
        return obj.stac_extensions is not None and any(uri == ext_uri for uri in obj.stac_extensions)

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "Extension[T]":  # noqa: F821
        """Extend the given STAC Object with properties from the :stac-ext:`Extension`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        cls_map = {pystac.Item: MetaItemExtension}

        for key, meta in cls_map.items():
            if isinstance(obj, key):
                # cls.ensure_has_extension(obj, add_if_missing)
                kls = extend_type(key, meta, cls[key])
                return cast(cls[T], kls(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


def extend_type(stac: T, cls: MetaItemExtension, ext: MetaItemExtension[T]) -> Type:
    """Create an extension subclass for different STAC objects.

    Note: This is super confusing... we should come up with some better nomenclature.

    Parameters
    ----------
    stac: pystac.Item, pystac.Asset, pystac.Collection
      The STAC object.
    cls: MetaItemExtension
      The generic extension class for the STAC object.
    ext: MetaExtension[T]
      The meta extension class.
    """
    cls_name = f"{stac.__name__}{ext.__name__}"
    return types.new_class(cls_name, (cls, ext), {}, lambda ns: ns)


class MetaItemExtension:
    """A concrete implementation of :class:`Extension` on an :class:`~pystac.Item`.

    Extends the properties of the Item to include properties defined in the
    :stac-ext:`Extension`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`Extension.ext` on an :class:`~pystac.Item` to extend it.
    """

    def __init__(self, item: pystac.Item) -> None:
        self.item = item
        self.properties = item.properties

    def get_assets(
        self,
        service_type: Optional[ServiceType] = None,
    ) -> dict[str, pystac.Asset]:
        """Get the item's assets where eo:bands are defined.

        Args:
            service_type: If set, filter the assets such that only those with a
                matching :class:`~STACpopulator.stac_utils.ServiceType` are returned.

        Returns
        -------
            Dict[str, Asset]: A dictionary of assets that match ``service_type``
                if set or else all of this item's assets were service types are defined.
        """
        return {
            key: asset
            for key, asset in self.item.get_assets().items()
            if (isinstance(service_type, ServiceType) and service_type.value in asset.extra_fields)
            or any(ServiceType.from_value(field, default=False) for field in asset.extra_fields)
        }

    def __repr__(self) -> str:
        """Return repr."""
        return f"<{self.__class__.__name__} Item id={self.item.id}>"


# TODO: Add the other STAC item meta extensions


def schema_properties(schema: dict) -> list[str]:
    """Return the list of properties described by schema."""
    out = []
    for key, val in schema["properties"].items():
        prefix, name = key.split(":") if ":" in key else (None, key)
        out.append(name)
    return out


def model_from_schema(model_name: str, schema: dict) -> BaseModel:
    """Create pydantic BaseModel from JSON schema."""
    type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
        None: Any,
    }

    fields = {}
    for key, val in schema["properties"].items():
        prefix, name = key.split(":") if ":" in key else (None, key)
        typ = type_map[val.get("type")]
        default = ... if key in schema["required"] else None
        fields[name] = (typ, Field(default, alias=key))
    return create_model(model_name, **fields)
