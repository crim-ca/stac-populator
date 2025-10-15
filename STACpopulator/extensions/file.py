"""FileHelper module."""

import functools
from typing import Dict, TypeVar

import pystac
import requests
from pystac.extensions.file import FileExtension

from STACpopulator.extensions.base import ExtensionHelper

# Constants
T = TypeVar("T", pystac.Asset, pystac.Link)
HTTP_SERVER_ASSET_KEY = "HTTPServer"
OPEN_DAP_ASSET_KEY = "OpenDAP"


class FileHelper(ExtensionHelper):
    """Helper to handle file info from elements of types Asset and Link."""

    access_urls: Dict[str, str]
    _session = requests.Session()

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> T:
        """Apply the FileExtension to an asset."""
        # FIXME: This extension is applicable to Assets and Links.
        # Currently only applied to the HTTPServer asset to avoid heavy load during populator run
        asset = item.assets[HTTP_SERVER_ASSET_KEY]
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            byte_order=None,  # NOTE: Appears to be variable-related. Unclear what would be the value for the whole file.
            header_size=self.header_size,
            size=self.size,
            checksum=None,  # NOTE: Should be made available in the metadata on THREDDS catalog
            values=None,  # NOTE: Deprecated field
            local_path=None,  # NOTE: Seems to be irrelevant
        )

    @functools.cached_property
    def size(self) -> int:
        """Return file size in bytes."""
        if HTTP_SERVER_ASSET_KEY not in self.access_urls:
            return 0
        res = self._session.head(self.access_urls[HTTP_SERVER_ASSET_KEY])
        res.raise_for_status()
        return int(res.headers.get("Content-Length", None))

    @functools.cached_property
    def header_size(self) -> int:
        """Return the header size of the netCDF file in bytes."""
        # FIXME: Implementation to be discussed to confirm compliance with header size definition
        if OPEN_DAP_ASSET_KEY not in self.access_urls:
            return 0

        header_size = 0
        # <url>.dds returns variable and dimension structure
        # <url>.das returns attributes and metadata
        for end in [".dds", ".das"]:
            url = self.access_urls[OPEN_DAP_ASSET_KEY] + end
            res = self._session.get(url, stream=True)
            res.raise_for_status()

            bytes_count: int = sum(len(chunk) for chunk in res.iter_content(chunk_size=8192))
            header_size += bytes_count
        return header_size
