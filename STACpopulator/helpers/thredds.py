from __future__ import annotations

import pystac

from STACpopulator.extensions.thredds import T, THREDDSExtension, THREDDSService
from STACpopulator.helpers.base import Helper
from STACpopulator.stac_utils import ServiceType, magpie_resource_link


class THREDDSHelper(Helper):
    """Helper for interacting with THREDDS."""

    def __init__(self, access_urls: dict[str, str]) -> None:
        self.access_urls = {ServiceType.from_value(svc): url for svc, url in access_urls.items()}

    @classmethod
    def from_data(
        cls,
        data: dict[str, any],
        **kwargs,
    ) -> THREDDSHelper:
        """Create a THREDDSHelper instance from raw data."""
        return cls(access_urls=data["data"]["access_urls"])

    @property
    def services(self) -> list[THREDDSService]:
        """Return a list of THREDDS services including one for this helper."""
        return [
            THREDDSService(
                service_type=svc_type,
                href=href,
            )
            for svc_type, href in self.access_urls.items()
        ]

    @property
    def links(self) -> list[pystac.Link]:
        """Return a link for this resource."""
        url = self.access_urls[ServiceType.httpserver]
        link = magpie_resource_link(url)
        return [link]

    def apply(self, item: T, add_if_missing: bool = False) -> T:
        """Apply the THREDDS extension to an item."""
        ext = THREDDSExtension.ext(item, add_if_missing=add_if_missing)
        ext.apply(services=self.services, links=self.links)
        return item
