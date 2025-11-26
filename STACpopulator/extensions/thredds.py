from __future__ import annotations

from typing import Generic, TypeVar, Union, cast

import pystac
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
)

from STACpopulator.stac_utils import ServiceType

T = TypeVar("T", pystac.Collection, pystac.Item)


class THREDDSMetadata:
    """Metadata for THREDDS objects."""

    media_types = {
        ServiceType.httpserver: "application/x-netcdf",
        ServiceType.opendap: pystac.MediaType.HTML,
        ServiceType.wcs: pystac.MediaType.XML,
        ServiceType.wms: pystac.MediaType.XML,
        ServiceType.netcdfsubset: "application/x-netcdf",  # used in THREDDS version < 5.0
        ServiceType.netcdfsubsetgrid: "application/x-netcdf",  # used in THREDDS version > 5.0
        ServiceType.netcdfsubsetpoint: "application/x-netcdf",  # used in THREDDS version > 5.0
    }

    asset_roles = {
        ServiceType.httpserver: ["data"],
        ServiceType.opendap: ["data"],
        ServiceType.wcs: ["data"],
        ServiceType.wms: ["visual"],
        ServiceType.netcdfsubset: ["data"],  # used in THREDDS version < 5.0
        ServiceType.netcdfsubsetgrid: ["data"],  # used in THREDDS version > 5.0
        ServiceType.netcdfsubsetpoint: ["data"],  # used in THREDDS version > 5.0
    }
    service_type: ServiceType


class THREDDSExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Item, pystac.Collection]],
    THREDDSMetadata,
):
    """Extension for THREDDS objects."""

    def __init__(self, obj: Union[pystac.Item, pystac.Collection]) -> None:
        self.obj = obj

    def apply(
        self,
        services: list["THREDDSService"],
        links: list[pystac.Link],
    ) -> None:
        """Add the values defined by this extension to self.obj."""
        for svc in services:
            key = svc.service_type.value
            self.obj.add_asset(key, svc.get_asset())
        for link in links:
            self.obj.add_link(link)

    @classmethod
    def get_schema_uri(cls) -> str:
        """Return an empty string representing an empty schema URI."""
        return ""

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> THREDDSExtension[T]:
        """Extend the given STAC Object with properties from the :stac-ext:`THREDDS Extension <thredds>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises
        ------
            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Collection):
            return cast(THREDDSExtension[T], CollectionTHREDDSExtension(obj))
        elif isinstance(obj, pystac.Item):
            return cast(THREDDSExtension[T], ItemTHREDDSExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


class THREDDSService(THREDDSMetadata):
    """Extension for the THREDDS service."""

    def __init__(self, service_type: ServiceType, href: str) -> None:
        self.service_type = service_type
        self.href = href

    def get_asset(self) -> pystac.Asset:
        """Return the asset stored at this THREDDS location."""
        asset = pystac.Asset(
            href=self.href,
            media_type=str(self.media_types.get(self.service_type) or ""),
            roles=self.asset_roles.get(self.service_type) or [],
        )
        return asset


class ItemTHREDDSExtension(THREDDSExtension[pystac.Item]):
    """The :class:`~pystac.Item` being extended."""

    item: pystac.Item

    def __init__(self, item: pystac.Item) -> None:
        self.item = item
        self.properties = item.properties
        super().__init__(self.item)

    def __repr__(self) -> str:
        """Return repr."""
        return f"<ItemTHREDDSExtension Item id={self.item.id}>"


class CollectionTHREDDSExtension(THREDDSExtension[pystac.Item]):
    """Extension for THREDDS collections."""

    def __init__(self, collection: pystac.Collection) -> None:
        super().__init__(collection)

    def __repr__(self) -> str:
        """Return repr."""
        return f"<CollectionTHREDDSExtension Collection id={self.obj.id}>"
