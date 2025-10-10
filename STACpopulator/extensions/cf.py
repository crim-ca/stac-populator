"""CF Extension Module."""

from __future__ import annotations

import functools
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    cast,
    get_args,
)

import pystac
from pydantic import BaseModel
from pystac.extensions import item_assets
from pystac.extensions.base import ExtensionManagementMixin, PropertiesExtension

from STACpopulator.extensions.base import ExtensionHelper
from STACpopulator.stac_utils import ServiceType

T = TypeVar("T", pystac.Collection, pystac.Item, pystac.Asset)
SchemaName = Literal["cf"]
SCHEMA_URI = "https://stac-extensions.github.io/cf/v0.2.0/schema.json"
PREFIX = f"{get_args(SchemaName)[0]}:"
PARAMETER_PROP = PREFIX + "parameter"


class CFParameter(BaseModel):
    """CFParameter."""

    name: str
    unit: Optional[str]

    def __repr__(self) -> str:
        """Return string repr."""
        return f"<CFParameter name={self.name}, unit={self.unit}>"


class CFHelper(ExtensionHelper):
    """CFHelper."""

    _prefix: str = "cf"
    variables: Dict[str, Any]

    @functools.cached_property
    def parameters(self) -> List[CFParameter]:
        """Extracts cf:parameter-like information from item_data."""
        parameters = []

        for _, var in self.variables.items():
            attrs = var.get("attributes", {})
            name = attrs.get("standard_name")  # Get the required standard name
            if not name:
                continue  # Skip if no valid name
            unit = attrs.get("units") or ""
            parameters.append(CFParameter(name=name, unit=unit))

        return parameters

    def apply(self, item: T, add_if_missing: bool = True) -> T:
        """Apply the Datacube extension to an item."""
        ext = CFExtension.ext(item, add_if_missing=add_if_missing)
        ext.apply(parameters=self.parameters)

        # FIXME: This temporary workaround has been added to comply with the (most certainly buggy) validation schema for CF extension
        # It should be remove once the PR is integrated since applying on the item should be enough
        asset = item.assets["HTTPServer"]
        cf_asset_ext = CFExtension.ext(asset, add_if_missing=True)
        cf_asset_ext.apply(parameters=self.parameters)
        return item


class CFExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Asset, pystac.Item, pystac.Collection]],
):
    """CF Metadata Extension."""

    @property
    def name(self) -> SchemaName:
        """Return the schema name."""
        return get_args(SchemaName)[0]

    @property
    def parameter(self) -> List[dict[str, Any]] | None:
        """Get or set the CF parameter(s)."""
        return self._get_property(PARAMETER_PROP, int)

    @parameter.setter
    def parameter(self, v: List[dict[str, Any]] | None) -> None:
        self._set_property(PARAMETER_PROP, v)

    def apply(
        self,
        parameters: Union[List[CFParameter], List[dict[str, Any]]],
    ) -> None:
        """Apply CF Extension properties to the extended :class:`~pystac.Item` or :class:`~pystac.Asset`."""
        if not isinstance(parameters[0], dict):
            parameters = [p.model_dump() for p in parameters]
        self.parameter = parameters

    @classmethod
    def get_schema_uri(cls) -> str:
        """Return this extension's schema URI."""
        return SCHEMA_URI

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> CFExtension[T]:
        """Extend the given STAC Object with properties from the :stac-ext:`CF Extension <cf>`.

        This extension can be applied to instances of :class:`~pystac.Item`, :class:`~pystac.Asset`, or  :class:`~pystac.Collection`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Collection):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(CFExtension[T], CollectionCFExtension(obj))
        elif isinstance(obj, pystac.Item):
            cls.ensure_has_extension(obj, add_if_missing)
            return cast(CFExtension[T], ItemCFExtension(obj))
        elif isinstance(obj, pystac.Asset):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(CFExtension[T], AssetCFExtension(obj))
        elif isinstance(obj, item_assets.AssetDefinition):
            cls.ensure_owner_has_extension(obj, add_if_missing)
            return cast(CFExtension[T], ItemAssetsCFExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


class ItemCFExtension(CFExtension[pystac.Item]):
    """
    A concrete implementation of :class:`CFExtension` on an :class:`~pystac.Item`.

    Extends the properties of the Item to include properties defined in the
    :stac-ext:`CF Extension <cf>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`CFExtension.ext` on an :class:`~pystac.Item` to extend it.
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
            if (service_type in ServiceType and service_type.value in asset.extra_fields)
            or any(ServiceType.from_value(field, default=None) is ServiceType for field in asset.extra_fields)
        }

    def __repr__(self) -> str:
        """Return repr."""
        return f"<ItemCFExtension Item id={self.item.id}>"


class ItemAssetsCFExtension(CFExtension[item_assets.AssetDefinition]):
    """Extention for CF item assets."""

    properties: dict[str, Any]
    asset_defn: item_assets.AssetDefinition

    def __init__(self, item_asset: item_assets.AssetDefinition) -> None:
        self.asset_defn = item_asset
        self.properties = item_asset.properties


class AssetCFExtension(CFExtension[pystac.Asset]):
    """
    A concrete implementation of :class:`CFExtension` on an :class:`~pystac.Asset`.

    Extends the Asset fields to include properties defined in the
    :stac-ext:`CF Extension <cf>`.

    This class should generally not be instantiated directly. Instead, call
    :meth:`CFExtension.ext` on an :class:`~pystac.Asset` to extend it.
    """

    asset_href: str
    """The ``href`` value of the :class:`~pystac.Asset` being extended."""

    properties: dict[str, Any]
    """The :class:`~pystac.Asset` fields, including extension properties."""

    additional_read_properties: Optional[Iterable[dict[str, Any]]] = None
    """If present, this will be a list containing 1 dictionary representing the
    properties of the owning :class:`~pystac.Item`."""

    def __init__(self, asset: pystac.Asset) -> None:
        self.asset_href = asset.href
        self.properties = asset.extra_fields
        if asset.owner and isinstance(asset.owner, pystac.Item):
            self.additional_read_properties = [asset.owner.properties]

    def __repr__(self) -> str:
        """Return repr."""
        return f"<AssetCFExtension Asset href={self.asset_href}>"


class CollectionCFExtension(CFExtension[pystac.Collection]):
    """Extension for CF data."""

    def __init__(self, collection: pystac.Collection) -> None:
        self.collection = collection
