from typing import Generic, TypeVar, Union, cast

import pystac
from pystac.extensions.base import (
    ExtensionManagementMixin,
    PropertiesExtension,
)
from pydantic import ConfigDict, field_validator, model_validator
from STACpopulator.stac_utils import ServiceType, magpie_resource_link, ncattrs_to_bbox, ncattrs_to_geometry
from STACpopulator.extensions.base import Helper, BaseSTAC
from STACpopulator.extensions.datacube import DataCubeHelper

T = TypeVar("T", pystac.Collection, pystac.Item)


class THREDDSMetadata:
    media_types = {
        ServiceType.httpserver: "application/x-netcdf",
        ServiceType.opendap: pystac.MediaType.HTML,
        ServiceType.wcs: pystac.MediaType.XML,
        ServiceType.wms: pystac.MediaType.XML,
        ServiceType.netcdfsubset: "application/x-netcdf",
    }

    asset_roles = {
        ServiceType.httpserver: ["data"],
        ServiceType.opendap: ["data"],
        ServiceType.wcs: ["data"],
        ServiceType.wms: ["visual"],
        ServiceType.netcdfsubset: ["data"],
    }
    service_type: ServiceType


class THREDDSExtension(
    Generic[T],
    PropertiesExtension,
    ExtensionManagementMixin[Union[pystac.Item, pystac.Collection]],
    THREDDSMetadata,
):
    def __init__(self, obj: Union[pystac.Item, pystac.Collection]):
        self.obj = obj

    def apply(
        self,
        services: list["THREDDSService"],
        links: list[pystac.Link],
    ):
        for svc in services:
            key = svc.service_type.value
            self.obj.add_asset(key, svc.get_asset())
        for link in links:
            self.obj.add_link(link)

    @classmethod
    def get_schema_uri(cls) -> str:
        return ""

    @classmethod
    def ext(cls, obj: T, add_if_missing: bool = False) -> "THREDDSExtension[T]":
        """Extends the given STAC Object with properties from the
        :stac-ext:`THREDDS Extension <thredds>`.

        This extension can be applied to instances of :class:`~pystac.Item` or
        :class:`~pystac.Asset`.

        Raises:

            pystac.ExtensionTypeError : If an invalid object type is passed.
        """
        if isinstance(obj, pystac.Collection):
            return cast(THREDDSExtension[T], CollectionTHREDDSExtension(obj))
        elif isinstance(obj, pystac.Item):
            return cast(THREDDSExtension[T], ItemTHREDDSExtension(obj))
        else:
            raise pystac.ExtensionTypeError(cls._ext_error_message(obj))


class THREDDSService(THREDDSMetadata):
    def __init__(self, service_type: ServiceType, href: str):
        self.service_type = service_type
        self.href = href

    def get_asset(self) -> pystac.Asset:
        asset = pystac.Asset(
            href=self.href,
            media_type=str(self.media_types.get(self.service_type) or ""),
            roles=self.asset_roles.get(self.service_type) or [],
        )
        return asset


class ItemTHREDDSExtension(THREDDSExtension[pystac.Item]):
    item: pystac.Item
    """The :class:`~pystac.Item` being extended."""

    def __init__(self, item: pystac.Item):
        self.item = item
        self.properties = item.properties
        super().__init__(self.item)

    def __repr__(self) -> str:
        return f"<ItemTHREDDSExtension Item id={self.item.id}>"


class CollectionTHREDDSExtension(THREDDSExtension[pystac.Item]):

    def __init__(self, collection: pystac.Collection):
        super().__init__(collection)

    def __repr__(self) -> str:
        return f"<CollectionTHREDDSExtension Collection id={self.obj.id}>"


class THREDDSHelper(Helper):
    def __init__(self, access_urls: dict[str, str]):
        self.access_urls = {
            ServiceType.from_value(svc): url
            for svc, url in access_urls.items()
        }

    @property
    def services(self) -> list[THREDDSService]:
        return [
            THREDDSService(
                service_type=svc_type,
                href=href,
            )
            for svc_type, href in self.access_urls.items()
        ]

    @property
    def links(self) -> list[pystac.Link]:
        url = self.access_urls[ServiceType.httpserver]
        link = magpie_resource_link(url)
        return [link]

    def apply(self, item, add_if_missing:bool = False):
        """Apply the THREDDS extension to an item."""
        ext = THREDDSExtension.ext(item, add_if_missing=add_if_missing)
        ext.apply(services=self.services, links=self.links)
        return item


class THREDDSCatalogDataModel(BaseSTAC):
    """Base class ingesting attributes loaded by `THREDDSLoader` and creating a STAC item.

    This is meant to be subclassed for each extension.

    It includes two validation mechanisms:
     - pydantic validation using type hints, and
     - json schema validation.
    """
    # Data from loader
    data: dict

    # Extensions classes
    datacube: DataCubeHelper
    thredds: THREDDSHelper

    model_config = ConfigDict(populate_by_name=True, extra="ignore", arbitrary_types_allowed=True)

    @classmethod
    def from_data(cls, data):
        """Instantiate class from data provided by THREDDS Loader.
        """
        # This is where we match the Loader's output to the STAC item and extensions inputs. If we had multiple
        # loaders, that's probably the only thing that would be different between them.
        return cls(data=data,
                   start_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_start"],
                   end_datetime=data["groups"]["CFMetadata"]["attributes"]["time_coverage_end"],
                   geometry=ncattrs_to_geometry(data),
                   bbox=ncattrs_to_bbox(data),
                   )

    @model_validator(mode="before")
    @classmethod
    def datacube_helper(cls, data):
        """Instantiate the DataCubeHelper."""
        data["datacube"] = DataCubeHelper(data['data'])
        return data

    @model_validator(mode="before")
    @classmethod
    def thredds_helper(cls, data):
        """Instantiate the THREDDSHelper."""
        data["thredds"] = THREDDSHelper(data['data']["access_urls"])
        return data


# TODO: Validate services links exist ?
# @field_validator("access_urls")
# @classmethod
# def validate_access_urls(cls, value):
#     assert len(set(["HTTPServer", "OPENDAP"]).intersection(value.keys())) >= 1, (
#         "Access URLs must include HTTPServer or OPENDAP keys.")
#     return value
