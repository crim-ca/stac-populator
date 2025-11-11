"""FileHelper module."""

import functools
import logging
from typing import Dict, Optional, TypeVar

import pystac
import requests
from pydantic import ConfigDict, Field
from pystac.extensions.file import FileExtension
from requests import Session

from STACpopulator.extensions.base import ExtensionHelper

# Constants
T = TypeVar("T", pystac.Asset, pystac.Link)
logger = logging.getLogger(__name__)


class FileHelper(ExtensionHelper):
    """Helper to handle file info from elements of types Asset and Link."""

    access_urls: Dict[str, str]
    asset_key: str = "HTTPServer"
    session: Optional[Session] = Field(default=None, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        access_urls: dict[str, str],
        asset_key: str = "HTTPServer",
        session: Optional[Session] = None,
    ) -> None:
        """Initialize the file helper.

        Parameters
        ----------
        access_urls : dict[str, str]
            Dictionary of catalog access URLs.
        asset_key : str.
            Asset key matching main file in access_urls. Defaults to `HTTPServer`.
        session : requests.Session, optional
            Requests session object to use for HTTP requests. Defaults to `requests.Session()`.
        """
        super().__init__(
            access_urls=access_urls,
            asset_key=asset_key,
            session=session or requests.Session(),
        )

    @classmethod
    def from_data(
        cls,
        data: dict[str, any],
        **kwargs,
    ) -> "FileHelper":
        """Create a FileHelper instance from raw data."""
        return cls(access_urls=data["data"]["access_urls"], **kwargs)

    def apply(self, item: pystac.Item, add_if_missing: bool = True) -> T:
        """Apply the FileExtension to an asset."""
        # FIXME: This extension is applicable to Assets and Links.
        # Currently applied to the HTTPServer asset by default to avoid heavy load during populator run
        asset = item.assets[self.asset_key]
        file_ext = FileExtension.ext(asset, add_if_missing=add_if_missing)
        file_ext.apply(
            size=self.size,
            byte_order=None,  # NOTE: Appears to be variable-related. Unclear what would be the value for the whole file.
            header_size=None,  # NOTE: No utility yet available. Might not be relevant.
            checksum=None,  # NOTE: Should be made available in the metadata on THREDDS catalog
            values=None,  # NOTE: Deprecated field
            local_path=None,  # NOTE: Seems to be irrelevant
        )

    @functools.cached_property
    def size(self) -> Optional[int]:
        """Return file size in bytes, None if asset_key not in access URLs dictionnary."""
        if self.asset_key not in self.access_urls:
            logger.warning("Asset key %s is not present in access URLs.", self.asset_key)
            return None
        res = self.session.head(self.access_urls[self.asset_key])
        res.raise_for_status()
        return int(res.headers.get("Content-Length", None))
